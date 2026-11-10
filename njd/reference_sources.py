"""Explicit reference-only eligibility for prefectures authorized by the user."""
import copy
import json
from datetime import datetime
import re
from urllib.parse import parse_qs,urlsplit
from njd.records import build_dataset,municipality_from_address
from njd.nationwide import SOURCE_KEYS
from njd.report import PREFECTURES
from njd.wikipedia import BASE,LICENSE,Document,article_reference,article_infoboxes,_title

BASIS='wikipedia_reference'
AUTHORIZED_CODES={'30','34','35','36','44','45'}


def _postal_address_body(address):
    return re.sub(r'^〒[0-9]{3}-[0-9]{4}\s+','',address)


def _location_context_matches(address,prefecture,context):
    municipality=municipality_from_address(address,prefecture)
    if not municipality or not address.startswith(municipality) or not isinstance(context,str):return False
    match=re.fullmatch(re.escape(prefecture+municipality)+r'(?P<tail>[^。]*?)に(?:ある|鎮座する|所在する)(?:神社|神宮|天満宮|八幡宮|東照宮|大社|社)(?:である)?。',context)
    if not match:return False
    tail=match['tail'];remaining=address[len(municipality):]
    if any(term in tail for term in ('ではなく','でなく','ではない','じゃなく','じゃない','では無く','では無い')):return False
    comparison_tail=re.sub(r'[（(][ぁ-ゖァ-ヶーゝゞヽヾ]+[）)]','',tail)
    # Only the actual infobox address may intervene before the locative verb.
    # Negations, other regions and arbitrary descriptive clauses are not proof.
    if not remaining.startswith(comparison_tail):return False
    if comparison_tail and comparison_tail[-1].isdigit() and len(remaining)>len(comparison_tail) and remaining[len(comparison_tail)].isdigit():return False
    return True


def _explicit_shrine_template(box):
    try:
        metadata=json.loads(box.attrs.get('data-mw',''))
        parts=metadata.get('parts',[]) if isinstance(metadata,dict) else []
        if not isinstance(parts,list):return None
        targets=[v.get('template',{}).get('target',{}) for v in parts if isinstance(v,dict) and isinstance(v.get('template'),dict)]
        targets=[t for t in targets if isinstance(t,dict) and isinstance(t.get('wt'),str)]
        if len(targets)==1 and targets[0]['wt'].strip()=='神社' and targets[0].get('href')=='./Template:神社':return targets[0]['wt'].strip()
    except (ValueError,TypeError):pass
    return None


def inspect_article(page,code):
    if code not in AUTHORIZED_CODES:raise ValueError('reference-only prefecture is not authorized')
    root=Document(page.text).root
    boxes=article_infoboxes(root)
    if len(boxes)!=1:raise ValueError('one shrine infobox required')
    headers=[h.text().strip() for h in boxes[0].all('th')]
    labels=[v for v in headers if v in ('主祭神','祭神')]
    template=_explicit_shrine_template(boxes[0])
    if not headers or not (labels or template):raise ValueError('explicit shrine infobox type required; temples and lists are not facilities')
    ref=article_reference(page,headers[0])
    ids=set(re.findall(r'"wgArticleId"\s*:\s*(\d+)',page.text))
    if len(ids)!=1:raise ValueError('one stable article ID required')
    if labels:ref['shrine_type_label_raw']=labels[0]
    else:ref['shrine_type_template_raw']=template
    ref.update(article_id=int(next(iter(ids))),
        verification_method='Exact shrine infobox name/location; explicit deity-label or shrine-template metadata; literal full-name lead kana; actual article/revision IDs; reference-only identity, agency publication not asserted.')
    prefecture=PREFECTURES[int(code)-1]
    if not _postal_address_body(ref['address_raw']).startswith(prefecture):
        municipality=municipality_from_address(ref['address_raw'],prefecture)
        contexts=[]
        for section in root.all('section'):
            if section.attrs.get('data-mw-section-id')!='0':continue
            for paragraph in section.all('p'):
                text=paragraph.text().strip()
                pattern=(re.escape(ref['name_raw'])+r'[（(]'+re.escape(ref['reading_raw'])+r'(?:[、,](?:(?:旧字表記|正式名称)[：:])?[\u3400-\u9fff\uf900-\ufaff々]+(?:とも)?)?[）)]は[、,\s]*'
                    +r'(?P<place>'+re.escape(prefecture+municipality)+r')(?P<tail>[^。]*?)に(?P<verb>ある|鎮座する|所在する)'
                    +r'(?P<end>(?:神社|神宮|天満宮|八幡宮|東照宮|大社|社)(?:である)?。)')
                match=re.match(pattern,text) if municipality else None
                if match:
                    context=match['place']+match['tail']+'に'+match['verb']+match['end']
                    if _location_context_matches(ref['address_raw'],prefecture,context):contexts.append(context)
        if len(contexts)==1:
            ref.update(prefecture_context_raw=prefecture,municipality_context_raw=municipality,
                location_context_excerpt=contexts[0],location_context_locator='same primary-name lead paragraph, complete affirmative shrine-location sentence')
            ref['excerpt']+=' / '+contexts[0]
    problems=_reference_problems(ref,code)
    if problems:raise ValueError('; '.join(problems))
    return ref


def _reference_problems(ref,code):
    if not isinstance(ref,dict):return ['missing Wikipedia article evidence']
    fields=('url','title','name_raw','reading_raw','address_raw','excerpt','permalink','page_hash','checked_at','license_url','locator')
    invalid=[key for key in fields if not isinstance(ref.get(key),str) or not ref[key]]
    if invalid:return ['missing or invalid reference field: '+key for key in invalid]
    problems=[]
    if code not in AUTHORIZED_CODES:problems.append('reference-only prefecture is not authorized')
    if ref.get('source_kind')!='encyclopedia':problems.append('reference is not an encyclopedia article')
    try:
        title=_title(ref['url']);p=urlsplit(ref['permalink']);q=parse_qs(p.query)
    except (ValueError,TypeError):return ['invalid reference URL']
    if not title or ':' in title or title!=ref.get('title'):problems.append('invalid Wikipedia article URL/title')
    for key in ('article_id','revision_id'):
        if type(ref.get(key)) is not int or ref[key]<=0:problems.append('missing positive '+key)
    if (p.scheme!='https' or p.netloc!='ja.wikipedia.org' or p.path!='/w/index.php' or p.fragment
        or set(q)!={'title','oldid'} or q.get('title')!=[title] or q.get('oldid')!=[str(ref.get('revision_id'))]):
        problems.append('revision permalink does not identify the inspected article/version')
    if ref.get('license_url')!=LICENSE:problems.append('missing Wikipedia license attribution')
    if not re.fullmatch('[0-9a-f]{64}',ref.get('page_hash','')):problems.append('missing inspected page hash')
    try:
        if datetime.fromisoformat(ref.get('checked_at','')).tzinfo is None:raise ValueError()
    except (TypeError,ValueError):problems.append('missing timezone-aware inspection date')
    if ref.get('shrine_type_label_raw') not in ('主祭神','祭神') and ref.get('shrine_type_template_raw')!='神社':problems.append('explicit shrine type evidence missing')
    name=ref.get('name_raw','');raw=ref.get('reading_raw','');address=ref.get('address_raw','');excerpt=ref.get('excerpt','')
    if not all(isinstance(v,str) and v and v in excerpt for v in (name,raw,address)):problems.append('name/full reading/address not recorded in inspected excerpt')
    if re.search(r'[・･、,，/／＆&＋+]',name):problems.append('combined names require individual full-reading review')
    if code in AUTHORIZED_CODES:
        prefecture=PREFECTURES[int(code)-1]
        if not _postal_address_body(address).startswith(prefecture):
            municipality=municipality_from_address(address,prefecture)
            if (not municipality or ref.get('prefecture_context_raw')!=prefecture or ref.get('municipality_context_raw')!=municipality
                or not _location_context_matches(address,prefecture,ref.get('location_context_excerpt'))
                or ref.get('location_context_excerpt','') not in excerpt):
                problems.append('source address lacks matching explicit prefecture/municipality context')
    from njd.normalize import normalize_reading
    try:
        reading=normalize_reading(raw)
        for suffix,endings in [('神社',('じんじゃ','じんしゃ','しんじゃ','しんしゃ')),('神宮',('じんぐう',)),('大社',('たいしゃ','だいしゃ','おおやしろ')),('宮',('ぐう','みや','きゅう')),('社',('しゃ','やしろ','じんじゃ'))]:
            if name.endswith(suffix):
                if not reading.endswith(endings):raise ValueError()
                break
    except (ValueError,TypeError):problems.append('literal full shrine reading is absent or invalid')
    return problems


def reference_problems(facility,entry,source):
    problems=_reference_problems(facility.get('source_reference'),facility.get('prefecture_code'))
    if source.get('listing_basis')!=BASIS or facility.get('listing_basis')!=BASIS:problems.append('reference-only source basis differs')
    if facility.get('agency') or source.get('official_agency_listing_verified') is not False:problems.append('reference source must not claim agency publication')
    if facility.get('source_publisher')!='日本語版Wikipedia':problems.append('reference publisher missing')
    ref=facility.get('source_reference')
    if not isinstance(ref,dict):ref={}
    if (ref.get('name_raw'),ref.get('reading_raw'),ref.get('address_raw'),ref.get('url'),ref.get('page_hash'))!=(facility.get('name_raw'),entry.get('reading_raw'),facility.get('address'),facility.get('listing_url'),facility.get('page_hash')):
        problems.append('reference fields differ from acquired facility/entry')
    if entry.get('reading_source_kind')=='encyclopedia' and entry.get('reading_url') not in (ref.get('url'),ref.get('permalink')):
        problems.append('encyclopedia reading URL differs from inspected article/version')
    if facility.get('native_source_id')!='wikipedia:pageid:'+str(ref.get('article_id')):problems.append('stable article identity differs')
    extras=facility.get('additional_source_references',[])
    if not isinstance(extras,list):problems.append('invalid additional source references')
    else:
        occurrences=set();observed=facility.get('listing_occurrences',[])
        if not isinstance(observed,list):problems.append('invalid source occurrences');observed=[]
        for value in observed:
            if not isinstance(value,dict) or any(not isinstance(value.get(key),str) for key in ('url','page_hash','fetched_at')):
                problems.append('invalid source occurrence fields');continue
            occurrences.add((value['url'],value['page_hash'],value['fetched_at']))
        for extra in extras:
            issues=_reference_problems(extra,facility.get('prefecture_code'));problems.extend(issues)
            if issues:continue
            if any(extra.get(key)!=ref.get(key) for key in ('article_id','name_raw','reading_raw','address_raw')):
                problems.append('additional source observation conflicts with facility identity/raw fields')
            if (extra.get('url'),extra.get('page_hash'),extra.get('checked_at')) not in occurrences:
                problems.append('additional reference has no observed source occurrence')
    return problems


def dataset_from_references(code,references,*,metadata=None):
    if code not in AUTHORIZED_CODES:raise ValueError('reference-only prefecture is not authorized')
    rows=[]
    for ref in references:
        problems=_reference_problems(ref,code)
        if problems:raise ValueError('; '.join(problems))
        rows.append(dict(name=ref['name_raw'],reading_raw=ref['reading_raw'],address=ref['address_raw'],url=ref['url'],
            source_id='wikipedia:pageid:'+str(ref['article_id']),municipality=municipality_from_address(_postal_address_body(ref['address_raw']),PREFECTURES[int(code)-1]),fetched_at=ref['checked_at'],page_hash=ref['page_hash'],locator=ref['locator'],evidence=ref['excerpt']))
    source=dict(metadata or {})
    source.update(listing_basis=BASIS,source_publisher='日本語版Wikipedia',official_agency_listing_verified=False,
        authority_status='reference_source',coverage='Inspected Wikipedia shrine articles only; not agency listings or all prefectural shrines.',
        license_url=LICENSE,terms_url='https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use/ja',
        redistribution_status='Wikipedia source attribution and CC BY-SA 4.0 retained; not relicensed as MIT.')
    data=build_dataset(SOURCE_KEYS[int(code)-1],code,PREFECTURES[int(code)-1],'',rows,metadata=source)
    data['collection'].pop('agency',None)
    by_id={};extra={}
    for row,ref in zip(rows,references):
        if row['source_id'] in by_id:
            if ref!=by_id[row['source_id']]:extra.setdefault(row['source_id'],[]).append(ref)
        else:by_id[row['source_id']]=ref
    for f in data['facilities']:
        f.pop('agency',None);f.update(listing_basis=BASIS,source_publisher='日本語版Wikipedia',source_reference=copy.deepcopy(by_id[f['native_source_id']]))
        if f['native_source_id'] in extra:f['additional_source_references']=copy.deepcopy(extra[f['native_source_id']])
    for entry in data['entries']:entry.update(reading_source_kind='encyclopedia',listing_basis=BASIS)
    from njd.validation import blocking_problems
    problems=blocking_problems(data)
    if problems:raise ValueError('reference dataset validation failed: '+str(problems[:3]))
    return data


def research(code,state_dir,client,*,limit=0,refresh=False):
    """Stage inspected reference records; never write the canonical repository."""
    from njd.wikipedia import external_directory,wiki_url,category_links
    from njd.http import FetchError
    from njd.storage import load_dataset,write_json
    from njd.nationwide import public_failure
    if code not in AUTHORIZED_CODES or limit<0:raise ValueError('unsupported prefecture or negative limit')
    state_dir=external_directory(state_dir);path=state_dir/'state.json'
    state=load_dataset(path) if path.exists() else dict(schema_version=1,prefecture_code=code,categories={},articles={})
    if state.get('prefecture_code')!=code:raise ValueError('research state belongs to another prefecture')
    categories=state['categories'];articles=state['articles'];queue=[wiki_url('Category:'+PREFECTURES[int(code)-1]+'の神社')]
    seen=set();inventory=set();category_failure=False;attempted=0
    def checkpoint():
        reviews=[];refs=[];pages=[]
        for url in sorted(seen):
            v=categories[url]
            if v.get('page_hash'):pages.append(dict(url=url,sha256=v['page_hash'],fetched_at=v['fetched_at']))
            if v.get('status')!='fetched':reviews.append(dict(url=url,status='fetch_failed',reason=v.get('public_reason','category inspection failed')))
        for url in sorted(inventory):
            v=articles.get(url)
            if not v:continue
            if v.get('page_hash'):pages.append(dict(url=url,sha256=v['page_hash'],fetched_at=v['fetched_at']))
            problems=_reference_problems(v.get('reference'),code) if v.get('status')=='extracted' else []
            if problems:v.update(status='needs_review',reason='; '.join(problems))
            if v.get('status')=='extracted':refs.append(v['reference'])
            else:reviews.append(dict(url=url,reason=v.get('public_reason',v.get('reason','inspection incomplete')),**{k:v[k] for k in ('status','page_hash','fetched_at') if k in v}))
        inspected={url for url in inventory if articles.get(url,{}).get('status') in ('extracted','needs_review') and articles[url].get('page_hash')}
        remaining=inventory-inspected;unvisited=len(remaining);failed=sum(v.get('status')=='fetch_failed' for v in reviews)
        complete=not category_failure and not failed and not unvisited
        metadata=dict(pages=pages,pages_fetched=len(pages),article_inventory_count=len(inventory),articles_inspected=len(inspected),articles_attempted_total=len(inventory&set(articles)),
            articles_with_full_reference=len(refs),article_reviews=reviews,inspection_complete=complete,collection_complete=complete,
            remaining_scope=sorted(remaining),coverage='Recorded Wikipedia category tree only; article/list counts differ from facility counts.')
        candidate=dataset_from_references(code,refs,metadata=metadata)
        summary=dict(prefecture_code=code,articles=len(inventory),facilities=len(candidate['facilities']),article_reviews=len(reviews),
            fetch_errors=failed,unvisited=unvisited,complete=complete,articles_attempted=attempted,canonical_update='not applied; review candidate.json before adoption')
        state['summary']=summary;write_json(state_dir/'candidate.json',candidate);write_json(path,state);return summary
    while queue:
        url=queue.pop(0)
        if url in seen:continue
        seen.add(url);saved=categories.get(url,{})
        if refresh or saved.get('status')!='fetched':
            try:
                page=client.fetch(url,refresh=refresh);links=category_links(page)
                saved=dict(status='fetched',**links,page_hash=page.sha256,fetched_at=page.fetched_at)
            except (FetchError,OSError,UnicodeError,ValueError) as exc:saved=dict(status='fetch_failed',reason=str(exc),public_reason=public_failure(exc))
            categories[url]=saved
        if saved.get('status')!='fetched':category_failure=True;return checkpoint()
        queue.extend(saved['categories']);inventory.update(saved['articles'])
    checkpoint()
    for url in sorted(inventory):
        if not refresh and articles.get(url,{}).get('status') in ('extracted','needs_review'):continue
        if limit and attempted>=limit:break
        attempted+=1;saved={}
        try:
            page=client.fetch(url,refresh=refresh);saved.update(page_hash=page.sha256,fetched_at=page.fetched_at)
            saved.update(status='extracted',reference=inspect_article(page,code))
        except ValueError as exc:saved.update(status='needs_review',reason=str(exc))
        except (FetchError,OSError,UnicodeError) as exc:saved.update(status='fetch_failed',reason=str(exc),public_reason=public_failure(exc))
        articles[url]=saved;checkpoint()
        if saved['status']=='fetch_failed':break
    return checkpoint()


def main(argv=None):
    import argparse,json
    from pathlib import Path
    from njd.http import Client
    from njd.wikipedia import external_directory
    p=argparse.ArgumentParser(description='Stage user-authorized Wikipedia reference-only shrine records; does not edit canonical data')
    p.add_argument('--prefecture',required=True,choices=sorted(AUTHORIZED_CODES));p.add_argument('--state-dir',required=True,type=Path)
    p.add_argument('--cache-dir',type=Path,default=Path.home()/'.cache/national-jinja-dictionary/http')
    p.add_argument('--limit',type=int,default=0);p.add_argument('--offline',action='store_true');p.add_argument('--refresh',action='store_true')
    args=p.parse_args(argv)
    result=research(args.prefecture,args.state_dir,Client(external_directory(args.cache_dir),offline=args.offline,retries=0),limit=args.limit,refresh=args.refresh)
    print(json.dumps(result,ensure_ascii=False,sort_keys=True));return int(bool(result['fetch_errors']))


if __name__=='__main__':raise SystemExit(main())
