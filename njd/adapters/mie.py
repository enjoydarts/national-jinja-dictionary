"""Independent, explicitly linked Mie agency committee HTML; no embedded data."""
import re
from urllib.parse import quote, unquote, urljoin, urlsplit, urlunsplit
from njd.adapters.south import Tree, Node, record
from njd.http import FetchError
from njd.normalize import normalize_reading
from njd.records import build_dataset

HOST='kyoka.mie-jinjacho.or.jp'
INDEX='http://'+HOST+'/shrine/'


def _url(value,base=INDEX):
    p=urlsplit(urljoin(base,value))
    if p.scheme not in ('http','https') or p.netloc!=HOST or p.query or p.fragment:raise ValueError('Mie URL outside independent official HTML scope')
    path=unquote(p.path)
    if not path.startswith('/shrine/') or any(x in ('.','..') for x in path.split('/')) or '\\' in path:raise ValueError('unexpected Mie shrine URL')
    return urlunsplit((p.scheme,HOST,quote(p.path,safe='/%'),'', ''))


def _identity(url):
    # Scheme changes are equivalent for loop detection, never invented for fetches.
    p=urlsplit(_url(url));return unquote(p.path)


def _fetch(client,url):
    url=_url(url)
    if not hasattr(client,'_raw'):
        page=client.fetch(url);_url(page.url);return page
    # Validate each real redirect before requesting its target; no cross-host fetch.
    for _ in range(6):
        refresh=getattr(client,'refresh_requested',False)
        client._policy(url,refresh=refresh);page=client._raw(url,refresh=refresh)
        if page.status in (301,302,303,307,308):
            if not page.headers.get('location'):raise FetchError('Mie redirect missing location')
            url=_url(page.headers['location'],page.url);continue
        if page.status!=200:raise FetchError('Mie HTTP '+str(page.status))
        return page
    raise FetchError('Mie redirect loop')


def index_links(page):
    _url(page.url);root=Tree(page.text).root;posts=root.find('div','post')
    if not posts:raise ValueError('Mie index article structure absent')
    links=[]
    for post in posts:
        heads=post.find('h2')
        if len(heads)!=1:raise ValueError('Mie index heading ambiguous')
        anchors=heads[0].find('a')
        if len(anchors)!=1 or not anchors[0].text:raise ValueError('Mie index detail link absent')
        url=_url(anchors[0].attrs.get('href',''),page.url)
        if not re.fullmatch(r'/shrine/[^/]+/',unquote(urlsplit(url).path)):raise ValueError('Mie index link is not a detail')
        item=(url,anchors[0].text)
        if item not in links:links.append(item)
    older=[]
    for a in root.find('a'):
        if '古い記事' not in a.text:continue
        url=_url(a.attrs.get('href',''),page.url)
        if not re.fullmatch(r'/shrine/(?:page/[1-9][0-9]*/)?',unquote(urlsplit(url).path)):raise ValueError('unexpected Mie older-page URL')
        older.append(url)
    if len(set(older))>1:raise ValueError('multiple Mie next pages')
    return links,older[0] if older else None


def _full_reading(name,raw):
    if not raw:return '', 'missing full source reading'
    try:reading=normalize_reading(raw)
    except ValueError:return '', 'nonliteral source reading requires review'
    endings=[('神社',('じんじゃ','じんしゃ','しんじゃ','しんしゃ','しゃ')),('神宮',('じんぐう',)),('大社',('たいしゃ','だいしゃ','おおやしろ')),('八幡宮',('はちまんぐう',)),('天満宮',('てんまんぐう',)),('宮',('ぐう','みや','きゅう')),('社',('しゃ','やしろ'))]
    for suffix,allowed in endings:
        if name.endswith(suffix):
            return (raw,'') if reading.endswith(allowed) else ('','source reading is partial or name ending requires review')
    return '', 'full reading of official label including annotations requires review'


def parse_detail(page):
    _url(page.url);regions=Tree(page.text).root.find('div','shrine_detail')
    if len(regions)!=1:raise ValueError('Mie detail region absent or ambiguous')
    region=regions[0];heads=region.find('h2');tables=region.find('table','table_03')
    if len(heads)!=1 or len(tables)!=1:raise ValueError('Mie detail heading/table structure changed')
    head=heads[0];kana=head.find('span','furigana')
    if len(kana)>1:raise ValueError('Mie detail reading ambiguous')
    source_raw=kana[0].raw_text if kana else ''
    raw=re.sub(r'^\s*[–—-]\s*|\s*[–—-]\s*$','',source_raw).strip()
    name=''.join(x.raw_text if isinstance(x,Node) else x for x in head.children if x not in kana).strip()
    if not name or any(ord(x)<32 for x in name):raise ValueError('Mie detail name absent or multiline')
    fields={}
    for tr in tables[0].find('tr'):
        cells=[n for n in tr.children if isinstance(n,Node) and n.tag in ('th','td')]
        if len(cells)!=2:continue
        key,value=re.sub(r'\s+','',cells[0].text),cells[1].text
        if key in fields:raise ValueError('duplicate Mie identity field: '+key)
        fields[key]=value
    code=fields.get('神社コード','');address=fields.get('鎮座地','')
    if not re.fullmatch(r'\d{7}',code) or not address:raise ValueError('Mie native code/address absent')
    reading,reason=_full_reading(name,raw)
    row=record(page,name,reading,address,'div.shrine_detail h2; span.furigana; table.table_03 th=神社コード/鎮座地',source_id=code,address_raw=address)
    row.update(source_reading_raw=raw,source_reading_display_raw=source_raw,reading_review_reason=reason,
        evidence=f'正式掲載名={name}; 掲載ふりがな原文={raw}; 神社コード={code}; 鎮座地={address}')
    return row


def _bind_index(row,page,url,listed_name):
    row=dict(row)
    raw_hrefs=[a.attrs.get('href','') for post in Tree(page.text).root.find('div','post') for head in post.find('h2') for a in head.find('a')
               if a.text==listed_name and _url(a.attrs.get('href',''),page.url)==url]
    row['index_source']=dict(url=page.url,page_hash=page.sha256,fetched_at=page.fetched_at,name_raw=listed_name,
        href=raw_hrefs[0] if raw_hrefs else url,resolved_href=url,detail_name_raw=row['name'],detail_url=row['url'],locator='div.post h2 a')
    if row['name']!=listed_name:row['review_reason']='Mie index and detail official names differ'
    return row


def collect_mie(client,limit=None):
    if limit is not None and (not isinstance(limit,int) or limit<=0):raise ValueError('Mie limit must be a positive facility count or None')
    next_url=INDEX;seen_indexes=set();seen_details={};records=[];pages=[];indexes=[];failed=[];remaining=[];codes=set();halt=False
    while next_url:
        if _identity(next_url) in seen_indexes:
            failed.append(dict(url=next_url,reason='pagination loop'));remaining.append(next_url);break
        seen_indexes.add(_identity(next_url));indexes.append(next_url)
        try:
            page=_fetch(client,next_url);links,older=index_links(page)
            pages.append(dict(url=page.url,sha256=page.sha256,fetched_at=page.fetched_at))
        except (ValueError,FetchError,UnicodeError,OSError) as exc:
            failed.append(dict(url=next_url,reason=str(exc)));remaining.append(next_url);break
        for index,(url,listed_name) in enumerate(links):
            if _identity(url) in seen_details:
                records.append(_bind_index(seen_details[_identity(url)],page,url,listed_name));continue
            if limit is not None and len(codes)>=limit:
                remaining.extend(x[0] for x in links[index:]);halt=True;break
            try:
                detail=_fetch(client,url);row=parse_detail(detail)
                pages.append(dict(url=detail.url,sha256=detail.sha256,fetched_at=detail.fetched_at))
                seen_details[_identity(url)]=row
                row=_bind_index(row,page,url,listed_name)
                records.append(row);codes.add(row['source_id'])
            except (ValueError,FetchError,UnicodeError,OSError) as exc:
                failed.append(dict(url=url,reason=str(exc)));remaining.append(url)
        if halt or (limit is not None and len(codes)>=limit and older):
            if older:remaining.append(older)
            break
        next_url=older
    # Generic build_dataset binds native codes and detects differing acquired rows.
    build_rows=[dict(row,reading_raw=row['source_reading_raw']) for row in records]
    data=build_dataset('mie','24','三重県','三重県神社庁',build_rows,pages=pages,metadata=dict(
        limit=limit,authority_status='confirmed',listing_authority='agency education committee explicitly linked by prefectural agency',
        observed_index_urls=indexes,failed_pages=failed,remaining_scope=list(dict.fromkeys(remaining)),
        traversal_complete=not remaining and not failed,coverage='actual independent committee HTML articles followed through observed older-page anchors only; sidebar category totals not facility count',
        source_rows_observed=len(records),pages_fetched=len(pages),redistribution_status='unconfirmed'))
    by_code={}
    for row in records:by_code.setdefault(row['source_id'],[]).append(row)
    facilities={f['id']:f for f in data['facilities']}
    for entry in data['entries']:
        f=facilities[entry['facility_id']];rows=by_code[f['native_source_id']]
        entry['source_reading_raw']=rows[0]['source_reading_raw'];entry['source_reading_display_raw']=rows[0]['source_reading_display_raw']
        if rows[0]['reading_review_reason']:
            entry.update(status='pending',reading='',reason=rows[0]['reading_review_reason'])
        if len({(r['name'],r['source_reading_raw'],r['address']) for r in rows})>1:
            f['status']=entry['status']='pending';f['reason']=entry['reason']='conflicting rows for Mie native shrine code'
            f['source_reading_conflicts']=[dict(name_raw=r['name'],reading_raw=r['source_reading_raw'],address_raw=r['address'],url=r['url'],page_hash=r['page_hash'],fetched_at=r['fetched_at']) for r in rows]
        f['index_occurrences']=[]
        for row in rows:
            if row['index_source'] not in f['index_occurrences']:f['index_occurrences'].append(row['index_source'])
        review_reasons=sorted({r['review_reason'] for r in rows if r.get('review_reason')})
        if review_reasons:
            reason='; '.join(review_reasons)
            f.update(status='pending',reason=reason,review_reason=reason)
            entry.update(status='pending',reading='',reason=reason)
    return data


REGISTRY={'mie':dict(code='24',prefecture='三重県',agency='三重県神社庁',collect=collect_mie)}
