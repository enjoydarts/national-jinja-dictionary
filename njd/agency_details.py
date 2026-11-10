"""Inspect recorded official detail links; emit independent primary-reading proposals."""
import argparse
import hashlib
from html import unescape
from pathlib import Path
import re
from urllib.parse import urlsplit, urljoin, parse_qs
from njd.adapters.central import Document as CentralDocument, cells as central_cells, clean, decode_html, parse_shiga, parse_shiga_detail
from njd.corrections import correction_problems
from njd.http import Client, FetchError
from njd.normalize import normalize_reading
from njd.storage import json_bytes, load_dataset, write_json
from njd.wikipedia import Document, Node, external_directory

HOST='www.shimane-jinjacho.or.jp'
SOURCES=dict(shimane=dict(host=HOST,detail=r'/[a-z]+/[0-9a-f]{40}\.html'),
    nagano=dict(host='www.nagano-jinjacho.jp',detail=r'/shibu/(?:[a-zA-Z0-9_-]+/)+[a-zA-Z0-9_-]+\.html?'),
    shiga=dict(host='www.shiga-jinjacho.jp',detail=r'/ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-detail\.html'))


def detail_url(url,listing_url=None,source='shimane'):
    """Only previously recorded public detail links on the known agency host."""
    try:
        p=urlsplit(url or '');listing=urlsplit(listing_url or '');spec=SOURCES[source]
        if source=='shiga':
            q=parse_qs(p.query,keep_blank_values=True)
            return (p.scheme=='https' and p.netloc==spec['host'] and not p.fragment
                and bool(re.fullmatch(spec['detail'],p.path)) and set(q)=={'mode:view','view:oid'}
                and q['mode:view']==['1'] and len(q['view:oid'])==1 and bool(re.fullmatch(r'[0-9]+',q['view:oid'][0]))
                and (listing_url is None or _shiga_index_url(listing_url)))
        return (p.scheme=='https' and p.netloc==spec['host'] and not p.query and not p.fragment
            and bool(re.fullmatch(spec['detail'],p.path))
            and (listing_url is None or listing.scheme in ('http','https') and listing.netloc==spec['host']))
    except ValueError:return False


def parse_detail(page,name,source='shimane'):
    if not detail_url(page.url,source=source):raise ValueError('untrusted official detail URL')
    if source=='nagano':return parse_nagano_detail(page,name)
    if source=='shiga':
        observed=parse_shiga_detail(decode_html(page))
        if not observed or observed['name_raw']!=name:raise ValueError('one exact agency-listed title, literal kana and location required')
        return dict(observed,url=page.url,title=name+' | 滋賀県神社庁',source_kind='agency',
            checked_at=page.fetched_at,fetched_at=page.fetched_at,page_hash=page.sha256,
            agency_code=parse_qs(urlsplit(page.url).query)['view:oid'][0],
            excerpt=observed['name_display_raw']+' / '+observed['address_raw'],
            locator='div.j_title first literal kana; separate alias; unique table row 鎮座地',
            verification_method='Exact agency-linked name/native ID and literal kana; full-name and location validation performed before proposal. Alias not registered.')
    boxes=[n for n in Document(page.text).root.all('table') if n.has_class('address-detail')]
    if len(boxes)!=1:raise ValueError('one address-detail table required')
    rows=[]
    for row in boxes[0].all('tr'):
        cells=[c for c in row.children if isinstance(c,Node) and c.tag in ('td','th')]
        if len(cells)!=2 or any(list(c.all('table')) for c in cells):raise ValueError('malformed detail table row')
        rows.append((cells[0].text().strip(),cells[1].text().strip()))
    formal_labels={'神社名（正称)','神社名（正称）','神社名(正称)'}
    formal=[i for i,(label,value) in enumerate(rows) if label in formal_labels]
    if len(formal)!=1:raise ValueError('one explicit formal-name row required')
    i=formal[0]
    if rows[i][1]!=name:raise ValueError('official detail formal name differs from acquired listed name')
    if i+1>=len(rows) or rows[i+1][0]!='ふりがな':raise ValueError('immediate formal-name reading row absent')
    raw=rows[i+1][1];_full_reading(name,raw)
    values={}
    for label in ('鎮座地','神社コード'):
        found=[value for key,value in rows if key==label]
        if len(found)!=1 or not found[0]:raise ValueError('one nonempty '+label+' row required')
        values[label]=found[0]
    if not re.fullmatch(r'[0-9]{5}',values['神社コード']):raise ValueError('invalid agency shrine code')
    if any(ord(c)<32 for c in name+raw+values['鎮座地']):raise ValueError('multiline name, reading or location requires review')
    return dict(url=page.url,title=name+' | 島根県神社庁',source_kind='agency',name_raw=name,reading_raw=raw,
        address_raw=values['鎮座地'],agency_code=values['神社コード'],checked_at=page.fetched_at,page_hash=page.sha256,
        excerpt=name+' / '+raw+' / '+values['鎮座地']+' / 神社コード '+values['神社コード'],
        locator=f'table.address-detail tr[{i+1}] 神社名（正称); immediately following tr[{i+2}] ふりがな; unique 鎮座地 and 神社コード rows',
        verification_method='mechanical exact formal name, immediately following literal full-kana reading, unique rendered location/code; correction_problems name/address binding')


def nagano_links(page):
    """Mirror central.parse_nagano header/cell/nested-row selection, retaining anchors."""
    if not _index_url(page.url):raise ValueError('untrusted Nagano index URL')
    result=[]
    for table in CentralDocument(page.text).root.find('table'):
        nested={id(row) for child in table.find('table') for row in child.find('tr')};recognized=False
        for i,row in enumerate((r for r in table.find('tr') if id(r) not in nested),1):
            cs=central_cells(row);values=[clean(c.text()) for c in cs]
            if values==['神社名','〒','住所']:recognized=True;continue
            if not (recognized and len(cs)==3 and values[0] and re.search('[市町村]',values[2])):continue
            links={urljoin(page.url,a.attrs.get('href','')) for a in cs[0].find('a') if a.attrs.get('href')}
            if len(links)!=1:continue
            url=next(iter(links))
            if not detail_url(url,page.url,source='nagano'):continue
            result.append(dict(name_raw=values[0],address_raw=values[2],url=url,index_url=page.url,index_page_hash=page.sha256,
                index_checked_at=page.fetched_at,index_locator=f'table tr[{i}] exact 神社名/〒/住所 row; first cell a[href]',
                index_excerpt=values[0]+' / '+values[2]))
    return result


def _shiga_index_url(url):
    try:
        p=urlsplit(url or '');q=parse_qs(p.query,keep_blank_values=True)
        return (p.scheme=='https' and p.netloc==SOURCES['shiga']['host'] and not p.fragment
            and p.path=='/ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-search.html'
            and set(q)<={'mode:search','view:term','view:page'} and bool(q)
            and all(len(v)==1 for v in q.values())
            and q.get('mode:search',['1'])==['1']
            and all(re.fullmatch(r'[0-9]+',v[0]) for k,v in q.items() if k!='mode:search'))
    except ValueError:return False


def shiga_links(page):
    if not _shiga_index_url(page.url):raise ValueError('untrusted Shiga index URL')
    html=decode_html(page);root=CentralDocument(html).root
    bases=[b.attrs['href'] for b in root.find('base') if b.attrs.get('href')]
    if len(bases)>1:raise ValueError('ambiguous Shiga index base')
    base=urljoin(page.url,bases[0]) if bases else page.url
    rows=parse_shiga(html);counts={}
    for row in rows:counts[row['source_id']]=counts.get(row['source_id'],0)+1
    result=[]
    for row in rows:
        if counts[row['source_id']]!=1:continue
        # The URL must come from this exact anchor/postal-span pair, never
        # from another anchor elsewhere on the index with a matching name.
        href=row['href_raw'];url=urljoin(base,unescape(href))
        if not detail_url(url,page.url,'shiga'):continue
        if parse_qs(urlsplit(url).query)['view:oid']!=[row['source_id']]:continue
        result.append(dict(name_raw=row['name'],address_raw=row['address'],source_id=row['source_id'],url=url,
            index_url=page.url,index_page_hash=page.sha256,index_checked_at=page.fetched_at,
            index_locator=row['locator'],index_excerpt=row['evidence'],href_raw=href,base_href=bases[0] if bases else None))
    return result


def _index_url(url):
    try:
        p=urlsplit(url or '')
        return p.scheme=='https' and p.netloc==SOURCES['nagano']['host'] and not p.query and not p.fragment and bool(re.fullmatch(r'/shibu/[a-z0-9]+\.htm',p.path))
    except ValueError:return False


def _full_reading(name,raw):
    reading=normalize_reading(raw)
    suffixes={'神社':('じんじゃ','じんしゃ','しんじゃ','しんしゃ'),'神宮':('じんぐう',),'大社':('たいしゃ','だいしゃ','おおやしろ'),'宮':('ぐう','みや','きゅう'),'社':('しゃ','やしろ')}
    for suffix,endings in suffixes.items():
        if name.endswith(suffix):
            if not reading.endswith(endings):raise ValueError('explicit reading lacks full shrine-name ending; requires review')
            break
    return reading


def parse_nagano_detail(page,name):
    tables=[]
    for table in CentralDocument(page.text).root.find('table'):
        nested={id(row) for child in table.find('table') for row in child.find('tr')};rows=[]
        for row in table.find('tr'):
            if id(row) in nested:continue
            cs=central_cells(row)
            if len(cs)==2:rows.append((clean(cs[0].text()),cs[1].text().strip()))
        if any(label=='神社名' for label,value in rows):tables.append(rows)
    if len(tables)!=1:raise ValueError('one typed shrine detail table required')
    rows=tables[0];names=[(i,value) for i,(label,value) in enumerate(rows) if label=='神社名']
    if len(names)!=1:raise ValueError('one typed shrine-name field required')
    i,raw_name=names[0]
    match=re.match(re.escape(name)+r'\s*[（(]([ぁ-ゖァ-ヶーゝゞヽヾ]+)[）)]',raw_name)
    if not match:raise ValueError('leading exact full name and literal kana absent')
    tail=raw_name[match.end():].strip()
    if tail and not re.fullmatch(r'[（(]通称[）)].+',tail):raise ValueError('ambiguous suffix after formal-name reading')
    _full_reading(name,match[1])
    addresses=[(j,value) for j,(label,value) in enumerate(rows) if label in ('鎮座地','所在地')]
    if len(addresses)!=1 or not addresses[0][1]:raise ValueError('one typed shrine location required')
    j,address=addresses[0]
    if j!=i+1:raise ValueError('location is not immediately attached to shrine name; office/priest ambiguity')
    if re.search(r'前宮|奥宮|[\r\n]',address):raise ValueError('multiple shrine locations or multiline location require review')
    return dict(url=page.url,title=name+' | 長野県神社庁',source_kind='agency',name_raw=name,name_field_raw=raw_name,
        reading_raw=match[1],address_raw=address,checked_at=page.fetched_at,page_hash=page.sha256,
        excerpt=match[0]+' / '+address,locator=f'own table rows[{i+1}] td[神社名] leading formal-name kana; immediately following row[{j+1}] td[鎮座地/所在地]',
        verification_method='exact acquired index name/address row and actual name-cell detail link; leading full-name literal kana; typed shrine location; correction_problems identity binding')


def targets(data_dir,source='shimane'):
    if source not in SOURCES:raise ValueError('unsupported agency detail source')
    data_dir=Path(data_dir);excluded=set()
    for filename in ('reviews.json','decisions.json'):
        path=data_dir/filename
        if path.exists():
            doc=load_dataset(path);excluded.update(doc.get('entries',doc))
    data=load_dataset(data_dir/'sources'/f'{source}.json');fs={f['id']:f for f in data['facilities']};result=[]
    for entry in data['entries']:
        f=fs[entry['facility_id']]
        if (entry['id'] in excluded or entry.get('reading_raw') or entry.get('identity_review_required')
            or entry.get('human_review') or f.get('status')!='verified' or f.get('review_reason') or f.get('source_conflicts')
            or data['collection'].get('authority_status') in ('pending','unconfirmed')):continue
        result.append(dict(entry=entry,facility=f,source=data['collection']))
    return sorted(result,key=lambda t:t['entry']['id'])


def fingerprint(target):
    return hashlib.sha256(json_bytes(dict(entry=target['entry'],facility=target['facility'],
        authority_status=target['source'].get('authority_status')))).hexdigest()


def proposal(target,ref):
    f=target['facility'];e=target['entry']
    value=dict(status='verified',facility_id=f['id'],expected_source_hash=e.get('source_hash'),
        original=dict(name_raw=f.get('name_raw'),reading_raw=e.get('reading_raw'),address=f.get('address'),listing_url=f.get('listing_url')),
        changes=dict(reading=normalize_reading(ref['reading_raw'])),references=[ref],
        reason='Recorded official agency detail explicitly supplies the full formal-name reading; acquired index source remains unchanged.',
        identity_match=dict(agency_name=f.get('listed_name'),reference_name=ref['name_raw'],agency_address=f.get('address'),reference_address=ref['address_raw']))
    problems=correction_problems(value,f,e,target['source'])
    if problems:raise ValueError('; '.join(problems))
    return value


def research(data_dir,state_dir,client,*,source='shimane',limit=0,refresh=False,recheck=False):
    if limit<0:raise ValueError('limit must be nonnegative')
    state_dir=external_directory(state_dir);state_path=state_dir/'state/progress.json'
    state=load_dataset(state_path) if state_path.exists() else dict(schema_version=1,source=source,entries={})
    if state.get('source')!=source:raise ValueError('state belongs to another source')
    selected=targets(data_dir,source);records=state['entries'];attempted=0;index_cache={}
    correction_ids=set()
    correction_path=Path(data_dir)/'corrections.json'
    if correction_path.exists():correction_ids.update(load_dataset(correction_path).get('entries',{}))
    def checkpoint():
        proposals={};pending=errors=unvisited=0
        for target in selected:
            eid=target['entry']['id'];saved=records.get(eid,{})
            if saved.get('fingerprint')!=fingerprint(target):unvisited+=1;continue
            if saved.get('status')=='failed':errors+=1;continue
            if saved.get('status')!='inspected':unvisited+=1;continue
            value=saved.get('proposal')
            if value and not correction_problems(value,target['facility'],target['entry'],target['source']):proposals[eid]=value
            else:pending+=1
        summary=dict(source=source,targets=len(selected),proposals=len(proposals),pending=pending,errors=errors,unvisited=unvisited,
            complete=not errors and not unvisited,inspection_scope='recorded eligible agency detail links only; inspection completion is not nationwide coverage',
            existing_correction_entry_ids=sorted(correction_ids & {t['entry']['id'] for t in selected}),attempted_this_run=attempted)
        state['summary']=summary;write_json(state_dir/'proposals.json',dict(schema_version=1,entries=proposals));write_json(state_path,state)
        return summary
    checkpoint()
    ordered=sorted(selected,key=lambda t:(records.get(t['entry']['id'],{}).get('fingerprint')==fingerprint(t),t['entry']['id']))
    for target in ordered:
        eid=target['entry']['id'];saved=records.get(eid,{})
        if saved.get('fingerprint')==fingerprint(target) and saved.get('status')=='inspected' and not refresh and not recheck:continue
        if limit and attempted>=limit:break
        attempted+=1;f=target['facility'];url=f.get('native_source_id')
        saved=dict(fingerprint=fingerprint(target),expected_source_hash=target['entry'].get('source_hash'),url=url,status='inspected')
        try:
            proof={}
            if source in ('nagano','shiga'):
                index=f.get('listing_url')
                index_valid=_index_url if source=='nagano' else _shiga_index_url
                link_parser=nagano_links if source=='nagano' else shiga_links
                if not index_valid(index):raise ValueError('unknown or cross-host agency listing URL')
                if index not in index_cache:
                    try:
                        index_page=client.fetch(index,refresh=refresh)
                        if index_page.url!=index:raise ValueError('index redirected away from recorded listing URL')
                        index_cache[index]=link_parser(index_page)
                    except (FetchError,OSError,UnicodeError,ValueError) as exc:index_cache[index]=exc
                if isinstance(index_cache[index],Exception):raise index_cache[index]
                matches=[row for row in index_cache[index] if (row['name_raw'],row['address_raw'])==(f.get('listed_name'),f.get('address'))]
                if source=='shiga':matches=[row for row in matches if row['source_id']==f.get('native_source_id')]
                if len(matches)!=1:raise ValueError('no unique exact acquired name/address index row with official detail link')
                proof=matches[0];url=proof['url'];saved.update(url=url,index_proof=proof)
            if not detail_url(url,f.get('listing_url'),source):raise ValueError('native detail URL missing, unknown or outside the recorded official host')
            page=client.fetch(url,refresh=refresh)
            saved.update(page_hash=page.sha256,checked_at=page.fetched_at)
            if page.url!=url:raise ValueError('detail redirected away from recorded native URL; requires review')
            ref=parse_detail(page,f.get('listed_name',''),source)
            ref.update({k:v for k,v in proof.items() if k.startswith('index_')})
            if source=='shiga':
                if ref['agency_code']!=f.get('native_source_id'):raise ValueError('agency detail native ID differs')
                ref['index_proof']=proof;ref['reading_scope']='partial_or_absent';saved['reference']=ref
                _full_reading(ref['name_raw'],ref['reading_raw'])
                ref['reading_scope']='full_name'
            saved['reference']=ref;saved['proposal']=proposal(target,ref)
        except ValueError as exc:saved['pending_reason']=str(exc)
        except (FetchError,OSError,UnicodeError) as exc:saved.update(status='failed',error=str(exc))
        records[eid]=saved;checkpoint()
        if source=='shiga' and saved.get('status')=='failed':break
    return checkpoint()


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',choices=list(SOURCES),default='shimane')
    parser.add_argument('--data-dir',type=Path,default=Path('data'))
    parser.add_argument('--state-dir',type=Path,required=True)
    parser.add_argument('--cache-dir',type=Path,default=Path.home()/'.cache/national-jinja-dictionary/http')
    parser.add_argument('--limit',type=int,default=0)
    parser.add_argument('--offline',action='store_true');parser.add_argument('--refresh',action='store_true');parser.add_argument('--recheck',action='store_true')
    args=parser.parse_args(argv)
    client=Client(external_directory(args.cache_dir),offline=args.offline)
    result=research(args.data_dir,args.state_dir,client,source=args.source,limit=args.limit,refresh=args.refresh,recheck=args.recheck)
    import json
    print(json.dumps(result,ensure_ascii=False,sort_keys=True));return 0

if __name__=='__main__':raise SystemExit(main())
