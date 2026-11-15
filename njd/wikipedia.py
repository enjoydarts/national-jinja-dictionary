"""Conservative secondary reading research; proposals never alter canonical data."""
import argparse
import hashlib
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
import re
from urllib.parse import parse_qs, quote, unquote, urljoin, urlsplit, urlencode

from njd.corrections import correction_problems
from njd.locations import apply_locations, raw_address
from njd.http import Client, FetchError
from njd.normalize import normalize_reading
from njd.report import PREFECTURES
from njd.storage import load_dataset, write_json, json_bytes

BASE='https://ja.wikipedia.org'
LICENSE='https://creativecommons.org/licenses/by-sa/4.0/deed.ja'
VOID={'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}

@dataclass
class Node:
    tag: str
    attrs: dict=field(default_factory=dict)
    children: list=field(default_factory=list)
    def all(self,tag=None):
        for child in self.children:
            if isinstance(child,Node):
                if tag is None or child.tag==tag:yield child
                yield from child.all(tag)
    def text(self):
        return ''.join(c.text() if isinstance(c,Node) else c for c in self.children if not isinstance(c,Node) or c.tag not in ('script','style','sup'))
    def has_class(self,value):return value in self.attrs.get('class','').split()

class Document(HTMLParser):
    def __init__(self,text):
        super().__init__(convert_charrefs=True);self.root=Node('document');self.stack=[self.root];self.feed(text)
    def handle_starttag(self,tag,attrs):
        node=Node(tag,dict(attrs));self.stack[-1].children.append(node)
        if tag not in VOID:self.stack.append(node)
    def handle_startendtag(self,tag,attrs):
        self.handle_starttag(tag,attrs)
        if tag not in VOID:self.handle_endtag(tag)
    def handle_endtag(self,tag):
        for i in range(len(self.stack)-1,0,-1):
            if self.stack[i].tag==tag:del self.stack[i:];break
    def handle_data(self,data):self.stack[-1].children.append(data)


def wiki_url(title):return BASE+'/wiki/'+quote(title.replace(' ','_'),safe=':()_')


def _title(url):
    parts=urlsplit(url)
    if parts.scheme!='https' or parts.netloc!='ja.wikipedia.org':return None
    if parts.path.startswith('/wiki/'):return unquote(parts.path[6:]).replace('_',' ')
    if parts.path=='/w/index.php':return parse_qs(parts.query).get('title',[None])[0]
    return None


def category_links(page):
    """Accept only links in generated category regions, never navigation links."""
    if not (_title(page.url) or '').startswith('Category:'):raise ValueError('not a Japanese Wikipedia category')
    root=Document(page.text).root;regions={n.attrs.get('id'):n for n in root.all() if n.attrs.get('id') in ('mw-pages','mw-subcategories')}
    if not regions:
        empty=[n for n in root.all('div') if n.has_class('mw-category-generated')
            and n.text().strip()=='現在このカテゴリには、ページまたはメディアがありません。'
            and not list(n.all('a'))]
        if len(empty)==1:return dict(categories=[],articles=[])
        raise ValueError('generated category regions absent')
    categories=set();articles=set()
    for region,node in regions.items():
        for a in node.all('a'):
            url=urljoin(page.url,a.attrs.get('href',''));parts=urlsplit(url);title=_title(url)
            if not title or parts.fragment:continue
            query=parse_qs(parts.query)
            if title.startswith('Category:'):
                if region=='mw-subcategories' and parts.path.startswith('/wiki/'):
                    categories.add(wiki_url(title))
                elif title==_title(page.url) and ('pagefrom' in query or 'subcatfrom' in query):
                    categories.add(url)
            elif region=='mw-pages' and ':' not in title and parts.path.startswith('/wiki/') and not parts.query:
                articles.add(wiki_url(title))
    return dict(categories=sorted(categories),articles=sorted(articles))


def article_infoboxes(root):
    leads=[n for n in root.all('section') if n.attrs.get('data-mw-section-id')=='0']
    container=leads[0] if len(leads)==1 else root
    boxes=[]
    for box in container.all('table'):
        if not box.has_class('infobox'):continue
        is_map=(box.attrs.get('id')=='GeoGroup' and box.has_class('mw-collapsible') and box.has_class('noprint')
            and re.sub(r'\s+','',box.text())=='全ての座標を示した地図-OSM表示')
        if not is_map:boxes.append(box)
    return boxes


def _address_text(node):
    if node.tag in ('script','style','sup'):return ''
    if node.tag=='a':
        target=urlsplit(node.attrs.get('href',''))
        if target.netloc=='geohack.toolforge.org' and target.path=='/geohack.php' and any(
            n.has_class('geo') or n.has_class('geo-dms') or n.has_class('geo-dec') for n in node.all()):return ''
    return ''.join(_address_text(c) if isinstance(c,Node) else c for c in node.children)


def _address_cell(cell):
    breaks=list(cell.all('br'))
    if list(cell.all('table')):raise ValueError('multiple address lines')
    if not breaks:return _address_text(cell).strip(),{}
    if len(breaks)!=1 or not any(c is breaks[0] for c in cell.children):raise ValueError('multiple address lines')
    i=next(i for i,c in enumerate(cell.children) if c is breaks[0])
    parts=[_address_text(Node('div',children=items)).strip() for items in (cell.children[:i],cell.children[i+1:])]
    before,after=parts;pref='(?:'+'|'.join(map(re.escape,PREFECTURES))+')'
    postal=bool(re.fullmatch(r'〒[0-9]{3}-[0-9]{4}',before) and re.match(pref,after))
    county=bool(re.fullmatch(pref+r'[\u3400-\u9fff々]+郡',before) and re.match(r'[^0-9\s都道府県郡区]+?[町村]',after))
    if (not (postal or county) or any(t in after for t in ('社務所','元宮','現社地','前宮','奥宮','〒'))
        or sum(after.count(p) for p in PREFECTURES)>int(postal)):
        raise ValueError('multiple address lines')
    value=(' ' if postal else '').join(parts)
    return value,dict(address_lines_raw=parts,address_layout_normalization='single postal/address or prefecture/county/municipality line wrap; whitespace only')


def article_reference(page,name):
    """Bind one exact bold lead name and kana to one rendered shrine infobox."""
    title=_title(page.url)
    if not title or ':' in title:raise ValueError('not a public Japanese Wikipedia article')
    root=Document(page.text).root
    outputs=[n for n in root.all() if n.has_class('mw-parser-output')]
    if len(outputs)!=1:raise ValueError('article content region ambiguous')
    content=outputs[0]
    boxes=article_infoboxes(content)
    if len(boxes)!=1:raise ValueError('single infobox required')
    box=boxes[0];headers=list(box.all('th'))
    if not headers or headers[0].text().strip()!=name:raise ValueError('infobox name differs')
    addresses=[];address_cells=[];address_layouts=[]
    for row in box.all('tr'):
        cells=[c for c in row.children if isinstance(c,Node) and c.tag in ('th','td')]
        if len(cells)==2 and cells[0].tag=='th' and cells[0].text().strip()=='所在地':
            address,layout=_address_cell(cells[1])
            addresses.append(address);address_cells.append(cells[1].text().strip());address_layouts.append(layout)
    if len(addresses)!=1 or not addresses[0]:raise ValueError('single rendered address required')
    leads=[n for n in content.all('section') if n.attrs.get('data-mw-section-id')=='0']
    if len(leads)!=1:raise ValueError('explicit lead section absent')
    paragraphs=list(leads[0].all('p'));matches=[]
    for index,p in enumerate(paragraphs,1):
        text=p.text().strip();bold=list(p.all('b'))
        if not bold or bold[0].text()!=name:continue
        match=re.match(re.escape(name)+r'[（(]([ぁ-ゖァ-ヶーゝゞヽヾ]+)(?:[、,](?:(?:旧字表記|正式名称)[：:])?[\u3400-\u9fff\uf900-\ufaff々]+(?:とも)?)?[）)]',text)
        if not match:continue
        for other in re.finditer(r'[（(][ぁ-ゖァ-ヶーゝゞヽヾ]+[）)]',text[match.end():]):
            before=text[:match.end()+other.start()].rstrip()
            # A different place or explicitly named old/alias shrine may have
            # its own kana. Bare extra kana or another reading of this name
            # remains ambiguous and is never used to complete the main reading.
            word=re.search(r'(?:「([^「」]+)」|([\u3400-\u9fff々〆ヵヶァ-ヶー]+))$',before)
            if not word or before.endswith(name) or (word.group(1) or word.group(2))==name:
                raise ValueError('multiple readings of the primary name or unbound lead kana')
        raw=match[1];reading=normalize_reading(raw)
        endings={'神社':('じんじゃ','じんしゃ','しんじゃ','しんしゃ','しゃ','やしろ'),'神宮':('じんぐう','ぐう'),'大社':('たいしゃ','だいしゃ','おおやしろ'),'宮':('ぐう','みや','きゅう')}
        for suffix,allowed in endings.items():
            if name.endswith(suffix):
                if not reading.endswith(allowed):raise ValueError('reading omits shrine name ending or requires review')
                break
        matches.append((index,match[0],raw))
    if len(matches)!=1:raise ValueError('one exact full-name lead reading required')
    revision=re.findall(r'"wgRevisionId"\s*:\s*(\d+)',page.text)
    if len(set(revision))!=1 or int(revision[0])<=0:raise ValueError('actual revision absent or ambiguous')
    index,excerpt,raw=matches[0]
    result=dict(url=page.url,title=title,source_kind='encyclopedia',name_raw=name,reading_raw=raw,address_raw=addresses[0],
        excerpt=excerpt+' / '+addresses[0],checked_at=page.fetched_at,page_hash=page.sha256,revision_id=int(revision[0]),
        permalink=BASE+'/w/index.php?'+urlencode(dict(title=title,oldid=revision[0])),license_url=LICENSE,
        locator=f'.mw-parser-output section[data-mw-section-id="0"] p[{index}] b; table.infobox tr[th="所在地"] td; mw.config.wgRevisionId',
        verification_method='mechanical exact bold full-name and single literal kana parenthetical; single rendered infobox name/address; correction_problems identity binding')
    result.update(address_layouts[0])
    if addresses[0]!=address_cells[0]:
        result.update(address_cell_raw=address_cells[0],address_extraction='literal address text; coordinate-link subtree excluded' if not address_layouts[0] else 'literal address text; single line wrap normalized; original line parts retained')
    return result


def external_directory(path):
    path=Path(path).expanduser().resolve();repository=Path(__file__).resolve().parents[1]
    if path.is_relative_to(repository):raise ValueError('research state/cache must be outside repository')
    return path


def pending_targets(data_dir,codes):
    data_dir=Path(data_dir);excluded=set()
    from njd.canonical import is_canonical, export_legacy
    if is_canonical(data_dir):
        projected=export_legacy(data_dir)
    else:
        projected={str(p.relative_to(data_dir)):load_dataset(p)
            for p in list((data_dir/'sources').glob('*.json'))+
                [data_dir/name for name in ('locations.json','corrections.json','reviews.json','decisions.json','source_aliases.json')
                 if (data_dir/name).exists()]}
    path=data_dir/'locations.json'
    locations=projected.get('locations.json')
    for filename in ('corrections.json','reviews.json','decisions.json'):
        if filename in projected:
            d=projected[filename];excluded.update(d.get('entries',d))
    targets=[]
    for filename,data in sorted(projected.items()):
        if not filename.startswith('sources/'):continue
        if locations is not None:data=apply_locations(data,locations)
        if data['collection'].get('source_key')=='kochi':
            from njd.source_aliases import apply_source_aliases
            if 'source_aliases.json' in projected:
                decisions=projected.get('decisions.json',{})
                protected={e['id'] for e in data['entries'] if decisions.get(e['id'],{}).get('status')=='pending'
                    and decisions[e['id']].get('expected_source_hash')==e.get('source_hash')}
                data=apply_source_aliases(data,projected['source_aliases.json'],protected_pending_entry_ids=protected)
        source=data['collection']
        if source.get('prefecture_code') not in codes:continue
        fs={f['id']:f for f in data['facilities']}
        for entry in data['entries']:
            facility=fs[entry['facility_id']]
            if (entry['id'] in excluded or entry.get('reading_raw') or entry.get('reading') or entry.get('status')!='pending'
                or entry.get('identity_review_required') or facility.get('status')!='verified' or facility.get('review_reason')
                or facility.get('source_conflicts') or entry.get('correction') or entry.get('human_review')):continue
            targets.append(dict(facility=facility,entry=entry,source=source))
    return sorted(targets,key=lambda t:t['entry']['id'])


def _proposal(target,ref):
    f=target['facility'];e=target['entry']
    correction=dict(status='verified',facility_id=f['id'],expected_source_hash=e.get('source_hash'),
        original=dict(name_raw=f.get('name_raw'),reading_raw=e.get('reading_raw'),address=raw_address(f),listing_url=f.get('listing_url')),
        changes=dict(reading=normalize_reading(ref['reading_raw'])),references=[ref],
        reason='Explicit full reading in independently inspected Wikipedia lead; exact name and rendered address checked mechanically.',
        identity_match=dict(agency_name=f.get('listed_name'),reference_name=ref['name_raw'],agency_address=raw_address(f),effective_address=f.get('address'),reference_address=ref['address_raw']))
    problems=correction_problems(correction,f,e,target['source'])
    if problems:raise ValueError('; '.join(problems))
    return correction


def _target_fingerprint(target):
    f=target['facility'];raw=target['entry'].get('source_hash')
    if not f.get('location_supplement',{}).get('applied'):return raw
    return hashlib.sha256(json_bytes([raw,f.get('address'),f.get('municipality')])).hexdigest()


def research(data_dir,state_dir,codes,client,*,limit=0,inventory_only=False,refresh=False,recheck=False):
    """Checkpoint every category/article. Retrieval failures retry on ordinary resume."""
    if limit<0:raise ValueError('limit must be nonnegative')
    state_dir=external_directory(state_dir);state_path=state_dir/'state/progress.json'
    state=load_dataset(state_path) if state_path.exists() else dict(schema_version=1,prefectures={})
    targets=pending_targets(data_dir,codes);attempted=0
    all_targets={t['entry']['id']:t for t in pending_targets(data_dir,[f'{i:02}' for i in range(1,48)])}
    proposal_path=state_dir/'proposals.json'
    previous=load_dataset(proposal_path).get('entries',{}) if proposal_path.exists() else {}
    current_ids={t['entry']['id'] for t in targets}
    proposals={eid:p for eid,p in previous.items() if eid not in current_ids and eid in all_targets
        and not correction_problems(p,all_targets[eid]['facility'],all_targets[eid]['entry'],all_targets[eid]['source'])}
    for code in sorted(codes):
        prefecture=PREFECTURES[int(code)-1];root=wiki_url('Category:'+prefecture+'の神社')
        scope=state['prefectures'].setdefault(code,dict(root=root,categories={},articles={}))
        categories=scope['categories'];queue=[root];seen=set()
        while queue:
            url=queue.pop(0)
            if url in seen:continue
            seen.add(url);saved=categories.get(url,{})
            if refresh or saved.get('status')!='fetched':
                try:
                    p=client.fetch(url,refresh=refresh);links=category_links(p)
                    saved=dict(status='fetched',**links,page_hash=p.sha256,checked_at=p.fetched_at)
                except (FetchError,ValueError,OSError,UnicodeError) as exc:saved=dict(status='failed',reason=str(exc))
                categories[url]=saved;write_json(state_path,state)
            if saved.get('status')=='fetched':queue.extend(saved['categories'])
        inventory=set(u for url in seen for u in categories[url].get('articles',[]))
        matching={};by_name={}
        for url in sorted(inventory):
            by_name.setdefault(re.sub(r' [（(][^()（）]+[）)]$','',_title(url) or ''),[]).append(url)
        for target in targets:
            f=target['facility']
            if f['prefecture_code']==code:
                for url in by_name.get(f.get('listed_name'),[]):matching.setdefault(url,[]).append(target)
        observations={};reinspected=set()
        for url,items in sorted(matching.items()):
            fingerprints={t['entry']['id']:_target_fingerprint(t) for t in items}
            saved=scope['articles'].get(url,{})
            reusable=saved.get('fingerprints')==fingerprints and saved.get('status')=='inspected' and not refresh and not recheck
            if not reusable and not inventory_only and (not limit or attempted<limit):
                attempted+=1;saved=dict(fingerprints=fingerprints,status='inspected',proposals={},pending={})
                try:
                    page=client.fetch(url,refresh=refresh)
                    saved.update(page_hash=page.sha256,checked_at=page.fetched_at)
                    for target in items:
                        eid=target['entry']['id']
                        try:saved['proposals'][eid]=_proposal(target,article_reference(page,target['facility']['listed_name']))
                        except ValueError as exc:saved['pending'][eid]=str(exc)
                except (FetchError,ValueError,OSError,UnicodeError) as exc:saved.update(status='failed',reason=str(exc))
                scope['articles'][url]=saved;write_json(state_path,state);reinspected.add(url);reusable=saved['status']=='inspected'
            if reusable:
                for target in items:
                    eid=target['entry']['id'];proposal=saved.get('proposals',{}).get(eid)
                    if proposal and not correction_problems(proposal,target['facility'],target['entry'],target['source']):observations.setdefault(eid,[]).append(proposal)
        scope['remaining_articles']=sorted(url for url,items in matching.items() if scope['articles'].get(url,{}).get('status')!='inspected' or scope['articles'][url].get('fingerprints')!={t['entry']['id']:_target_fingerprint(t) for t in items} or (recheck and url not in reinspected))
        scope['conflicting_reading_entry_ids']=sorted(eid for eid,values in observations.items() if len({v['changes']['reading'] for v in values})>1)
        waiting_ids={t['entry']['id'] for url in scope['remaining_articles'] for t in matching[url]}
        for eid,values in sorted(observations.items()):
            if eid not in waiting_ids and eid not in scope['conflicting_reading_entry_ids']:proposals[eid]=values[0]
        scope['category_errors']={url:categories[url].get('reason') for url in sorted(seen) if categories[url].get('status')!='fetched'}
        scope['inventory_complete']=not scope['category_errors']
        scope['candidate_articles']=len(matching)
        matched_ids={t['entry']['id'] for items in matching.values() for t in items}
        scope['unmatched_entry_ids']=sorted(t['entry']['id'] for t in targets if t['facility']['prefecture_code']==code and t['entry']['id'] not in matched_ids)
        scope['complete']=scope['inventory_complete'] and not scope['remaining_articles']
    selected=[state['prefectures'][code] for code in sorted(codes)]
    result=dict(complete=all(s['complete'] for s in selected),remaining_articles=sum(len(s['remaining_articles']) for s in selected),
        category_errors={u:reason for s in selected for u,reason in s['category_errors'].items()},proposals=len(proposals),articles_attempted=attempted,
        coverage='requested prefecture category trees only; inspected candidates and unmatched facilities are separate; no national completeness claim')
    write_json(state_dir/'proposals.json',dict(schema_version=1,entries=proposals));state['summary']=result;write_json(state_path,state)
    return result


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prefecture',required=True,choices=['all']+[f'{i:02}' for i in range(1,48)])
    parser.add_argument('--data-dir',type=Path,default=Path('data'))
    parser.add_argument('--state-dir',type=Path,required=True)
    parser.add_argument('--cache-dir',type=Path,default=Path.home()/'.cache/national-jinja-dictionary/http')
    parser.add_argument('--limit',type=int,default=0,help='maximum article fetches this run; 0 means unlimited')
    parser.add_argument('--inventory-only',action='store_true',help='prefetch category inventory without fetching articles')
    parser.add_argument('--offline',action='store_true');parser.add_argument('--refresh',action='store_true')
    parser.add_argument('--recheck',action='store_true',help='reparse saved articles through the HTTP cache without forcing network refresh')
    args=parser.parse_args(argv)
    codes=[f'{i:02}' for i in range(1,48)] if args.prefecture=='all' else [args.prefecture]
    client=Client(external_directory(args.cache_dir),offline=args.offline)
    result=research(args.data_dir,args.state_dir,codes,client,limit=args.limit,inventory_only=args.inventory_only,refresh=args.refresh,recheck=args.recheck)
    import json
    print(json.dumps(result,ensure_ascii=False,sort_keys=True));return 0

if __name__=='__main__':raise SystemExit(main())
