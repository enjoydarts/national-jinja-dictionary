"""Observed Hyogo map XML and code-bound factual profile headers only.

The selected rectangle is a search input, not an observed UI viewport or a
verified prefectural boundary. Neither an API cap nor site-wide completeness
has been established. No article prose, aliases or photographs are extracted.
"""
import copy
import re
from urllib.parse import parse_qsl, unquote, urljoin, urlsplit
from xml.etree import ElementTree as ET
from njd.adapters.central import Document, Node, decode_html
from njd.http import FetchError
from njd.normalize import normalize_reading
from njd.records import build_dataset

ORIGIN='https://www.hyogo-jinjacho.com'
INDEX=ORIGIN+'/data/xml.php?ne_lat=36&sw_lat=34&ne_lng=136&sw_lng=134'
SMALL=ORIGIN+'/data/xml.php?ne_lat=34.691492&sw_lat=34.671492&ne_lng=135.186149&sw_lng=135.166149'
PROTOCOL_URL=ORIGIN+'/js/formsearch.js'
OBSERVED_QUERIES={tuple(sorted(parse_qsl(urlsplit(u).query))) for u in (INDEX,SMALL)}


class _NameDocument(Document):
    def handle_starttag(self,tag,attrs):
        original=self.get_starttag_text()
        super().handle_starttag(tag,attrs)
        if tag=='img':self.stack[-1].children[-1].original_start_tag=original


def _source_name(node):
    if node.tag=='img':return node.original_start_tag
    return ''.join(_source_name(c) if isinstance(c,Node) else c for c in node.children)


def _url(value,base=INDEX):
    raw=urlsplit(value)
    if any(x in ('.','..') for x in unquote(raw.path).split('/')) or '\\' in unquote(value):raise ValueError('Hyogo path traversal')
    url=urljoin(base,value);p=urlsplit(url)
    if p.scheme!='https' or p.netloc!='www.hyogo-jinjacho.com' or p.fragment:raise ValueError('Hyogo URL outside official origin')
    if p.path=='/data/xml.php':
        pairs=parse_qsl(p.query,keep_blank_values=True)
        if len(dict(pairs))!=len(pairs) or tuple(sorted(pairs)) not in OBSERVED_QUERIES:raise ValueError('unobserved Hyogo map query')
    elif not re.fullmatch(r'/data/[0-9]{7}\.html',p.path) or p.query:raise ValueError('unexpected Hyogo profile path/query')
    return url


def _identity(url):
    p=urlsplit(_url(url));return p.path,tuple(sorted(parse_qsl(p.query,keep_blank_values=True)))


def _fetch(client,url):
    url=_url(url);requested=_identity(url);seen=set()
    for _ in range(6):
        identity=_identity(url)
        if identity!=requested:raise ValueError('Hyogo redirect changes requested map/profile identity')
        if identity in seen:raise FetchError('Hyogo redirect loop')
        seen.add(identity)
        if hasattr(client,'_raw'):
            refresh=getattr(client,'refresh_requested',False)
            client._policy(url,refresh=refresh);page=client._raw(url,refresh=refresh)
        else:page=client.fetch(url)
        if _identity(page.url)!=requested:raise ValueError('Hyogo response changes requested map/profile identity')
        if page.status in (301,302,303,307,308):
            if not page.headers.get('location'):raise FetchError('Hyogo redirect missing location')
            target=_url(page.headers['location'],page.url)
            if _identity(target)!=requested:raise ValueError('Hyogo redirect changes requested map/profile identity')
            url=target;continue
        if page.status!=200:raise FetchError('Hyogo HTTP '+str(page.status))
        # https://developers.cloudflare.com/cloudflare-challenges/challenge-types/challenge-pages/detect-response/
        if any(k.lower()=='cf-mitigated' and v.lower().strip()=='challenge' for k,v in page.headers.items()):
            raise FetchError('Hyogo access/authentication challenge')
        text=decode_html(page)
        if re.search(r'type\s*=\s*[\"\']?password\b|captcha|access denied|cloudflare[^\n]{0,120}challenge',text,re.I):raise FetchError('Hyogo access/authentication challenge')
        footers=' '.join(f.text() for f in Document(text).root.find('footer'))
        if re.search(r'(?:情報|データ|自動取得|自動収集|自動アクセス)[^。\n]{0,80}(?:禁止|禁じ|無断転載)',footers):
            raise FetchError('Hyogo broader data/access restriction requires review')
        return page
    raise FetchError('too many Hyogo redirects')


def parse_xml(page):
    if urlsplit(_url(page.url)).path!='/data/xml.php' or page.status!=200:raise ValueError('unexpected Hyogo XML endpoint/status')
    text=decode_html(page)
    if re.search(r'<!DOCTYPE|<!ENTITY',text,re.I):raise ValueError('unexpected XML document/entity declaration')
    try:root=ET.fromstring(text)
    except ET.ParseError as exc:raise ValueError('invalid Hyogo map XML') from exc
    if root.tag!='Locations' or any(x.tag!='Locate' for x in root):raise ValueError('Hyogo Locations/Locate structure absent')
    rows=[]
    for index,item in enumerate(root,1):
        fields={c.tag:c.text or '' for c in item}
        if len(fields)!=len(item) or set(fields)!={'code','name','place','lat','lng'} or any(len(c) for c in item):raise ValueError('Hyogo Locate fields changed')
        code=fields['code']
        if not re.fullmatch(r'[0-9]{7}',code):raise ValueError('invalid Hyogo native code')
        if any(not re.fullmatch(r'-?\d+(?:\.\d+)?',fields[k]) for k in ('lat','lng')):raise ValueError('invalid explicit map coordinates')
        binding=dict(url=page.url,page_hash=page.sha256,fetched_at=page.fetched_at,locator=f'Locations/Locate[{index}]',
            code_raw=code,name_raw=fields['name'],address_raw=fields['place'],protocol_url=PROTOCOL_URL,href_derivation='data/ + actual Locate code + .html')
        rows.append(dict(source_id=code,name=fields['name'],address=fields['place'],url=ORIGIN+'/data/'+code+'.html',xml_source=binding))
    return rows


def _reading_reason(name,raw):
    try:kana=normalize_reading(raw)
    except ValueError:return 'missing or nonliteral full agency reading'
    endings=[('神社',('じんじゃ','じんしゃ','しんじゃ','しんしゃ','しゃ')),('神宮',('じんぐう',)),('大社',('たいしゃ','だいしゃ','おおやしろ')),('宮',('ぐう','みや','きゅう')),('社',('しゃ','やしろ'))]
    for suffix,allowed in endings:
        if name.endswith(suffix):return '' if kana.endswith(allowed) and (kana not in allowed or name==suffix) else 'agency reading is partial or name ending requires review'
    return 'full reading of annotated or unfamiliar official name requires review'


def parse_detail(page,expected):
    url=_url(page.url);expected_url=_url(expected['url']);code=expected['source_id']
    if urlsplit(url).path!='/data/'+code+'.html' or _identity(url)!=_identity(expected_url) or page.status!=200:
        raise ValueError('Hyogo profile URL differs from actual XML code')
    headers=[h for h in _NameDocument(decode_html(page)).root.find('header') if 'hero' in h.attrs.get('class','').split()]
    if len(headers)!=1:raise ValueError('Hyogo header.hero absent or ambiguous')
    header=headers[0];heads=header.find('h1');kanas=[n for n in header.find('div') if 'kana' in n.attrs.get('class','').split()]
    code_regions=[n for n in header.find('div') if 'code' in n.attrs.get('class','').split()]
    if len(heads)!=1 or len(kanas)!=1 or len(code_regions)!=1:raise ValueError('Hyogo header name/kana/code structure changed')
    strong=code_regions[0].find('strong')
    if len(strong)!=1:raise ValueError('Hyogo printed native code absent/ambiguous')
    code_raw=strong[0].text().strip();printed=re.fullmatch(r'([0-9]{7})(?:/[^\s]+)?',code_raw)
    addresses=[]
    for dl in header.find('dl'):
        for div in dl.find('div'):
            dt=div.find('dt');dd=div.find('dd')
            if len(dt)==1 and dt[0].text().strip()=='所在地' and len(dd)==1:addresses.append(dd[0].text().strip())
    if len(addresses)!=1:raise ValueError('Hyogo header 所在地 absent/ambiguous')
    name=_source_name(heads[0]).strip();display_name=heads[0].text().strip();raw=kanas[0].text().strip()
    address_raw=addresses[0];address=re.sub(r'^〒\d{3}-\d{4}\s*','',address_raw)
    review=[]
    # An image occupies one unresolved character. Compatible surrounding text
    # is not a Unicode confirmation; the standard glyph hold still applies.
    pattern=re.escape(name)
    for img in heads[0].find('img'):
        pattern=pattern.replace(re.escape(img.original_start_tag),'.')
    if not name or not re.fullmatch(pattern,expected['name']):review.append('Hyogo map and profile official names differ or are missing')
    if not address:review.append('Hyogo profile address is missing')
    elif expected['address'] and address!=expected['address']:review.append('Hyogo map and profile addresses differ')
    if printed is None or printed[1]!=code:review.append('Hyogo printed profile code differs from map code')
    if any(c in display_name for c in '()（）'):review.append('annotated official name requires review')
    row=dict(name=name,reading_raw=raw,reading_display_raw=raw,address=address,address_raw=address_raw,source_id=code,
        map_address_raw=expected['address'],address_role='agency profile shrine location',
        url=url,page_hash=page.sha256,fetched_at=page.fetched_at,locator='header.hero h1; div.kana; div.code strong; dl dt[所在地] + dd',
        evidence=f'神社名={name}; かな={raw}; 神社コード={code_raw}; 所在地={address_raw}',
        reading_review_reason=_reading_reason(display_name,raw),printed_code_raw=code_raw,xml_source=copy.deepcopy(expected['xml_source']))
    if heads[0].find('img'):row['name_rendering_status']='external_glyph'
    if review:row['review_reason']='; '.join(review)
    return row


def collect_hyogo(client,limit=None):
    if limit is not None and (type(limit) is not int or limit<=0):raise ValueError('Hyogo limit must be a positive integer or None')
    records=[];pages=[];failed=[];remaining=[];refs=[];details={};attempted=set()
    def fail(url,reason):failed.append(dict(url=url,reason=str(reason)));remaining.append(url)
    def acquire(url):
        p=_fetch(client,url);pages.append(dict(url=p.url,sha256=p.sha256,fetched_at=p.fetched_at));return p
    try:
        map_page=acquire(INDEX);refs=parse_xml(map_page)
        if not refs:fail(INDEX,'empty map response; no reliable native inventory total establishes completeness')
    except (ValueError,FetchError,UnicodeError,OSError) as exc:fail(INDEX,exc)
    for index,ref in enumerate(refs):
        code=ref['source_id'];url=ref['url']
        if code in attempted and code not in details:continue
        if code not in details:
            if limit is not None and len(attempted)>=limit:
                remaining.extend(r['url'] for r in refs[index:] if r['source_id'] not in details);break
            attempted.add(code)
            try:details[code]=acquire(url)
            except (ValueError,FetchError,UnicodeError,OSError) as exc:
                # A host/access/redirect failure stops all further requests.
                fail(url,exc);remaining.extend(r['url'] for r in refs[index+1:] if r['source_id'] not in details);break
        try:records.append(parse_detail(details[code],ref))
        except (ValueError,UnicodeError) as exc:fail(url,exc)
    data=build_dataset('hyogo','28','兵庫県','兵庫県神社庁',records,pages=pages,metadata=dict(limit=limit,authority_status='confirmed',
        observed_xml_url=INDEX,selected_bounds=dict(parse_qsl(urlsplit(INDEX).query)),ui_viewport_observed=False,api_cap_confirmed=False,
        prefectural_boundary_confirmed=False,inventory_total_confirmed=False,collection_complete=False,
        traversal_complete=bool(refs) and not failed and not remaining,failed_pages=failed,remaining_scope=list(dict.fromkeys(remaining)),
        xml_records_observed=len(refs),xml_unique_codes=len({r['source_id'] for r in refs}),detail_profiles_attempted=len(attempted),detail_profiles_fetched=len(details),
        protocol_reference=PROTOCOL_URL,redistribution_status='unconfirmed',source_conditions='記事・写真の無断転載を禁じます。',
        coverage='actual XML response for the explicitly selected rectangle only; not an observed UI viewport, prefectural boundary or proven site-wide inventory'))
    by_code={}
    for row in records:by_code.setdefault(row['source_id'],[]).append(row)
    facilities={f['id']:f for f in data['facilities']}
    for entry in data['entries']:
        f=facilities[entry['facility_id']];rows=by_code[f['native_source_id']];row=rows[0]
        entry['reading_display_raw']=row['reading_display_raw'];entry['printed_code_raw']=row['printed_code_raw']
        f['xml_occurrences']=[copy.deepcopy(r['xml_source']) for r in rows]
        f['map_address_raw']=row['map_address_raw'];f['address_role']=row['address_role']
        if f.get('name_rendering_status')=='external_glyph':entry.update(status='pending',reading='',reason=f['reason'])
        if row['reading_review_reason']:entry.update(status='pending',reading='',reason=row['reading_review_reason'])
        review=sorted({r['review_reason'] for r in rows if r.get('review_reason')})
        if any(len({r['xml_source'][key] for r in rows if r['xml_source'][key]})>1 for key in ('name_raw','address_raw')):
            review.append('conflicting explicit XML identity fields for the same native code')
        if review:
            reason='; '.join(review);f.update(status='pending',reason=reason,review_reason=reason);entry.update(status='pending',reading='',reason=reason)
    return data


REGISTRY={'hyogo':dict(code='28',prefecture='兵庫県',agency='兵庫県神社庁',collect=collect_hyogo)}
