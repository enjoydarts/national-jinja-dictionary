"""Stage literal Miyazaki youth-association observations, separately from agency data.

This collector never writes canonical data or treats the association as a shrine
agency. Whole articles, shrine histories and photographs stay in private cache.
"""
import argparse
import copy
from datetime import datetime
from pathlib import Path
import re
import unicodedata
from urllib.parse import urljoin,urlsplit
from njd.http import Client,FetchError
from njd.normalize import normalize_reading
from njd.records import municipality_from_address
from njd.storage import load_dataset,write_json
from njd.wikipedia import Document,external_directory

BASE='https://www.m-shinsei.jp'
INDEX=BASE+'/shrine/'
PUBLISHER='宮崎県神道青年会'
BASIS='association_reference'


def _index_url(url):
    try:p=urlsplit(url)
    except (TypeError,ValueError):return False
    return (p.scheme=='https' and p.netloc=='www.m-shinsei.jp' and not p.query and not p.fragment
        and bool(re.fullmatch(r'/shrine/(?:page/[1-9][0-9]*/)?',p.path)))


def _profile_url(url):
    try:p=urlsplit(url)
    except (TypeError,ValueError):return False
    return p.scheme=='https' and p.netloc=='www.m-shinsei.jp' and not p.query and not p.fragment and bool(re.fullmatch(r'/m_shrine/[^/]+/',p.path))


def _full_reading(name,raw):
    reading=normalize_reading(raw)
    for suffix,endings in [('神社',('じんじゃ','じんしゃ','しんじゃ','しんしゃ','しゃ','やしろ')),('神宮',('じんぐう','ぐう')),('大社',('たいしゃ','だいしゃ','おおやしろ')),('宮',('ぐう','みや','きゅう')),('社',('しゃ','やしろ','じんじゃ'))]:
        if name.endswith(suffix):
            if not reading.endswith(endings):raise ValueError('reading does not include written shrine suffix; no inferred completion')
            return reading
    raise ValueError('unrecognized shrine name ending; individual source review required')


def _header_pair(header,address):
    match=re.fullmatch(r'([^（）()]+)[（(]([^（）()]+)[）)]([^（）()]*)',header)
    if not match:raise ValueError('one literal name and full kana pair required')
    name,kana,tail=match.groups()
    # A suffix is accepted only as a literal locality in this card's address.
    # Removing the explicit address markers is comparison-only, never output.
    comparison=address.replace('大字','').replace('字','')
    if tail and (not re.fullmatch(r'[ぁ-ゖ\u3400-\u9fff\uf900-\ufaff々ヶケ0-9-]+',tail)
        or tail not in comparison or re.search(r'(?:神社|神宮|大社|宮|社)$',tail)):
        raise ValueError('name annotation is not an explicitly matching locality; individual review required')
    return name,kana,tail


def _in_prefecture(address):
    from njd.report import PREFECTURES
    explicit=next((p for p in PREFECTURES if address.startswith(p)),None)
    return explicit in (None,'宮崎県')


def inspect_index(page):
    if page.status!=200 or not _index_url(page.url):raise ValueError('unexpected association index URL or status')
    root=Document(page.text).root
    if not any(n.text().strip()=='宮崎県の神社' for n in root.all('h1')):raise ValueError('prefectural shrine directory heading absent')
    lists=[n for n in root.all('ul') if n.has_class('shrine_list')]
    if len(lists)!=1:raise ValueError('one shrine listing container required')
    cards=[n for n in lists[0].children if getattr(n,'tag',None)=='li']
    if not cards:raise ValueError('empty listing requires source review')
    observations=[];reviews=[]
    for index,card in enumerate(cards,1):
        locator=f'ul.shrine_list > li:nth-child({index})'
        header_nodes=list(card.all('h2'));headers=[h.text().strip() for h in header_nodes]
        graphics=[n for h in header_nodes for n in h.all() if n.tag in ('img','svg','object','iframe')]
        links=[urljoin(page.url,a.attrs.get('href','')) for a in card.all('a') if a.text().strip()=='詳細はこちら']
        fields={};invalid=False
        for group in card.all('div'):
            if not group.has_class('data_list'):continue
            labels=[n.text().strip() for n in group.all('div') if n.has_class('data_ttl')]
            values=[n for n in group.all('div') if n.has_class('data')]
            if len(labels)!=1 or len(values)!=1 or labels[0] in fields:invalid=True;continue
            if list(values[0].all('br')):invalid=True
            fields[labels[0]]=values[0].text().strip()
        context=dict(url=page.url,page_hash=page.sha256,checked_at=page.fetched_at,locator=locator)
        raw=dict(header_raw=headers[0] if len(headers)==1 else '',address_raw=fields.get('住所',''),profile_urls=links)
        if graphics:raw.update(name_rendering_status='external_glyph',rendering_nodes=[dict(tag=n.tag,attributes=n.attrs) for n in graphics])
        try:
            if graphics:raise ValueError('nontext name glyph; individual source and Unicode review required')
            if invalid or len(headers)!=1 or len(links)!=1 or not _profile_url(links[0]):raise ValueError('ambiguous title, detail link or address fields')
            address=fields.get('住所','')
            name,kana,tail=_header_pair(headers[0],address);_full_reading(name,kana)
            if not address or any(c.isspace() or ord(c)<32 or ord(c)==127 for c in address):raise ValueError('missing or multiline address; individual source review required')
            if not _in_prefecture(address):raise ValueError('explicit address prefecture differs from Miyazaki')
            if not municipality_from_address(address,'宮崎県'):raise ValueError('address does not identify a municipality; possible mislabeled source fields')
            if '郵便番号' not in fields:raise ValueError('postal metadata field missing; possible source layout change')
            if any(c.isspace() or ord(c)<32 or ord(c)==127 for c in name):raise ValueError('layout characters in name')
            observations.append(dict(**context,name_raw=name,reading_raw=kana,address_raw=address,
                header_raw=headers[0],postal_code_raw=fields['郵便番号'],profile_url=links[0],
                header_location_suffix_raw=tail,
                source_kind='shinto_association',source_publisher=PUBLISHER,
                prefecture_context_raw='宮崎県の神社',excerpt=headers[0]+' / 住所 '+address))
        except ValueError as exc:reviews.append(dict(**context,**raw,status='needs_review',reason=str(exc)))
    next_links=[urljoin(page.url,n.attrs.get('href','')) for n in root.all('a') if n.has_class('nextpostslink')]
    if len(next_links)>1 or any(not _index_url(u) or u==page.url for u in next_links):raise ValueError('ambiguous or out-of-scope next page')
    return dict(observations=observations,reviews=reviews,next_url=next_links[0] if next_links else None,cards_observed=len(cards))


def research(state_dir,client,*,limit=0,refresh=False):
    """Follow observed next links; checkpoint once per page, resume without refetch."""
    from njd.nationwide import public_failure
    if limit<0:raise ValueError('negative observation limit')
    state_dir=external_directory(state_dir);path=state_dir/'state.json'
    state=load_dataset(path) if path.exists() else dict(schema_version=1,source_key='miyazaki_youth',pages={})
    if state.get('source_key')!='miyazaki_youth':raise ValueError('state belongs to another source')
    observations=[];reviews=[];seen=set();url=INDEX;failure=False
    def checkpoint():
        complete=url is None and not failure
        result=dict(source_key='miyazaki_youth',prefecture_code='45',source_publisher=PUBLISHER,
            official_agency_listing_verified=False,observations=observations,reviews=reviews,
            pages=[dict(url=u,page_hash=v['page_hash'],fetched_at=v['fetched_at']) for u,v in state['pages'].items() if u in seen and v.get('status')=='inspected'],
            collection_complete=complete,remaining_url=url,redistribution_status='unconfirmed; no source license inferred; page bodies and images not redistributed')
        summary=dict(observations=len(observations),reviews=len(reviews),pages=len(result['pages']),complete=complete,remaining_url=url)
        state['summary']=summary;write_json(state_dir/'observations.json',result);write_json(path,state);return summary
    while url:
        if url in seen:raise ValueError('pagination cycle; source review required')
        seen.add(url);saved=state['pages'].get(url,{})
        if refresh or saved.get('status')!='inspected':
            try:
                page=client.fetch(url,refresh=refresh);inspection=inspect_index(page)
                saved=dict(status='inspected',page_hash=page.sha256,fetched_at=page.fetched_at,**inspection)
                state['pages'][url]=saved
            except (FetchError,ValueError,OSError) as exc:
                state['pages'][url]=dict(status='fetch_failed',public_reason=public_failure(exc));failure=True
                return checkpoint()
        observations.extend(saved['observations']);reviews.extend(saved['reviews']);url=saved['next_url']
        checkpoint()
        if limit and len(observations)>=limit:return checkpoint()
    return checkpoint()


def _observation_problems(ref):
    if not isinstance(ref,dict):return ['association observation must be an object']
    problems=[]
    for key in ('url','profile_url','name_raw','reading_raw','address_raw','header_raw','page_hash','checked_at','locator','excerpt'):
        if not isinstance(ref.get(key),str) or not ref[key]:problems.append('missing association observation field: '+key)
    if problems:return problems
    if not _index_url(ref['url']) or not _profile_url(ref['profile_url']):problems.append('association URL outside inspected source scope')
    if ref.get('source_kind')!='shinto_association' or ref.get('source_publisher')!=PUBLISHER:problems.append('association publisher/kind differs')
    if ref.get('license_url'):problems.append('association observation license is unconfirmed; unsupported license claim')
    if ref.get('prefecture_context_raw')!='宮崎県の神社':problems.append('association prefectural scope absent')
    try:
        if _header_pair(ref['header_raw'],ref['address_raw'])!=(ref['name_raw'],ref['reading_raw'],ref.get('header_location_suffix_raw','')):raise ValueError()
    except ValueError:problems.append('association literal name/reading/locality pair differs')
    if ref['excerpt']!=ref['header_raw']+' / 住所 '+ref['address_raw']:problems.append('association short evidence differs from raw fields')
    if not re.fullmatch('[0-9a-f]{64}',ref['page_hash']):problems.append('invalid association page hash')
    try:datetime.fromisoformat(ref['checked_at'])
    except ValueError:problems.append('invalid association inspection date')
    if not isinstance(ref.get('postal_code_raw'),str):problems.append('association raw postal metadata absent')
    if not municipality_from_address(ref['address_raw'],'宮崎県'):problems.append('association address has no municipality')
    if not _in_prefecture(ref['address_raw']):problems.append('association address prefecture differs')
    if not re.fullmatch(r'ul\.shrine_list > li:nth-child\([1-9][0-9]*\)',ref['locator']):problems.append('association source locator differs')
    if any(c.isspace() or ord(c)<32 or ord(c)==127 for c in ref['name_raw']+ref['address_raw']):problems.append('association name/address contains layout characters')
    try:_full_reading(ref['name_raw'],ref['reading_raw'])
    except ValueError:problems.append('association full literal reading absent')
    return problems


def _authority_problems(source):
    ref=source.get('authority_reference')
    if not isinstance(ref,dict):return ['association publisher authority reference absent']
    problems=[]
    if ref.get('url')!=BASE+'/aboutus/' or not isinstance(ref.get('excerpt'),str) or PUBLISHER not in ref['excerpt']:problems.append('association self-identification absent')
    if not isinstance(ref.get('page_hash'),str) or not re.fullmatch('[0-9a-f]{64}',ref['page_hash']):problems.append('association authority hash absent')
    try:datetime.fromisoformat(ref.get('checked_at',''))
    except (TypeError,ValueError):problems.append('association authority date absent')
    return problems


def inspect_authority(page):
    if page.url!=BASE+'/aboutus/' or page.status!=200:raise ValueError('unexpected association self-identification page')
    headings=[n.text().strip() for n in Document(page.text).root.all('h1')]
    if headings!=[PUBLISHER+'とは']:raise ValueError('association self-identification heading absent or changed')
    return dict(url=page.url,excerpt=headings[0],page_hash=page.sha256,checked_at=page.fetched_at)


def reference_problems(facility,entry,source):
    problems=_authority_problems(source)
    if (source.get('listing_basis')!=BASIS or facility.get('listing_basis')!=BASIS
        or source.get('source_key')!='miyazaki_youth' or facility.get('source_key')!='miyazaki_youth'
        or facility.get('prefecture_code')!='45' or source.get('prefecture_code')!='45'):
        problems.append('association source basis/scope differs')
    if facility.get('agency') or source.get('official_agency_listing_verified') is not False:problems.append('association reference must not claim agency publication')
    if facility.get('source_publisher')!=PUBLISHER or source.get('source_publisher')!=PUBLISHER:problems.append('association publisher differs')
    if source.get('redistribution_status')!='unconfirmed' or source.get('license_url'):problems.append('association source license is unconfirmed')
    # A separately validated human overlay may change the output reading. Its
    # original source observation remains literal and is checked below.
    if entry.get('reading_source_kind') not in ('association','user_review','reference','shrine_official'):problems.append('association reading source kind differs')
    ref=facility.get('source_reference');problems.extend(_observation_problems(ref))
    if not isinstance(ref,dict):return problems
    if (ref.get('name_raw'),ref.get('reading_raw'),ref.get('address_raw'),ref.get('url'),ref.get('page_hash'))!=(facility.get('name_raw'),entry.get('reading_raw'),facility.get('address'),facility.get('listing_url'),facility.get('page_hash')):
        problems.append('association observation differs from canonical fields')
    if (entry.get('reading_source_kind')=='association' and entry.get('reading_url')!=ref.get('url')
        or facility.get('native_source_id')!=ref.get('profile_url')):problems.append('association reading/profile identity differs')
    observations=facility.get('source_observations')
    if not isinstance(observations,list) or not observations or observations[0]!=ref:return problems+['association observed references absent']
    occurrences=facility.get('listing_occurrences',[])
    if not isinstance(occurrences,list):return problems+['invalid association source occurrences']
    for observation in observations:
        problems.extend(_observation_problems(observation))
        if not isinstance(observation,dict):continue
        if any(observation.get(k)!=ref.get(k) for k in ('name_raw','reading_raw','address_raw','profile_url')):problems.append('conflicting association observations require review')
        if dict(url=observation.get('url'),locator=observation.get('locator'),page_hash=observation.get('page_hash'),fetched_at=observation.get('checked_at')) not in occurrences:
            problems.append('association reference has no observed occurrence')
    return problems


def dataset_from_observations(observed,*,existing):
    """Prepare a separate reference dataset; conservatively hold possible identities.

    Existing names/addresses are comparison values only. No existing facility,
    human decision, source spelling or identifier is changed by this function.
    """
    from njd.records import build_dataset
    if observed.get('source_key')!='miyazaki_youth' or observed.get('prefecture_code')!='45':raise ValueError('association collection scope differs')
    authority=_authority_problems(observed)
    if authority:raise ValueError('; '.join(authority))
    refs=observed.get('observations')
    if not isinstance(refs,list):raise ValueError('association observations must be a list')
    names={};addresses={}
    def name_key(v):return unicodedata.normalize('NFKC',v)
    def address_key(v):
        value=re.sub(r'^〒[0-9]{3}-[0-9]{4}\s*','',unicodedata.normalize('NFKC',v)).removeprefix('宮崎県')
        value=re.sub(r'(?<=\d)[−‐‑‒–—―](?=\d)','-',value)
        value=re.sub(r'(?<=\d)番(?:地)?(?:の)?(?=\d)','-',value)
        value=re.sub(r'(?<=\d)(?:番地|番|号)$','',value)
        return value.replace('大字','')
    for f in (existing or {}).get('facilities',[]):
        if f.get('prefecture_code')!='45' or f.get('source_key')=='miyazaki_youth':continue
        names.setdefault(name_key(f['name_raw']),[]).append(f['id'])
        addresses.setdefault(address_key(f['address']),[]).append(f['id'])
    groups={};identities={};held=[]
    for ref in refs:
        problems=_observation_problems(ref)
        if problems:raise ValueError('; '.join(problems))
        groups.setdefault(ref['profile_url'],[]).append(ref)
        identities.setdefault((name_key(ref['name_raw']),address_key(ref['address_raw'])),set()).add(ref['profile_url'])
    rows=[];adopted={}
    for profile,observations in groups.items():
        ref=observations[0]
        existing_ids=sorted(set(names.get(name_key(ref['name_raw']),[])+addresses.get(address_key(ref['address_raw']),[])))
        conflict=any(any(r[k]!=ref[k] for k in ('name_raw','reading_raw','address_raw')) for r in observations)
        repeated=len(identities[(name_key(ref['name_raw']),address_key(ref['address_raw']))])>1
        if existing_ids or conflict or repeated:
            reason=('possible existing facility; name/address identity review required' if existing_ids else 'conflicting or duplicated association profile identity; individual review required')
            held.extend(dict(status='pending',reason=reason,existing_facility_ids=existing_ids,observation=copy.deepcopy(r)) for r in observations)
            continue
        adopted[profile]=observations
        for r in observations:
            rows.append(dict(name=r['name_raw'],reading_raw=r['reading_raw'],address=r['address_raw'],url=r['url'],source_id=profile,
                fetched_at=r['checked_at'],page_hash=r['page_hash'],locator=r['locator'],evidence=r['excerpt']))
    metadata={k:copy.deepcopy(v) for k,v in observed.items() if k not in ('observations','reviews','source_publisher','source_key','prefecture_code','official_agency_listing_verified','redistribution_status')}
    metadata.update(listing_basis=BASIS,source_publisher=PUBLISHER,authority_status='reference_source',official_agency_listing_verified=False,
        redistribution_status='unconfirmed',source_rows_observed=len(refs)+len(observed.get('reviews',[])),
        observation_reviews=copy.deepcopy(observed.get('reviews',[])),identity_reviews=held,
        coverage='Observed youth-association shrine directory only; not shrine-agency publication or all shrines in Miyazaki.')
    data=build_dataset('miyazaki_youth','45','宮崎県','',rows,metadata=metadata);data['collection'].pop('agency',None)
    for f in data['facilities']:
        f.pop('agency',None);f.update(listing_basis=BASIS,source_publisher=PUBLISHER,source_reference=copy.deepcopy(adopted[f['native_source_id']][0]),source_observations=copy.deepcopy(adopted[f['native_source_id']]))
    for e in data['entries']:e.update(reading_source_kind='association',listing_basis=BASIS)
    from njd.validation import blocking_problems
    issues=blocking_problems(data)
    if issues:raise ValueError('association dataset validation failed: '+str(issues[:3]))
    return data


def audit_profile(page,observation):
    """Compare the separate detail page to a listing observation, without repair."""
    if page.status!=200 or page.url!=observation.get('profile_url') or not _profile_url(page.url):raise ValueError('unexpected association profile response')
    root=Document(page.text).root
    headings=[n.text().strip() for n in root.all('h2')]
    addresses=[]
    for n in root.all('div'):
        if not n.has_class('data_list'):continue
        labels=[v.text().strip() for v in n.all('div') if v.has_class('data_ttl')]
        values=[v.text().strip() for v in n.all('div') if v.has_class('data')]
        if labels==['住所']:addresses.extend(values)
    matched=headings.count(observation['header_raw'])==1 and addresses==[observation['address_raw']]
    return dict(url=page.url,page_hash=page.sha256,checked_at=page.fetched_at,
        index_url=observation['url'],index_locator=observation['locator'],index_page_hash=observation['page_hash'],
        status='matched' if matched else 'mismatch',headings_raw=headings,address_fields_raw=addresses,
        verification_scope='same-publisher index/detail consistency; not an independent authority or real IME import')


def audit_sample(observations,state_dir,client,*,maximum=50,refresh=False):
    from njd.nationwide import public_failure
    if not 1<=maximum<=100:raise ValueError('profile audit sample must be between 1 and 100')
    count=min(maximum,len(observations));selected=([observations[0]] if count==1 else
        [observations[i*(len(observations)-1)//(count-1)] for i in range(count)] if count else [])
    results=[];path=external_directory(state_dir)/'profile-audit.json'
    def checkpoint():
        report=dict(requested=maximum,selected=count,inspected=len(results),
            matched=sum(v['status']=='matched' for v in results),mismatches=sum(v['status']=='mismatch' for v in results),
            failed=sum(v['status']=='fetch_failed' for v in results),results=results)
        write_json(path,report);return report
    for observation in selected:
        try:result=audit_profile(client.fetch(observation['profile_url'],refresh=refresh),observation)
        except (FetchError,ValueError,OSError) as exc:result=dict(url=observation['profile_url'],status='fetch_failed',public_reason=public_failure(exc))
        results.append(result);checkpoint()
    return checkpoint()


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--state-dir',required=True);p.add_argument('--cache-dir',default=str(Path.home()/'.cache/national-jinja-dictionary/http'))
    p.add_argument('--limit',type=int,default=0);p.add_argument('--offline',action='store_true');p.add_argument('--refresh',action='store_true')
    p.add_argument('--audit-profiles',type=int,default=0,help='compare an evenly distributed sample of 1-100 actual detail pages')
    p.add_argument('--prepare-with-data-dir',help='prepare candidate.json against existing canonical data; never adopt automatically')
    args=p.parse_args(argv)
    if args.offline and args.refresh:p.error('--offline and --refresh cannot be combined')
    if args.limit<0 or args.audit_profiles and not 1<=args.audit_profiles<=100:p.error('invalid collection limit or profile sample size')
    client=Client(external_directory(args.cache_dir),offline=args.offline,interval=2,timeout=30,retries=2)
    print(research(args.state_dir,client,limit=args.limit,refresh=args.refresh))
    if args.audit_profiles:
        observed=load_dataset(external_directory(args.state_dir)/'observations.json')
        result=audit_sample(observed['observations'],args.state_dir,client,maximum=args.audit_profiles,refresh=args.refresh)
        print({k:v for k,v in result.items() if k!='results'})
    if args.prepare_with_data_dir:
        from njd.nationwide import merge_collections
        directory=external_directory(args.state_dir);observed=load_dataset(directory/'observations.json')
        observed['authority_reference']=inspect_authority(client.fetch(BASE+'/aboutus/',refresh=args.refresh))
        robot=client.fetch(BASE+'/robots.txt')
        observed['robots_reference']=dict(url=robot.url,status=robot.status,page_hash=robot.sha256,checked_at=robot.fetched_at)
        observed['terms_urls']=[]
        observed['data_use_conditions']='再利用許諾・利用条件は未確認。事実項目と短い照合記録のみ保存。本文・画像は再配布せず、MITやWikipediaのライセンスを適用しない。'
        audit_path=directory/'profile-audit.json'
        if audit_path.exists():
            audit=load_dataset(audit_path)
            indexes={(r['profile_url'],r['url'],r['locator'],r['page_hash']) for r in observed['observations']}
            if all(r.get('status')=='matched' and (r.get('url'),r.get('index_url'),r.get('index_locator'),r.get('index_page_hash')) in indexes for r in audit.get('results',[])):
                observed['profile_audit']=audit
            else:raise ValueError('profile audit is incomplete, mismatched or stale; review before candidate preparation')
        candidate=dataset_from_observations(observed,existing=merge_collections(args.prepare_with_data_dir))
        write_json(directory/'candidate.json',candidate)
        print(dict(candidate_facilities=len(candidate['facilities']),identity_reviews=len(candidate['collection']['identity_reviews']),canonical_update='not applied'))

if __name__=='__main__':main()
