"""Nagasaki's observed regional tables, with the old outbound-link witnesses.

No kana column exists. Printed table numbers are local row numbers, not native
facility IDs. Only unique, identical outbound URLs link old and new observations.
"""
from collections import Counter
import re
from urllib.parse import unquote, urljoin, urlsplit, urlunsplit

from njd.adapters.central import Document, cells
from njd.adapters.south import parse_nagasaki, record
from njd.http import FetchError
from njd.records import build_dataset

ROOT='https://nagasaki-jinjacho.or.jp/'
HEADER=['番号','神社名','祭神名','旧社格','例祭日','郵便番号','鎮座地']


def _url(raw, base=ROOT):
    p=urlsplit(raw)
    if any(x in ('.','..') for x in unquote(p.path).split('/')) or '\\' in unquote(raw):
        raise ValueError('Nagasaki path traversal')
    u=urlsplit(urljoin(base,raw))
    if u.scheme!='https' or u.netloc!='nagasaki-jinjacho.or.jp' or u.query:
        raise ValueError('Nagasaki URL outside official origin or unexpected query')
    if u.path!='/' and not re.fullmatch(r'/[a-z]+\.html',u.path):
        raise ValueError('unexpected Nagasaki page path')
    return urlunsplit((u.scheme,u.netloc,u.path,'',''))


def _fetch(client,url):
    url=_url(url)
    # Check redirects before following; never leave the requested listing.
    if hasattr(client,'_raw'):
        refresh=getattr(client,'refresh_requested',False)
        client._policy(url,refresh=refresh);p=client._raw(url,refresh=refresh)
    else:p=client.fetch(url)
    if _url(p.url)!=url:raise ValueError('Nagasaki response identity changed')
    if p.status!=200:raise FetchError('Nagasaki HTTP '+str(p.status)+'; redirect/status requires review')
    if any(k.lower()=='cf-mitigated' and v.strip().lower()=='challenge' for k,v in p.headers.items()):
        raise FetchError('Nagasaki access challenge')
    if re.search(r'type\s*=\s*[\"\']?password\b|captcha|access denied',p.text,re.I):
        raise FetchError('Nagasaki access restriction')
    return p


def _witness(page):return dict(url=page.url,sha256=page.sha256,fetched_at=page.fetched_at)


def _website_key(url):
    # Empty HTTP root path and '/' are the same request target. Nothing else
    # (scheme, www, index.html, social account, query) is made equivalent.
    p=urlsplit(url or '')
    if p.scheme not in ('http','https') or not p.netloc:return None
    return urlunsplit((p.scheme,p.netloc,p.path or '/',p.query,p.fragment))


def parse_region(page):
    out=[];root=Document(page.text).root
    for ti,t in enumerate(root.find('table'),1):
        trs=t.find('tr')
        if not trs:continue
        first=[c.text().strip() for c in cells(trs[0])]
        if first!=HEADER:
            if '神社名' in first or '番号' in first:raise ValueError('Nagasaki table header changed')
            continue
        table_start=len(out)
        for ri,tr in enumerate(trs[1:],2):
            cs=cells(tr);values=[c.text().strip() for c in cs]
            locator=f'table[{ti}] tr[{ri}]'
            if len(values)!=7:raise ValueError('Nagasaki table column count changed')
            if not any(values):continue
            if not values[0] and values[1] and not any(values[2:]):
                if len(out)==table_start or not values[1].startswith(('(','（')):
                    raise ValueError('unrecognized Nagasaki name annotation')
                out[-1].update(name_annotation_raw=values[1],name_annotation_locator=locator,
                    name_rendering_status='external_glyph')
                continue
            if not values[0].isdigit() or not values[1] or not values[6]:
                raise ValueError('Nagasaki numbered name/address missing')
            links=[urljoin(page.url,a.attrs['href']) for a in cs[1].find('a') if a.attrs.get('href')]
            if len(links)>1:raise ValueError('multiple Nagasaki shrine website links')
            out.append(record(page,values[1],'',values[6],locator,
                printed_number_raw=values[0],postal_code_raw=values[5],
                official_url=links[0] if links else None))
    if not out:raise ValueError('Nagasaki regional tables absent')
    return out


def collect_nagasaki(client,limit=None):
    if limit is not None and (isinstance(limit,bool) or limit<1):raise ValueError('positive facility limit required')
    home=_fetch(client,ROOT)
    if not any(_url(a.attrs['href'],home.url)==ROOT+'search.html'
               for a in Document(home.text).root.find('a')
               if a.attrs.get('href') in ('search.html','/search.html',ROOT+'search.html')):
        raise ValueError('Nagasaki home search link absent')
    index=_fetch(client,ROOT+'search.html')
    main=[n for n in Document(index.text).root.find('div') if n.attrs.get('id')=='a-main']
    if len(main)!=1:raise ValueError('Nagasaki search main block absent/ambiguous')
    links=[];urls=[]
    for a in main[0].find('a'):
        raw=a.attrs.get('href','')
        if not raw or raw.startswith('#'):continue
        u=_url(raw,index.url)
        if u in (ROOT,ROOT+'search.html',ROOT+'link.html'):continue
        links.append(dict(href_raw=raw,label_raw=a.text().strip(),url=u))
        if u not in urls:urls.append(u)
    if not urls:raise ValueError('Nagasaki region links absent')
    legacy_page=_fetch(client,ROOT+'link.html');legacy=parse_nagasaki(legacy_page)
    pages=[_witness(p) for p in (home,index,legacy_page)];regional=[]
    # A failure aborts this incoming snapshot. Cached pages permit resumption;
    # no partial page set is used to establish unique legacy URL matches.
    for u in urls:
        p=_fetch(client,u);regional.extend(parse_region(p));pages.append(_witness(p))
    old_counts=Counter(_website_key(r.get('official_url')) for r in legacy)
    new_counts=Counter(_website_key(r.get('official_url')) for r in regional)
    old={_website_key(r.get('official_url')):r for r in legacy}
    consumed=set();identities=Counter((r['name'],r['address']) for r in regional)
    for r in regional:
        k=_website_key(r.get('official_url'))
        if k and old_counts[k]==new_counts[k]==1 and identities[(r['name'],r['address'])]==1:
            original=old[k];r['source_id']=original['source_id'];consumed.add(original['source_id'])
            r['legacy_link_observation']=dict(name_raw=original['name'],reading_raw='',address_raw='',
                url=original['url'],locator=original['locator'],page_hash=original['page_hash'],
                fetched_at=original['fetched_at'],native_source_id=original['source_id'],
                match_rule='unique identical outbound HTTP request URL (empty root path equals slash)')
        if identities[(r['name'],r['address'])]>1:
            r['source_id']='listing-observation|'+r['url']+'|'+r['locator']
            r['review_reason']='duplicate literal name/address observations; facility identity unresolved'
            r['identity_review_required']=True
    rows=regional+[r for r in legacy if r['source_id'] not in consumed]
    selected=rows if limit is None else rows[:limit]
    d=build_dataset('nagasaki','42','長崎県','長崎県神社庁',selected,pages=pages,metadata=dict(
        limit=limit,source_rows_observed=len(regional)+len(legacy),regional_rows_observed=len(regional),
        legacy_link_rows_observed=len(legacy),matched_legacy_links=len(consumed),regional_pages=len(urls),
        pages_fetched=len(pages),traversal_complete=True,collection_complete=len(selected)==len(rows),
        remaining_scope=[] if len(selected)==len(rows) else [dict(unselected_facility_records=len(rows)-len(selected))],
        discovery_links=links,coverage='observed regional table and outbound-link graph only; not a prefectural shrine census',
        native_id_note='URL for legacy links; otherwise literal name/address; unresolved duplicates use listing-observation locators, not official facility IDs'))
    if len(d['facilities'])!=len(selected):
        raise ValueError('unexpected Nagasaki row identity collision; explicit source review required')
    for f,e,r in zip(d['facilities'],d['entries'],selected):
        for field in ('legacy_link_observation','printed_number_raw','postal_code_raw','name_annotation_raw','name_annotation_locator'):
            if field in r:f[field]=r[field]
        if r.get('identity_review_required'):e['identity_review_required']=True
    return d
