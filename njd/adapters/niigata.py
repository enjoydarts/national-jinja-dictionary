"""Niigata agency public HTML search; only observed regional/pagination links."""
import re
from urllib.parse import parse_qsl, quote, urljoin, urlsplit, urlunsplit
from njd.adapters.south import Node, Tree, record
from njd.http import FetchError
from njd.normalize import normalize_reading
from njd.records import build_dataset

ORIGIN='https://niigata-jinjacho.jp'
INDEX=ORIGIN+'/shrine_niigata/'


class _NameTree(Tree):
    """Keep only image start tags needed to represent unknown source glyphs."""
    def handle_starttag(self,tag,attrs):
        original=self.get_starttag_text()
        super().handle_starttag(tag,attrs)
        if tag=='img':self.stack[-1].children[-1].original_start_tag=original


def _source_name(node):
    if node.tag=='img':return node.original_start_tag
    return ''.join(_source_name(c) if isinstance(c,Node) else c for c in node.children)


def _url(value,base=INDEX):
    p=urlsplit(urljoin(base,value))
    if p.scheme!='https' or p.netloc!='niigata-jinjacho.jp' or p.fragment:raise ValueError('Niigata URL outside official search scope')
    if p.path not in ('/shrine_niigata/','/shrine_niigata/index.php','/shrine_niigata/search.php'):raise ValueError('unexpected Niigata search path')
    query=parse_qsl(p.query,keep_blank_values=True)
    if p.path.endswith('search.php'):
        fields=dict(query)
        if len(fields)!=len(query) or set(fields)-{'area','keyword','page','num'}:raise ValueError('unknown Niigata search parameters')
        if not re.fullmatch(r'15\d{3}',fields.get('area','')) or fields.get('keyword',''):raise ValueError('unexpected Niigata search area/keyword')
        if any(not re.fullmatch(r'[1-9]\d*',fields[k]) for k in ('page','num') if k in fields):raise ValueError('invalid Niigata pagination')
    elif p.query:raise ValueError('unexpected Niigata index query')
    return urlunsplit((p.scheme,p.netloc,quote(p.path,safe='/%'),p.query,''))


def _identity(url):
    p=urlsplit(_url(url));q=dict(parse_qsl(p.query,keep_blank_values=True))
    if p.path in ('/shrine_niigata/','/shrine_niigata/index.php'):return ('index',)
    return (p.path,q.get('area'),q.get('keyword',''),q.get('page','1'),q.get('num','10'))


def _fetch(client,url):
    url=_url(url);requested=_identity(url)
    if not hasattr(client,'_raw'):
        page=client.fetch(url)
        if _identity(page.url)!=requested:raise FetchError('Niigata final response changes requested search scope')
        return page
    for _ in range(6):
        if _identity(url)!=requested:raise FetchError('Niigata redirect changes requested search scope')
        refresh=getattr(client,'refresh_requested',False)
        client._policy(url,refresh=refresh);page=client._raw(url,refresh=refresh)
        if _identity(page.url)!=requested:raise FetchError('Niigata final response changes requested search scope')
        if page.status in (301,302,303,307,308):
            if not page.headers.get('location'):raise FetchError('Niigata redirect missing location')
            url=_url(page.headers['location'],page.url);continue
        if page.status!=200:raise FetchError('Niigata HTTP '+str(page.status))
        return page
    raise FetchError('Niigata redirect loop')


def parse_index(page):
    _url(page.url);root=Tree(page.text).root
    forms=[f for f in root.find('form') if any(s.attrs.get('name')=='area' for s in f.find('select'))]
    if len(forms)!=1:raise ValueError('Niigata area search form absent or ambiguous')
    form=forms[0]
    if form.attrs.get('method','').lower()!='get' or urljoin(page.url,form.attrs.get('action',''))!=INDEX+'search.php':raise ValueError('Niigata search form action changed')
    selects=[s for s in form.find('select') if s.attrs.get('name')=='area']
    if len(selects)!=1 or not any(x.attrs.get('name')=='keyword' for x in form.find('input')):raise ValueError('Niigata search fields changed')
    options=[]
    for o in selects[0].find('option'):
        value=o.attrs.get('value','')
        if not value:continue
        if not re.fullmatch(r'15\d{3}',value) or not o.text:raise ValueError('invalid Niigata municipality option')
        options.append(dict(value=value,label=o.text))
    if not options or len({o['value'] for o in options})!=len(options):raise ValueError('missing or duplicate Niigata areas')
    links={}
    for a in root.find('a'):
        href=urljoin(page.url,a.attrs.get('href',''));p=urlsplit(href)
        if p.path!='/shrine_niigata/search.php':continue
        href=_url(href);fields=dict(parse_qsl(p.query,keep_blank_values=True))
        if set(fields)!={'area'}:raise ValueError('unexpected Niigata initial area link')
        if fields['area'] in links and links[fields['area']]!=href:raise ValueError('ambiguous Niigata area URL')
        links[fields['area']]=href
    if set(links)!={o['value'] for o in options}:raise ValueError('Niigata area menu and actual links disagree')
    return [links[o['value']] for o in options],options


def _reading_reason(name,raw):
    try:reading=normalize_reading(raw)
    except ValueError:return 'missing or nonliteral agency full reading'
    if any(c in name for c in '（）()／/・'):return 'annotated or multiple official names require full reading review'
    endings=[('合殿',('あいどの',)),('神社',('じんじゃ','じんしゃ','しんじゃ','しんしゃ','しゃ')),('神宮',('じんぐう',)),('大社',('たいしゃ','だいしゃ','おおやしろ')),('八幡宮',('はちまんぐう',)),('天満宮',('てんまんぐう',)),('宮',('みや','ぐう','きゅう')),('大明神',('だいみょうじん',)),('社',('しゃ','やしろ'))]
    for suffix,allowed in endings:
        if name.endswith(suffix):return '' if reading.endswith(allowed) and (reading not in allowed or name==suffix) else 'agency reading is partial or name ending requires review'
    return 'full reading of official label including annotations requires review'


def parse_results(page):
    _url(page.url);root=_NameTree(page.text).root
    regions=[s for s in root.find('section') if s.attrs.get('id')=='search_result']
    if len(regions)!=1:raise ValueError('Niigata search result structure absent or ambiguous')
    region=regions[0];counts=region.find('p','number')
    if len(counts)!=1 or not re.fullmatch(r'\s*\d+\s*件\s*',counts[0].text):raise ValueError('Niigata native result total missing')
    total=int(re.sub(r'\D','',counts[0].text));rows=[]
    for index,shrine in enumerate(region.find('div','shrine'),1):
        fields={};dls=shrine.find('dl')
        if len(dls)!=1:raise ValueError('Niigata shrine definition list changed')
        cells=[x for x in dls[0].children if isinstance(x,Node)]
        if len(cells)!=6:raise ValueError('Niigata shrine field count changed')
        for i,(key,label) in enumerate([('name','神社名'),('furigana','ふりがな'),('place','鎮座地')]):
            dt,dd=cells[2*i:2*i+2]
            if dt.tag!='dt' or dt.text!=label or dd.tag!='dd' or key not in dd.attrs.get('class','').split():raise ValueError('Niigata shrine identity labels changed')
            fields[key]=dd
        place=fields['place'];address_parts=[]
        for child in place.children:
            if not isinstance(child,Node):address_parts.append(child);continue
            anchors=child.find('a')
            if child.tag!='span' or len(anchors)!=1 or child.text!='（Google Mapを表示する）' or anchors[0].text!='Google Mapを表示する' or urlsplit(anchors[0].attrs.get('href','')).hostname not in ('maps.google.co.jp',):raise ValueError('unknown Niigata address annotation')
        address=''.join(address_parts).strip();name=_source_name(fields['name']).strip();raw=fields['furigana'].text
        locator=f'section#search_result div.shrine occurrence={index}; dl dd.name/dd.furigana/dd.place'
        row=record(page,name,raw,address,locator,address_raw=address)
        row.update(reading_review_reason=_reading_reason(fields['name'].text,raw),address_display_raw=place.text)
        if fields['name'].find('img'):
            row.update(name_rendering_status='external_glyph')
        rows.append(row)
    if (total and not rows) or total<len(rows):raise ValueError('Niigata result rows inconsistent with total')
    navs=region.find('div','navcnt')
    current=dict(parse_qsl(urlsplit(page.url).query,keep_blank_values=True))
    # Actual one-page/zero-result responses omit navigation entirely. Accept
    # only a first page whose explicit native total is fully accounted for.
    if not navs and current.get('page','1')=='1' and total==len(rows) and not region.find('a','next'):
        return rows,None,total
    if len(navs)!=1:raise ValueError('Niigata pagination region absent or ambiguous')
    next_links=[]
    for a in navs[0].find('a'):
        if 'next' not in a.attrs.get('class','').split():continue
        href=_url(a.attrs.get('href',''),page.url);fields=dict(parse_qsl(urlsplit(href).query,keep_blank_values=True))
        if fields.get('area')!=current.get('area') or fields.get('keyword','')!=current.get('keyword',''):raise ValueError('Niigata next page changes search scope')
        next_links.append(href)
    if len(set(next_links))>1:raise ValueError('ambiguous Niigata next page')
    return rows,next_links[0] if next_links else None,total


def collect_niigata(client,limit=None):
    if limit is not None and (type(limit) is not int or limit<=0):raise ValueError('Niigata limit must be a positive facility count or None')
    pages=[];records=[];failed=[];remaining=[];observed=[];totals={};options=[];source_rows=0;identities=set();seen=set();halt=False
    def note(page):pages.append(dict(url=page.url,sha256=page.sha256,fetched_at=page.fetched_at))
    try:
        page=_fetch(client,INDEX);note(page);starts,options=parse_index(page)
    except (ValueError,FetchError,UnicodeError,OSError) as exc:
        starts=[];failed.append(dict(url=INDEX,reason=str(exc)));remaining.append(INDEX)
    for area_index,start in enumerate(starts):
        area=dict(parse_qsl(urlsplit(start).query))['area'];url=start;area_rows=0
        while url:
            if _identity(url) in seen:
                failed.append(dict(url=url,reason='Niigata pagination loop'));remaining.append(url);break
            seen.add(_identity(url));observed.append(url)
            try:
                page=_fetch(client,url);note(page);rows,more,total=parse_results(page)
                source_rows+=len(rows);area_rows+=len(rows)
                if area in totals and totals[area]!=total:raise ValueError('Niigata native result total changed during traversal')
                totals[area]=total
                for index,row in enumerate(rows):
                    identity=(row['name'],row['address'])
                    if identity not in identities and limit is not None and len(identities)>=limit:
                        remaining.append(dict(url=url,unselected_rows=len(rows)-index));halt=True;break
                    identities.add(identity);records.append(row)
                if halt:
                    if more:remaining.append(more)
                    break
                if more and limit is not None and len(identities)>=limit:
                    remaining.append(more);halt=True;break
                if not more and area_rows!=total:raise ValueError('Niigata observed rows do not match native area total')
                url=more
            except (ValueError,FetchError,UnicodeError,OSError) as exc:
                failed.append(dict(url=url,reason=str(exc)));remaining.append(url);break
        if halt or (limit is not None and len(identities)>=limit and area_index+1<len(starts)):
            remaining.extend(starts[area_index+1:]);break
    data=build_dataset('niigata','15','新潟県','新潟県神社庁',records,pages=pages,metadata=dict(
        limit=limit,authority_status='confirmed',listing_authority='prefectural shrine agency own public HTML search',
        coverage='observed municipality menu links and actual next-page anchors only; no claim of every shrine in prefecture',
        municipality_options=options,native_totals=totals,observed_index_urls=observed,
        source_rows_observed=source_rows,pages_fetched=len(pages),failed_pages=failed,
        remaining_scope=remaining,traversal_complete=not failed and not remaining,redistribution_status='unconfirmed',
        identity_method='exact source name and address; search area/page identifiers are not facility identifiers'))
    by_identity={}
    for row in records:by_identity.setdefault((row['name'],row['address']),[]).append(row)
    facilities={f['id']:f for f in data['facilities']}
    for entry in data['entries']:
        facility=facilities[entry['facility_id']];rows=by_identity[(facility['name_raw'],facility['address'])]
        reasons=sorted({r['reading_review_reason'] for r in rows if r['reading_review_reason']})
        if reasons:entry.update(status='pending',reading='',reason='; '.join(reasons))
        if facility.get('source_conflicts'):entry.update(status='pending',reading='')
        reviews=[r for r in rows if r.get('name_rendering_status')=='external_glyph']
        if reviews:
            reason='source name uses an external glyph; Unicode correction requires references'
            facility.update(status='pending',reason=reason)
            entry.update(status='pending',reason=reason)
            facility['review_occurrences']=[dict(reason=reason,name_raw=r['name'],url=r['url'],locator=r['locator'],page_hash=r['page_hash'],fetched_at=r['fetched_at'],name_rendering_status=r.get('name_rendering_status')) for r in reviews]
        facility['address_display_raw']=rows[0]['address_display_raw']
    return data


REGISTRY={'niigata':dict(code='15',prefecture='新潟県',agency='新潟県神社庁',collect=collect_niigata,reviewed_html_robots=(ORIGIN,))}
