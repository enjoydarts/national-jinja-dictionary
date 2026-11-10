"""Research NTA registered-name readings; external proposals never edit canonical data."""
import argparse
import copy
import csv
from datetime import datetime, timezone
import hashlib
from http.cookiejar import CookieJar
import io
import json
from pathlib import Path
import re
from urllib.error import HTTPError
from urllib.parse import urlencode, urljoin, urlsplit
from urllib.request import Request, build_opener, HTTPCookieProcessor
import zipfile

from njd.corrections import correction_problems, _reference_matches
from njd.http import Client, FetchError, NoRedirect
from njd.normalize import normalize_reading
from njd.locations import raw_address
from njd.report import PREFECTURES
from njd.storage import load_dataset, write_json
from njd.wikipedia import Document, external_directory, pending_targets

BASE='https://www.houjin-bangou.nta.go.jp'
LANDING=BASE+'/download/zenken/'
TERMS=BASE+'/riyokiyaku/'
PDL='https://www.digital.go.jp/resources/open_data/public_data_license_v1.0'
TOKEN='jp.go.nta.houjin_bangou.framework.web.common.CNSFWTokenProcessor.request.token'
FIELDS='sequenceNumber corporateNumber process correct updateDate changeDate name nameImageId kind prefectureName cityName streetNumber addressImageId prefectureCode cityCode postCode addressOutside addressOutsideImageId closeDate closeCause successorCorporateNumber changeCause assignmentDate latest enName enPrefectureName enCityName enAddressOutside furigana hihyoji'.split()
MAX_ZIP=64*1024*1024
MAX_UNCOMPRESSED=512*1024*1024
MATCHING_PROFILE='full-name-address-literal-kana-v2-religious-prefix'

# The opened three-agency notice explicitly excludes the legal-form portion
# from registered furigana. This is a name-comparison rule, not kana inference.
LEGAL_PREFIX_RULE=dict(
    url=BASE+'/oshirase/h30/images/furigana_kouhyou.pdf',
    page_hash='edcab3f227f44e66a3b2974fa38d70f11959f4d9cf2979e3606e6a6497232c8f',
    fetched_at='2026-11-10T13:25:31.137436+00:00',
    locator='p.1 section 2 フリガナの記載について, second bullet',
    excerpt='フリガナは、法人の種類を表す部分',
    publisher='内閣官房・法務省・国税庁',effective_date='2018-03-12')


def legal_prefix_shrine_name(fields):
    """One literal 宗教法人 prefix, active registered法人399; no other edits."""
    required=('name','furigana','kind','latest','process','closeDate','hihyoji',
              'prefectureName','cityName','streetNumber','corporateNumber')
    if not isinstance(fields,dict) or any(not isinstance(fields.get(k),str) for k in required):return None
    if (fields['kind']!='399' or fields['latest']!='1' or fields['process']=='99'
        or fields['closeDate'] or fields['hihyoji']!='0'
        or not re.fullmatch('[0-9]{13}',fields['corporateNumber'])):return None
    prefix='宗教法人';name=fields['name']
    if not name.startswith(prefix):return None
    core=name[len(prefix):]
    # Identity matching must include competitors with missing/unusable kana.
    # Reading adoption is decided only after all active matches are counted.
    if not core or core.startswith(prefix) or re.search(r'\s',core):return None
    return core


def registered_name_identity(fields):
    core=legal_prefix_shrine_name(fields)
    if core is None:return None
    return dict(rule='literal_religious_corporation_prefix',removed_prefix='宗教法人',
        registered_name_raw=fields['name'],shrine_name_raw=core,
        rule_reference=copy.deepcopy(LEGAL_PREFIX_RULE))


def bound_registered_shrine_name(ref):
    """Validate the complete comparison witness without changing source text."""
    if not isinstance(ref,dict) or ref.get('source_kind')!='government_corporate_register' or ref.get('url')!=BASE+'/download/zenken/index.html':return None
    fields=ref.get('source_fields');proof=registered_name_identity(fields)
    if proof is None or ref.get('registered_name_identity')!=proof:return None
    if not fields['furigana'] or fields['furigana'].startswith('シュウキョウホウジン'):return None
    if any(ref.get(k)!=v for k,v in dict(name_raw=fields['name'],reading_raw=fields['furigana'],
        address_raw=fields['prefectureName']+fields['cityName']+fields['streetNumber'],
        corporate_number=fields['corporateNumber']).items()):return None
    return proof['shrine_name_raw']


def discover(html,codes):
    """Read actual Unicode section/form; never invent a static archive URL."""
    root=Document(html).root
    forms=[n for n in root.all('form') if n.attrs.get('id')=='appForm']
    if len(forms)!=1 or forms[0].attrs.get('method','').lower()!='post':raise ValueError('official download form absent')
    url=urljoin(LANDING,forms[0].attrs.get('action',''))
    if url!=BASE+'/download/zenken/index.html':raise ValueError('unexpected download action')
    match=re.search(r'CSV形式・Unicode</h2>(.*?)XML形式・Unicode</h2>',html,re.S)
    if not match:raise ValueError('Unicode CSV section absent')
    section=match[1];date=re.search(r'令和(\d+)年(\d+)月(\d+)日更新',section)
    if not date:raise ValueError('snapshot date absent')
    year,month,day=map(int,date.groups());snapshot=datetime(year+2018,month,day).strftime('%Y%m%d')
    by_name={name:f'{i:02}' for i,name in enumerate(PREFECTURES,1)};result={}
    for dl in Document(section).root.all('dl'):
        dt=list(dl.all('dt'));dd=list(dl.all('dd'))
        if len(dt)!=1 or len(dd)!=1:continue
        code=by_name.get(dt[0].text().strip())
        if code not in codes:continue
        links=[]
        for a in dd[0].all('a'):
            m=re.fullmatch(r'return doDownload\((\d+)\);',a.attrs.get('onclick','').strip())
            if m:links.append(dict(file_id=m[1],display_size=a.text().strip()))
        if not links or len({x['file_id'] for x in links})!=len(links):raise ValueError('prefecture archive absent or ambiguous: '+code)
        files=[dict(url=url,snapshot=snapshot,**x) for x in links]
        result[code]=dict(files=files,**files[0])
    return result


class CorporateClient(Client):
    """Normal public session form transport; bounded ZIP read, same robots/rate policy."""
    def __init__(self,cache_dir,**kwargs):
        cache_dir=external_directory(cache_dir)
        self.opener=build_opener(NoRedirect(),HTTPCookieProcessor(CookieJar()))
        super().__init__(cache_dir,transport=self._transport,**kwargs)

    def _transport(self,url,timeout,user_agent,*,method='GET',data=None,content_type=None):
        headers={'User-Agent':user_agent}
        if content_type:headers['Content-Type']=content_type
        try:response=self.opener.open(Request(url,headers=headers,data=data,method=method),timeout=timeout)
        except HTTPError as exc:response=exc
        with response:
            body=response.read(MAX_ZIP+1)
            if len(body)>MAX_ZIP:raise FetchError('prefecture response exceeds 64 MiB')
            return response.status,{k.lower():v for k,v in response.headers.items()},body

    def _manifest_path(self,meta):
        # Stable monthly identity, independent of ephemeral session token.
        key=hashlib.sha256((meta['url']+'\n'+meta['file_id']+'\n'+meta['snapshot']).encode()).hexdigest()
        return self.cache/'corporate-downloads'/(key+'.json')

    def store_download(self,meta,page):
        if page.status!=200 or not page.body.startswith(b'PK'):raise FetchError('not a successful ZIP response')
        self._save(page)
        descriptor=dict(url=page.url,cache_identity=page.cache_identity,sha256=page.sha256,checked_at=page.fetched_at,
                        file_id=meta['file_id'],snapshot=meta['snapshot'])
        write_json(self._manifest_path(meta),descriptor)
        return page

    def download(self,meta,*,refresh=False):
        if meta.get('prefecture_code') not in {f'{i:02}' for i in range(1,48)} or meta.get('url')!=BASE+'/download/zenken/index.html':raise ValueError('only actual domestic prefecture downloads are allowed')
        path=self._manifest_path(meta)
        if path.exists() and not refresh:
            d=load_dataset(path);p=self._load(d['url'],d['cache_identity'])
            if p and p.sha256==d['sha256']:return p
            raise FetchError('monthly archive cache missing or mismatched')
        if self.offline:raise FetchError('offline monthly archive cache miss')
        # A fresh GET establishes cookies/token via the ordinary public form.
        landing=self.fetch(LANDING,refresh=True)
        discovered=discover(landing.text,[meta['prefecture_code']]).get(meta['prefecture_code'])
        if not discovered or not any(all(part[k]==meta[k] for k in ('file_id','snapshot','url')) for part in discovered['files']):raise FetchError('download inventory changed; rerun discovery')
        root=Document(landing.text).root
        tokens=[n.attrs.get('value') for n in root.all('input') if n.attrs.get('name')==TOKEN]
        if len(tokens)!=1 or not tokens[0]:raise FetchError('normal session token absent')
        data=urlencode({'event':'download','selDlFileNo':meta['file_id'],TOKEN:tokens[0]}).encode()
        self._policy(meta['url'])
        page=self._raw(meta['url'],method='POST',request_data=data,content_type='application/x-www-form-urlencoded',refresh=True)
        if page.status in (301,302,303):
            target=urljoin(page.url,page.headers.get('location',''))
            if urlsplit(target).netloc!=urlsplit(BASE).netloc:raise FetchError('unexpected download redirect host')
            page=self.fetch(target,refresh=refresh)
        elif page.status in (307,308):raise FetchError('POST-preserving redirect requires inspection')
        return self.store_download(meta,page)


def rows_from_archive(body,code,snapshot,*,max_uncompressed=MAX_UNCOMPRESSED):
    """Stream one bounded headerless CSV member; no filesystem extraction."""
    if len(body)>MAX_ZIP:raise ValueError('archive exceeds 64 MiB')
    with zipfile.ZipFile(io.BytesIO(body)) as archive:
        infos=archive.infolist()
        if len(infos)>8 or sum(n.file_size for n in infos)>max_uncompressed:raise ValueError('archive uncompressed limit exceeded')
        csvs=[n for n in infos if n.filename.endswith('.csv')]
        if len(csvs)!=1:raise ValueError('single CSV member required')
        member=csvs[0]
        if not re.fullmatch(re.escape(code)+r'_[a-z]+_all_'+re.escape(snapshot)+r'(?:_[0-9]{2})?\.csv',member.filename):raise ValueError('CSV member snapshot/prefecture mismatch')
        if member.flag_bits&1:raise ValueError('encrypted archive unsupported')
        with archive.open(member) as stream,io.TextIOWrapper(stream,encoding='utf-8-sig',errors='strict',newline='') as text:
            for index,row in enumerate(csv.reader(text,strict=True),1):
                if len(row)!=30:raise ValueError('CSV must have 30 headerless fields')
                values=dict(zip(FIELDS,row))
                if not re.fullmatch(r'\d{13}',values['corporateNumber']):raise ValueError('invalid corporate number/header row')
                yield member.filename,index,values


def _reading(name,raw):
    if not raw:raise ValueError('registered furigana absent')
    if not re.fullmatch(r'[ァ-ヶー]+',raw):raise ValueError('registered furigana is not literal katakana')
    if re.search(r'ジンジヤ|ジンギユウ|ジングウシヤ|タイシヤ|ダイシヤ|キユウ',raw):raise ValueError('large-kana ambiguity requires independent reading evidence')
    reading=normalize_reading(raw)
    for suffix,endings in [('神社',('じんじゃ','じんしゃ','しんじゃ','しんしゃ')),('神宮',('じんぐう',)),('大社',('たいしゃ','だいしゃ','おおやしろ')),('宮',('ぐう','みや','きゅう')),('社',('しゃ','やしろ'))]:
        if name.endswith(suffix):
            if not reading.endswith(endings):raise ValueError('registered reading omits full shrine name ending or requires review')
            break
    return reading


def _bound(row,target):
    f=target['facility'];e=target['entry'];address=row['prefectureName']+row['cityName']+row['streetNumber']
    # Unlike the general overlay matcher, a locality prefix is never enough here.
    if row['name']!=f['listed_name'] and legal_prefix_shrine_name(row)!=f['listed_name']:return False
    if not re.search(r'[0-9０-９]',f.get('address','')):return False
    if row['prefectureCode']!=f['prefecture_code'] or row['prefectureName']!=f['prefecture']:return False
    # The extracted name is used only for this full-address comparison. Raw
    # legal names and the exact rule packet are preserved in the proposal.
    return _reference_matches(dict(name_raw=f['listed_name'],address_raw=address),f,e,{})


def image_review_problems(ref):
    """Bind an individual visual inspection to the exact Unicode CSV row.

    Images never supply or repair a pronunciation. The literal kana remains
    in the registered CSV field, and ordinary automatic extraction still holds
    image-backed rows unless an explicit inspection packet is supplied.
    """
    fields=ref.get('source_fields',{})
    if not isinstance(fields,dict):return ['invalid registered source fields'] if ref.get('image_reviews') else []
    needed={key:fields.get(key) for key in ('nameImageId','addressImageId') if fields.get(key)}
    packet=ref.get('image_reviews')
    if not needed:return ['image review without a registered image ID'] if packet else []
    if not isinstance(packet,dict) or set(packet)!=set(needed):return ['registered image IDs require individually inspected image references']
    if any(not isinstance(fields.get(k),str) for k in ('name','furigana','corporateNumber','prefectureName','cityName','streetNumber')):return ['invalid image-backed CSV identity field types']
    problems=[];address=''.join(fields[k] for k in ('prefectureName','cityName','streetNumber'))
    if ref.get('url')!=BASE+'/download/zenken/index.html':problems.append('image-backed CSV reference is not the inspected official archive endpoint')
    if not re.fullmatch('[0-9]{13}',fields['corporateNumber']):problems.append('image-backed corporate number invalid')
    if fields.get('latest')!='1' or fields.get('process')=='99' or fields.get('closeDate') or fields.get('hihyoji')!='0':problems.append('image-backed registry identity is historical, closed or hidden')
    raw_pairs={'name_raw':fields['name'],'reading_raw':fields['furigana'],'address_raw':address,'corporate_number':fields['corporateNumber']}
    if any(ref.get(key)!=value for key,value in raw_pairs.items()):problems.append('image-backed reference differs from literal CSV identity or kana')
    if not isinstance(ref.get('page_hash'),str) or not re.fullmatch('[0-9a-f]{64}',ref['page_hash']):problems.append('image-backed archive hash absent')
    if not isinstance(ref.get('snapshot'),str) or not re.fullmatch('[0-9]{8}',ref['snapshot']):problems.append('image-backed archive snapshot absent')
    for field,image_id in needed.items():
        review=packet[field]
        if not isinstance(review,dict):problems.append('invalid registered image inspection');continue
        expected=dict(image_id=image_id,url=BASE+'/image?imageid='+str(image_id),corporate_number=fields.get('corporateNumber'),
            archive_page_hash=ref.get('page_hash'),snapshot=ref.get('snapshot'),csv_row=ref.get('csv_row'),
            source_name_raw=fields.get('name'),source_address_raw=address)
        if any(review.get(k)!=v for k,v in expected.items()):problems.append('registered image reference differs from its exact CSV record')
        if not isinstance(image_id,str) or not re.fullmatch('[0-9]{8}',image_id):problems.append('unrecognized registered image ID')
        if type(review.get('csv_row')) is not int or review['csv_row']<1:problems.append('registered image CSV row absent')
        if review.get('method')!='visual_inspection_of_official_image' or not isinstance(review.get('note'),str) or not review['note']:problems.append('individual image inspection method/note absent')
        if not isinstance(review.get('page_hash'),str) or not re.fullmatch('[0-9a-f]{64}',review['page_hash']):problems.append('inspected image hash absent')
        for key in ('fetched_at','checked_at'):
            try:
                if datetime.fromisoformat(review.get(key,'')).tzinfo is None:raise ValueError()
            except (TypeError,ValueError):problems.append('registered image '+key+' absent')
    return problems


def _proposal(target,row,member,index,meta,*,image_reviews=None):
    f=target['facility'];e=target['entry'];raw=row['furigana'];reading=_reading(row['name'],raw)
    if row['name']!=f['listed_name'] and raw.startswith('シュウキョウホウジン'):
        raise ValueError('registered kana includes legal-form prefix; no automatic kana removal')
    if (row['nameImageId'] or row['addressImageId']) and not image_reviews:raise ValueError('image-backed source characters require review')
    address=row['prefectureName']+row['cityName']+row['streetNumber']
    excerpt=row['name']+' / '+raw+' / '+address
    ref=dict(url=meta['url'],title='国税庁法人番号公表サイト 全件データ',source_kind='government_corporate_register',
        name_raw=row['name'],reading_raw=raw,address_raw=address,excerpt=excerpt,checked_at=meta['checked_at'],page_hash=meta['page_hash'],
        file_id=meta['file_id'],snapshot=meta['snapshot'],zip_member=member,csv_row=index,corporate_number=row['corporateNumber'],source_fields=row,
        locator=f"Unicode CSV file ID {meta['file_id']}; {member}; row {index}; corporateNumber={row['corporateNumber']}",
        license_url=PDL,terms_url=TERMS,attribution='出典：国税庁法人番号公表サイト（国税庁）（'+meta['url']+'）',
        processed_notice='国税庁法人番号公表サイト（国税庁）を加工して作成。カタカナをひらがなに機械変換。',
        verification_method='exact registered name and bound full numeric address; literal registered kana; no inferred small kana')
    if image_reviews is not None:ref['image_reviews']=copy.deepcopy(image_reviews)
    if row['name']!=f['listed_name']:
        proof=registered_name_identity(row)
        if proof is not None:ref['registered_name_identity']=proof
    proposal=dict(status='verified',facility_id=f['id'],expected_source_hash=e.get('source_hash'),
        original=dict(name_raw=f.get('name_raw'),reading_raw=e.get('reading_raw'),address=raw_address(f),listing_url=f.get('listing_url')),
        changes=dict(reading=reading),references=[ref],reason='Registered full-name furigana from inspected NTA prefecture archive; exact legal name and full address bound.',
        identity_match=dict(agency_name=f['listed_name'],reference_name=row['name'],agency_address=raw_address(f),effective_address=f['address'],reference_address=address))
    problems=correction_problems(proposal,f,e,target['source'])
    if problems:raise ValueError('; '.join(problems))
    return proposal


def proposals_for_archive(body,targets,meta,*,max_uncompressed=MAX_UNCOMPRESSED):
    return proposals_for_archives([(body,meta)],targets,max_uncompressed=max_uncompressed)


def proposals_for_archives(parts,targets,*,max_uncompressed=MAX_UNCOMPRESSED):
    """Combine all actual prefecture parts before deciding uniqueness."""
    by_name={}
    for target in targets:by_name.setdefault(target['facility']['listed_name'],[]).append(target)
    found={t['entry']['id']:[] for t in targets};duplicates=set();seen=set()
    for body,meta in parts:
        code=targets[0]['facility']['prefecture_code'] if targets else meta.get('prefecture_code')
        for member,index,row in rows_from_archive(body,code,meta['snapshot'],max_uncompressed=max_uncompressed):
            # Active identity only. Historical/closed readings are not supplements.
            if row['latest']!='1' or row['process']=='99' or row['closeDate'] or row['hihyoji']!='0':continue
            number=row['corporateNumber']
            if number in seen:duplicates.add(number)
            seen.add(number)
            names={row['name']};core=legal_prefix_shrine_name(row)
            if core is not None:names.add(core)
            for name in sorted(names):
                for target in by_name.get(name,[]):
                    if _bound(row,target):found[target['entry']['id']].append((row,member,index,meta))
    proposals={};pending={}
    for target in targets:
        eid=target['entry']['id'];matches=found[eid]
        if len(matches)!=1 or (matches and matches[0][0]['corporateNumber'] in duplicates):
            pending[eid]='no unique active exact name/full-address corporate identity';continue
        row,member,index,meta=matches[0]
        try:proposals[eid]=_proposal(target,row,member,index,meta)
        except ValueError as exc:pending[eid]=str(exc)
    return proposals,pending


def research(data_dir,state_dir,codes,client,*,limit=0,refresh=False):
    if limit<0:raise ValueError('limit must be nonnegative')
    state_dir=external_directory(state_dir);state_path=state_dir/'state/progress.json'
    state=load_dataset(state_path) if state_path.exists() else dict(schema_version=1,prefectures={})
    all_targets=pending_targets(data_dir,[f'{i:02}' for i in range(1,48)])
    active={t['entry']['id']:t for t in all_targets};targets=[t for t in all_targets if t['facility']['prefecture_code'] in codes]
    path=state_dir/'proposals.json';old=load_dataset(path).get('entries',{}) if path.exists() else {}
    proposals={eid:p for eid,p in old.items() if eid in active and not correction_problems(p,active[eid]['facility'],active[eid]['entry'],active[eid]['source'])}
    attempted=0;errors={};selected_codes=sorted({t['facility']['prefecture_code'] for t in targets})
    if not selected_codes:
        write_json(path,dict(schema_version=1,entries=proposals));return dict(proposals=len(proposals),prefectures_attempted=0,errors={})
    landing=client.fetch(LANDING,refresh=refresh);inventory=discover(landing.text,selected_codes)
    completed=set()
    for code in selected_codes:
        items=[t for t in targets if t['facility']['prefecture_code']==code]
        fingerprints={t['entry']['id']:hashlib.sha256(json.dumps(t,ensure_ascii=False,sort_keys=True).encode()).hexdigest() for t in items}
        saved=state['prefectures'].get(code,{})
        identity=lambda part:tuple(part.get(k) for k in ('url','file_id','snapshot'))
        current_parts=inventory.get(code,{}).get('files',[])
        reusable=(not refresh and saved.get('status')=='inspected' and saved.get('matching_profile')==MATCHING_PROFILE and saved.get('fingerprints')==fingerprints
            and current_parts and [identity(p) for p in saved.get('files',[])]==[identity(p) for p in current_parts]
            and saved.get('proposals')==sum(t['entry']['id'] in proposals for t in items))
        if reusable:
            completed.add(code);continue
        for t in items:proposals.pop(t['entry']['id'],None)
        if limit and attempted>=limit:continue
        attempted+=1
        try:
            if code not in inventory:raise ValueError('prefecture archive not found')
            observed=[]
            def parts():
                for part in inventory[code]['files']:
                    meta=dict(part,prefecture_code=code);page=client.download(meta,refresh=refresh)
                    meta.update(checked_at=page.fetched_at,page_hash=page.sha256);observed.append(meta)
                    yield page.body,meta
            accepted,pending=proposals_for_archives(parts(),items)
            proposals.update(accepted);state['prefectures'][code]=dict(status='inspected',matching_profile=MATCHING_PROFILE,files=observed,fingerprints=fingerprints,proposals=len(accepted),pending=pending)
            completed.add(code)
        except (FetchError,ValueError,OSError,UnicodeError,zipfile.BadZipFile,csv.Error) as exc:
            # Exception messages never contain the token-bearing request body.
            errors[code]=type(exc).__name__+': '+str(exc);state['prefectures'][code]=dict(status='failed',reason=errors[code])
        write_json(path,dict(schema_version=1,entries=proposals));write_json(state_path,state)
    result=dict(proposals=len(proposals),prefectures_attempted=attempted,errors=errors,remaining_prefectures=len(set(selected_codes)-completed),
        coverage='pending agency-listed facilities only; exact corporate name/full-address match; no whole-prefecture shrine completeness claim')
    state['summary']=result;write_json(state_path,state);return result


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prefecture',required=True,choices=['all']+[f'{i:02}' for i in range(1,48)])
    parser.add_argument('--data-dir',type=Path,default=Path('data'));parser.add_argument('--state-dir',type=Path,required=True)
    parser.add_argument('--cache-dir',type=Path,default=Path.home()/'.cache/national-jinja-dictionary/corporate')
    parser.add_argument('--offline',action='store_true');parser.add_argument('--refresh',action='store_true')
    parser.add_argument('--limit',type=int,default=0,help='maximum prefecture archives inspected this run; 0 means all selected')
    args=parser.parse_args(argv);codes=[f'{i:02}' for i in range(1,48)] if args.prefecture=='all' else [args.prefecture]
    result=research(args.data_dir,args.state_dir,codes,CorporateClient(args.cache_dir,offline=args.offline),limit=args.limit,refresh=args.refresh)
    print(json.dumps(result,ensure_ascii=False,sort_keys=True));return 0

if __name__=='__main__':raise SystemExit(main())
