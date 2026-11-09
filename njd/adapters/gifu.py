"""Explicit Gifu name groups → search rows → literal agency detail fields.

Index readings describe groups, never individual facilities. Article snippets,
photographs, deities and aliases are deliberately outside the parsed fields.
"""
import re
from urllib.parse import parse_qsl, unquote, urljoin, urlsplit
from njd.adapters.central import Document, Node, cells, clean, decode_html
from njd.http import FetchError
from njd.normalize import normalize_reading
from njd.records import build_dataset

INDEX='https://www.gifu-jinjacho.jp/jnjyalist.php'
HOST='www.gifu-jinjacho.jp'
PATHS={'/jnjyalist.php':{'page','tcnt','keysel'},'/search.php':{'page','tcnt','jinjya'},'/syosai.php':{'shrno','shrname'}}


class _NameDocument(Document):
    """Retain original image tags only where a name needs an external glyph."""
    def handle_starttag(self,tag,attrs):
        original=self.get_starttag_text()
        super().handle_starttag(tag,attrs)
        if tag=='img':self.stack[-1].children[-1].original_start_tag=original


def _source_name(node):
    if node.tag=='img':return node.original_start_tag
    return ''.join(_source_name(c) if isinstance(c,Node) else c for c in node.children)


def _url(value,base=INDEX):
    raw=urlsplit(value)
    if any(x in ('.','..') for x in unquote(raw.path).split('/')) or '\\' in unquote(value):
        raise ValueError('Gifu URL contains path traversal')
    url=urljoin(base,value);p=urlsplit(url)
    if p.scheme!='https' or p.netloc!=HOST or p.fragment or p.path not in PATHS:
        raise ValueError('Gifu URL outside official endpoint scope')
    pairs=parse_qsl(p.query,keep_blank_values=True);q=dict(pairs)
    if len(q)!=len(pairs) or set(q)-PATHS[p.path]:raise ValueError('unexpected Gifu query fields')
    for k in ('page','tcnt','shrno'):
        if k in q and not re.fullmatch(r'[0-9]+',q[k]):raise ValueError('invalid Gifu numeric query')
    if 'page' in q and int(q['page'])<1:raise ValueError('invalid Gifu page')
    if p.path=='/syosai.php' and ('shrno' not in q or int(q['shrno'])<1):raise ValueError('missing Gifu shrine identity')
    if p.path=='/search.php' and not q.get('jinjya'):raise ValueError('missing Gifu search name')
    if any(ord(c)<32 or ord(c)==127 for v in q.values() for c in v):raise ValueError('control character in Gifu query')
    return url


def _identity(url):
    p=urlsplit(_url(url));return p.path,tuple(sorted(parse_qsl(p.query,keep_blank_values=True)))


def _fetch(client,url):
    url=_url(url);original=_identity(url);seen=set()
    for _ in range(6):
        if _identity(url) in seen:raise FetchError('Gifu redirect loop')
        seen.add(_identity(url))
        if hasattr(client,'_raw'):
            refresh=getattr(client,'refresh_requested',False)
            client._policy(url,refresh=refresh);page=client._raw(url,refresh=refresh)
        else:page=client.fetch(url)
        if _identity(page.url)!=original:raise ValueError('Gifu response identity differs from requested endpoint/query')
        if page.status in (301,302,303,307,308):
            if not page.headers.get('location'):raise FetchError('Gifu redirect missing location')
            target=_url(page.headers['location'],page.url)
            if _identity(target)!=original:raise ValueError('Gifu redirect changes endpoint/name/shrine identity')
            url=target;continue
        if page.status!=200:raise FetchError('Gifu HTTP '+str(page.status))
        # https://developers.cloudflare.com/cloudflare-challenges/challenge-types/challenge-pages/detect-response/
        if any(k.lower()=='cf-mitigated' and v.lower().strip()=='challenge' for k,v in page.headers.items()):
            raise FetchError('Gifu access/authentication challenge')
        if re.search(rb'<input\b[^>]*\btype\s*=\s*["\']?password\b|captcha|access denied|cloudflare[^\n]{0,120}challenge',page.body,re.I):
            raise FetchError('Gifu access/authentication challenge')
        return page
    raise FetchError('too many Gifu redirects')


def _root(page,path):
    if urlsplit(_url(page.url)).path!=path or page.status!=200:raise ValueError('unexpected Gifu page endpoint/status')
    return _NameDocument(decode_html(page)).root


def _next(root,page):
    found=[];p=urlsplit(page.url);q=dict(parse_qsl(p.query,keep_blank_values=True))
    for a in root.find('a'):
        if not clean(a.text()).startswith('次の'):continue
        href=a.attrs.get('href','')
        if not href:raise ValueError('Gifu next link missing href')
        url=_url(href,page.url);n=urlsplit(url);nq=dict(parse_qsl(n.query,keep_blank_values=True))
        if n.path!=p.path or any(nq.get(k,'')!=q.get(k,'') for k in ('jinjya','keysel')):
            raise ValueError('Gifu next link changes search scope')
        if url not in found:found.append(url)
    if len(found)>1:raise ValueError('ambiguous Gifu next page')
    return found[0] if found else None


def _total(root,pattern):
    values=re.findall(pattern,clean(root.text()))
    if len(set(values))!=1:raise ValueError('Gifu explicit result total absent or ambiguous')
    return int(values[0])


def parse_index(page):
    root=_root(page,'/jnjyalist.php');total=_total(root,r'(\d+)\s*件の神社名が登録されています')
    tables=[x for x in root.find('table') if 'jnm_list' in x.attrs.get('class','').split()]
    if len(tables)!=1:raise ValueError('Gifu name-group table absent or ambiguous')
    rows=[]
    for i,tr in enumerate(tables[0].find('tr'),1):
        cs=cells(tr)
        if not cs or all(c.tag=='th' for c in cs):continue
        if len(cs)!=3:raise ValueError('Gifu name-group row structure changed')
        anchors=cs[0].find('a')
        if len(anchors)!=1 or not clean(anchors[0].text()) or not clean(cs[2].text()).isdigit():raise ValueError('Gifu name-group fields absent')
        a=anchors[0];url=_url(a.attrs.get('href',''),page.url);name=clean(a.text())
        if urlsplit(url).path!='/search.php' or dict(parse_qsl(urlsplit(url).query)).get('jinjya')!=name:
            raise ValueError('Gifu name-group href and name differ')
        rows.append(dict(name_raw=name,group_reading_raw=clean(cs[1].text()),group_count=int(clean(cs[2].text())),url=url,
            href_raw=a.attrs['href'],locator=f'table.jnm_list tr[{i}]'))
    if not rows and total:raise ValueError('Gifu nonempty index has no name groups')
    return dict(rows=rows,total=total,next_url=_next(root,page))


def _address(raw):return re.sub(r'^〒?\s*\d{3}-\d{4}\s*','',raw).strip()


def parse_search(page):
    root=_root(page,'/search.php');total=_total(root,r'(\d+)\s*件の神社がみつかりました')
    tables=[t for t in root.find('table') if 'sc_tbl' in t.attrs.get('class','').split()]
    if len(tables)!=1:raise ValueError('Gifu search result table absent or ambiguous')
    rows=[];current=None
    # Actual HTML omits closing TR tags. Iterate factual TDs rather than rows.
    for i,td in enumerate(tables[0].find('td'),1):
        style=re.sub(r'\s+','',td.attrs.get('style','')).lower()
        if td.attrs.get('width')=='555' and 'color:purple' in style:
            if current is not None:raise ValueError('Gifu search result address missing')
            anchors=td.find('a')
            if len(anchors)!=1:raise ValueError('Gifu search result name ambiguous')
            a=anchors[0];url=_url(a.attrs.get('href',''),page.url)
            if urlsplit(url).path!='/syosai.php':raise ValueError('Gifu result link not a detail')
            current=dict(name=clean(a.text()),url=url,href_raw=a.attrs['href'],source_id=dict(parse_qsl(urlsplit(url).query))['shrno'],locator=f'table.sc_tbl td[{i}] a')
        elif td.attrs.get('width')=='200' and current is not None and td.find('a'):
            anchors=td.find('a')
            if len(anchors)!=1:raise ValueError('Gifu detail button ambiguous')
            a=anchors[0];url=_url(a.attrs.get('href',''),page.url)
            if urlsplit(url).path!='/syosai.php' or dict(parse_qsl(urlsplit(url).query))['shrno']!=current['source_id']:
                raise ValueError('Gifu name and detail button shrine identities differ')
            current.update(url=url,href_raw=a.attrs['href'])
        elif td.attrs.get('width')=='555' and 'color:#993300' in style:
            if current is None:raise ValueError('Gifu search address without name')
            current.update(address=_address(clean(td.text())),address_raw=clean(td.text()))
            if not current['name'] or not current['address'].startswith('岐阜県'):raise ValueError('Gifu search name/address missing')
            rows.append(current);current=None
    if current is not None or (not rows and total):raise ValueError('Gifu search result fields absent')
    if len(rows)>total:raise ValueError('Gifu result row count exceeds total')
    return dict(rows=rows,total=total,next_url=_next(root,page))


def _reading_reason(name,raw):
    try:kana=normalize_reading(raw)
    except ValueError:return 'missing or nonliteral full detail reading'
    endings=[('神社',('じんじゃ','じんしゃ','しんじゃ','しんしゃ','しゃ')),('神宮',('じんぐう',)),('大社',('たいしゃ','だいしゃ','おおやしろ')),('宮',('ぐう','みや','きゅう')),('社',('しゃ','やしろ'))]
    for suffix,allowed in endings:
        if name.endswith(suffix):return '' if kana.endswith(allowed) and (kana not in allowed or name==suffix) else 'detail reading may be partial; full name reading requires review'
    return 'full reading of annotated or unfamiliar source name requires review'


def parse_detail(page,expected_name=None,expected_address=None):
    root=_root(page,'/syosai.php');heads=[n for n in root.find('font') if 'hyodai' in n.attrs.get('class','').split()]
    regions=[td for td in root.find('td') if td.attrs.get('height')=='80' and heads and heads[0] in td.find('font')]
    addresses=[n for n in root.find('td') if 'moji3' in n.attrs.get('class','').split()]
    if len(heads)!=1 or len(regions)!=1 or len(addresses)!=1:raise ValueError('Gifu detail name/reading/address structure changed')
    head=heads[0];display_name=head.text().strip();name=_source_name(head).strip();fonts=[f for f in regions[0].find('font') if f is not head]
    display=fonts[0].text().strip() if len(fonts)==1 else ''
    match=re.fullmatch(r'[（(]([^()（）]+)[）)]',display)
    raw=match[1] if match else ''
    address_raw=addresses[0].text().strip();address=_address(clean(address_raw))
    if not address.startswith('岐阜県') or not name:raise ValueError('Gifu detail name/address absent or outside prefecture')
    review=[]
    query_name=dict(parse_qsl(urlsplit(page.url).query)).get('shrname')
    if query_name is not None and query_name not in (display_name,'★'+display_name+'★','■'+display_name+'■'):
        review.append('Gifu detail query label and official name differ')
    if expected_name is not None and display_name!=expected_name:review.append('Gifu search and detail names differ')
    if expected_address is not None and address!=expected_address:review.append('Gifu search and detail addresses differ')
    if any(c in name for c in '()（）'):review.append('annotated official name requires review')
    row=dict(name=name,reading_raw=raw,address=address,address_raw=address_raw,url=page.url,page_hash=page.sha256,fetched_at=page.fetched_at,
        source_id=dict(parse_qsl(urlsplit(page.url).query))['shrno'],locator='td[height=80] font.hyodai + font; td.moji3',
        evidence=f'掲載名={name}; 掲載読み={display}; 住所={address_raw}',reading_display_raw=display,reading_review_reason=_reading_reason(display_name,raw))
    if head.find('img'):
        row['name_rendering_status']='external_glyph';review.append('source name uses external glyph')
        row['name_glyphs']=[dict(x.attrs) for x in head.find('img')]
    if review:row['review_reason']='; '.join(review)
    return row


def collect_gifu(client,limit=None):
    if limit is not None and (type(limit) is not int or limit<=0):raise ValueError('Gifu limit must be positive integer or None')
    records=[];pages=[];failed=[];remaining=[];groups=[];indexes=[];searches=[];totals=[];details={};codes=set();seen_index=set();seen_search=set();halt=False
    def acquire(url):
        # _fetch ValueErrors are scope/redirect refusals, not HTML parse errors.
        try:page=_fetch(client,url)
        except ValueError as exc:raise FetchError(str(exc)) from exc
        pages.append(dict(url=page.url,sha256=page.sha256,fetched_at=page.fetched_at));return page
    def fail(url,exc):failed.append(dict(url=url,reason=str(exc)));remaining.append(url)
    index_url=INDEX;index_total=None;query_totals={}
    while index_url and not halt:
        if _identity(index_url) in seen_index:fail(index_url,'index pagination loop');break
        seen_index.add(_identity(index_url));indexes.append(index_url)
        try:
            ip=acquire(index_url);parsed=parse_index(ip)
            if index_total is not None and parsed['total']!=index_total:raise ValueError('Gifu index total changed during traversal')
            index_total=parsed['total'];groups.extend(dict(r,index_url=ip.url,page_hash=ip.sha256,fetched_at=ip.fetched_at) for r in parsed['rows'])
        except (ValueError,FetchError,UnicodeError,OSError) as exc:fail(index_url,exc);break
        for group in parsed['rows']:
            search_url=group['url']
            if _identity(search_url) in seen_search:continue
            if limit is not None and len(codes)>=limit:
                remaining.extend(r['url'] for r in parsed['rows'] if _identity(r['url']) not in seen_search)
                halt=True;break
            chain=set();search_total=None;search_rows=0
            while search_url:
                if _identity(search_url) in chain:fail(search_url,'search pagination loop');break
                if _identity(search_url) in seen_search:break
                chain.add(_identity(search_url));seen_search.add(_identity(search_url));searches.append(search_url)
                try:
                    sp=acquire(search_url);result=parse_search(sp)
                    if search_total is not None and result['total']!=search_total:raise ValueError('Gifu search total changed during traversal')
                    search_total=result['total'];query_totals[_identity(group['url'])]=search_total;search_rows+=len(result['rows'])
                    totals.append(dict(url=sp.url,total=search_total,rows_observed=len(result['rows'])))
                except (FetchError,OSError) as exc:
                    fail(search_url,exc);halt=True;break
                except (ValueError,UnicodeError) as exc:fail(search_url,exc);break
                for pos,ref in enumerate(result['rows']):
                    code=ref['source_id'];url=ref['url']
                    if code not in details and limit is not None and len(codes)>=limit:
                        remaining.extend(r['url'] for r in result['rows'][pos:]);halt=True;break
                    try:
                        if code not in details:details[code]=parse_detail(acquire(url));codes.add(code)
                        row=dict(details[code]);reasons=[row['review_reason']] if row.get('review_reason') else []
                        if row['name']!=group['name_raw']:reasons.append('Gifu name group and detail names differ')
                        if row['name']!=ref['name']:reasons.append('Gifu search and detail names differ')
                        if row['address']!=ref['address']:reasons.append('Gifu search and detail addresses differ')
                        if reasons:row['review_reason']='; '.join(reasons)
                        row['index_source']=dict(url=sp.url,name_raw=ref['name'],address_raw=ref['address_raw'],href_raw=ref['href_raw'],locator=ref['locator'],page_hash=sp.sha256,fetched_at=sp.fetched_at)
                        records.append(row)
                    except (FetchError,OSError) as exc:
                        fail(url,exc);remaining.extend(r['url'] for r in result['rows'][pos+1:]);halt=True;break
                    except (ValueError,UnicodeError) as exc:fail(url,exc)
                if halt:
                    if result['next_url']:remaining.append(result['next_url'])
                    break
                if not result['next_url'] and search_rows!=search_total:fail(search_url,'Gifu search total differs from observed rows')
                search_url=result['next_url']
            if halt:
                remaining.extend(r['url'] for r in parsed['rows'] if _identity(r['url']) not in seen_search)
                break
        if halt:
            if parsed['next_url']:remaining.append(parsed['next_url'])
            break
        index_url=parsed['next_url']
    if not halt and not failed and index_total!=len(groups):fail(INDEX,'Gifu index total differs from observed name-reading groups')
    # The search combines all readings of the same name. A single group is
    # only a lower bound until every index group has actually been acquired.
    complete_index=not halt and index_url is None and index_total==len(groups)
    grouped={}
    for group in groups:grouped.setdefault(_identity(group['url']),[]).append(group)
    for key,items in grouped.items():
        if key not in query_totals:continue
        total=query_totals[key];url=items[0]['url'];counts=[r['group_count'] for r in items]
        if total<max(counts) or (complete_index and total!=sum(counts)):
            fail(url,'Gifu search total contradicts observed name-reading group counts')
    data=build_dataset('gifu','21','岐阜県','岐阜県神社庁',records,pages=pages,metadata=dict(limit=limit,authority_status='confirmed',
        observed_index_urls=indexes,observed_search_urls=searches,index_group_total=index_total,index_groups_observed=len(groups),index_groups=groups,
        search_result_totals=totals,failed_pages=failed,remaining_scope=list(dict.fromkeys(remaining)),traversal_complete=not remaining and not failed,
        coverage='actual index name-reading groups and search/detail hrefs only; index total is not facility count',redistribution_status='unconfirmed'))
    by_code={}
    for r in records:by_code.setdefault(r['source_id'],[]).append(r)
    fs={f['id']:f for f in data['facilities']}
    for e in data['entries']:
        f=fs[e['facility_id']];rows=by_code[f['native_source_id']];r=rows[0]
        e['reading_display_raw']=r['reading_display_raw']
        if r['reading_review_reason']:e.update(status='pending',reading='',reason=r['reading_review_reason'])
        f['index_occurrences']=[r['index_source'] for r in rows]
        if r.get('name_glyphs'):f['name_glyphs']=r['name_glyphs']
        reasons=sorted({r['review_reason'] for r in rows if r.get('review_reason')})
        if reasons:
            reason='; '.join(reasons);f.update(status='pending',reason=reason,review_reason=reason);e.update(status='pending',reading='',reason=reason)
    return data


REGISTRY={'gifu':dict(code='21',prefecture='岐阜県',agency='岐阜県神社庁',collect=collect_gifu)}
