"""Source-specific adapters for northern Japan; unknown structures fail closed.

Only the facts in each identified agency record are accepted. Raw readings
containing aliases remain unchanged so validation can hold them for review.
"""
from html.parser import HTMLParser
import re
from urllib.parse import urljoin, urlsplit


class Node:
    def __init__(self, tag='', attrs=()):
        self.tag=tag; self.attrs=dict(attrs); self.children=[]
    def all(self, tag=None, cls=None):
        for child in self.children:
            if isinstance(child, Node):
                if (tag is None or child.tag==tag) and (cls is None or cls in child.attrs.get('class','').split()):
                    yield child
                yield from child.all(tag,cls)
    def text(self):
        return ''.join(c.text() if isinstance(c,Node) else c for c in self.children).strip()


class Document(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.root=Node(); self.stack=[self.root]; self.feed(html)
    def handle_starttag(self,tag,attrs):
        if tag=='br': self.stack[-1].children.append('\n'); return
        n=Node(tag,attrs); self.stack[-1].children.append(n)
        if tag not in ('area','base','col','embed','hr','img','input','link','meta','param','source','track','wbr'): self.stack.append(n)
    def handle_startendtag(self,tag,attrs):
        self.handle_starttag(tag,attrs); self.handle_endtag(tag)
    def handle_endtag(self,tag):
        for i in range(len(self.stack)-1,0,-1):
            if self.stack[i].tag==tag:
                self.stack=self.stack[:i]; break
    def handle_data(self,data): self.stack[-1].children.append(data)


def decode(page):
    content_type=page.headers.get('content-type','')
    match=re.search(r'charset=["\']?([\w-]+)',content_type,re.I)
    if not match: match=re.search(rb'charset=["\']?([\w-]+)',page.body[:4096],re.I)
    charset=match.group(1) if match else 'utf-8'
    if isinstance(charset,bytes): charset=charset.decode('ascii')
    return page.body.decode(charset,errors='strict')


def links(root,base,predicate):
    return list(dict.fromkeys(urljoin(base,a.attrs['href']) for a in root.all('a') if a.attrs.get('href') and predicate(a)))


def record(page,name,raw,address,locator,**extra):
    return dict(name=name,reading_raw=raw,address=address,url=page.url,
        fetched_at=page.fetched_at,page_hash=page.sha256,locator=locator,
        evidence=f'{name} | {raw} | {address}',**extra)


def parse_akita(page):
    root=Document(decode(page)).root; rows=[]; recognized=False
    for table in root.all('table'):
        trs=list(table.all('tr'))
        if not trs: continue
        headers=[n.text() for n in trs[0].all() if n.tag in ('th','td')]
        if headers!=['神社名(漢字)','神社名(かな)','市町村','鎮座地']: continue
        recognized=True
        for i,tr in enumerate(trs[1:],2):
            cells=[n for n in tr.children if isinstance(n,Node) and n.tag in ('td','th')]
            if len(cells)==1 and cells[0].attrs.get('colspan')=='4' and cells[0].text()=='見つかりません。': continue
            if len(cells)!=4: raise ValueError('Akita table row changed')
            name,raw,context,address_raw=[c.text() for c in cells]
            address=re.sub(r'^〒\d{3}-\d{4}\s*','',address_raw)
            rows.append(record(page,name,raw,address,f'table tr[{i}]',address_raw=address_raw,address_context=context))
    if not recognized: raise ValueError('Akita table structure not recognized')
    return rows


def collect_akita(client,limit=None):
    from njd.records import build_dataset
    start=client.fetch('https://akita-jinjacho.sakura.ne.jp/shrine_search/')
    queue=links(Document(decode(start)).root,start.url,lambda a:'/cat_shrine/' in a.attrs['href'])
    if not queue: raise ValueError('Akita category links missing')
    seen=set(); pages=[start]; records=[]
    while queue:
        url=queue.pop(0)
        if url in seen: continue
        seen.add(url); page=client.fetch(url); pages.append(page)
        records.extend(parse_akita(page))
        queue.extend(links(Document(decode(page)).root,page.url,lambda a:'/cat_shrine/' in a.attrs['href'] and '/page/' in a.attrs['href']))
        if limit is not None and len(records)>=limit: records=records[:limit]; break
    return build_dataset('akita','05','秋田県','秋田県神社庁',records,
        pages=[dict(url=p.url,sha256=p.sha256,fetched_at=p.fetched_at) for p in pages],
        metadata=dict(limit=limit,coverage='all linked kana categories and pagination' if limit is None else 'limited selection',redistribution_status='unconfirmed'))


REGISTRY={'akita':dict(code='05',prefecture='秋田県',agency='秋田県神社庁',collect=collect_akita)}


def parse_miyagi(page):
    from urllib.parse import parse_qs
    root=Document(decode(page)).root; rows=[]
    for i,box in enumerate(root.all(cls='simple-list-item'),1):
        a=next(box.all('a'),None)
        if a is None: raise ValueError('Miyagi record link missing')
        m=re.fullmatch(r'(.+?)（(.*?)）',a.text(),re.S)
        name,raw=m.groups() if m else (a.text(),'')
        addresses=[n.text().removeprefix('[鎮座地]').strip() for n in box.all(cls='simple-meta') if n.text().startswith('[鎮座地]')]
        if len(addresses)!=1: raise ValueError('Miyagi location missing or ambiguous')
        sid=parse_qs(urlsplit(a.attrs['href']).query).get('code',[''])[0]
        rows.append(record(page,name,raw,addresses[0],f'.simple-list-item[{i}]',source_id=sid))
    if not rows: raise ValueError('Miyagi list structure not recognized')
    return rows


def parse_tochigi(page):
    root=Document(decode(page)).root; rows=[]; recognized=False
    for table in root.all('table','shrine_info'):
        trs=list(table.all('tr'))
        headers=[n.text() for n in trs[0].all('th')] if trs else []
        if headers!=['本務神社名','宮司名','住所','TEL']: raise ValueError('Tochigi table header changed')
        recognized=True
        for i,tr in enumerate(trs[1:],2):
            cells=list(tr.all('td'))
            if len(cells)!=4: raise ValueError('Tochigi table row changed')
            full=cells[0].text(); m=re.fullmatch(r'(.+?)\s*（([^（）]+)）',full,re.S)
            name,raw=m.groups() if m else (full,'')
            rows.append(record(page,name.strip(),raw.strip(),cells[2].text(),f'table.shrine_info tr[{i}]'))
    if not recognized: raise ValueError('Tochigi table structure not recognized')
    return rows


def parse_tokyo(page):
    root=Document(decode(page)).root
    names=list(root.all(cls='s_in_tl01')); readings=list(root.all(cls='s_in_rubi')); address_raw=''
    if len(names)!=1 or len(readings)>1: raise ValueError('Tokyo detail title changed')
    for box in root.all(cls='s_ad_box'):
        for ul in box.all('ul'):
            cells=list(ul.all('li'))
            if len(cells)==2 and cells[0].text()=='所在地': address_raw=cells[1].text()
    if not address_raw: raise ValueError('Tokyo detail location missing')
    address=re.sub(r'^〒\d{3}-\d{4}\s*','',address_raw)
    return [record(page,names[0].text(),readings[0].text() if readings else '',address,'.s_in_tl01 + .s_in_rubi; .s_ad_box 所在地',address_raw=address_raw,source_id=urlsplit(page.url).path.rstrip('/').split('/')[-1])]


def _dataset(key,records,pages,limit,coverage):
    from njd.records import build_dataset
    spec=REGISTRY[key]
    return build_dataset(key,spec['code'],spec['prefecture'],spec['agency'],records,
        pages=[dict(url=p.url,sha256=p.sha256,fetched_at=p.fetched_at) for p in pages],
        metadata=dict(limit=limit,coverage=coverage,redistribution_status='unconfirmed'))


def collect_miyagi(client,limit=None):
    url='https://miyagi-jinjacho.or.jp/jinja-search/list.php?chinzachi=&jinja_name=&jinja_kana='
    queue=[url]; seen=set(); pages=[]; records=[]
    while queue:
        url=queue.pop(0)
        if url in seen: continue
        seen.add(url); page=client.fetch(url); pages.append(page); records.extend(parse_miyagi(page))
        queue.extend(links(Document(decode(page)).root,page.url,lambda a:'次の' in a.text() and 'list.php?' in a.attrs['href']))
        if limit is not None and len(records)>=limit: records=records[:limit]; break
    return _dataset('miyagi',records,pages,limit,'all result pages by next link' if limit is None else 'limited selection')


def collect_tochigi(client,limit=None):
    start=client.fetch('http://www.tochigi-jinjacho.or.jp/?p=59'); pages=[start]; records=[]
    root=Document(decode(start)).root
    queue=[]
    for cell in root.all('td','shicyousonmei'): queue.extend(links(cell,start.url,lambda a:True))
    if not queue: raise ValueError('Tochigi municipality links missing')
    for url in dict.fromkeys(queue):
        page=client.fetch(url); pages.append(page); records.extend(parse_tochigi(page))
        if limit is not None and len(records)>=limit: records=records[:limit]; break
    return _dataset('tochigi',records,pages,limit,'all linked municipality honmu tables' if limit is None else 'limited selection')


def collect_tokyo(client,limit=None):
    start=client.fetch('http://www.tokyo-jinjacho.or.jp/jinja/'); pages=[start]; records=[]
    root=Document(decode(start)).root
    areas=links(root,start.url,lambda a:bool(re.search(r'(?:区|多摩|島嶼)$',a.text())) and urlsplit(urljoin(start.url,a.attrs['href'])).hostname==urlsplit(start.url).hostname)
    if not areas: raise ValueError('Tokyo municipality links missing')
    seen=set();seen_areas=set()
    for area in areas:
        if area in seen_areas:continue
        seen_areas.add(area)
        page=client.fetch(area); pages.append(page)
        queue=[]
        for box in Document(decode(page)).root.all(cls='s_top_box'): queue.extend(links(box,page.url,lambda a:True))
        if not queue:
            subareas=tokyo_subareas(Document(decode(page)).root,page.url)
            if not subareas:raise ValueError('Tokyo area shrine links missing: '+area)
            areas.extend(subareas);continue
        for url in queue:
            if url in seen: continue
            seen.add(url); detail=client.fetch(url); pages.append(detail); records.extend(parse_tokyo(detail))
            if limit is not None and len(records)>=limit: break
        if limit is not None and len(records)>=limit: break
    return _dataset('tokyo',records[:limit] if limit is not None else records,pages,limit,'all linked area cards and details' if limit is None else 'limited selection')


REGISTRY.update(miyagi=dict(code='04',prefecture='宮城県',agency='宮城県神社庁',collect=collect_miyagi),
    tochigi=dict(code='09',prefecture='栃木県',agency='栃木県神社庁',collect=collect_tochigi),
    tokyo=dict(code='13',prefecture='東京都',agency='東京都神社庁',collect=collect_tokyo))


FUKUSHIMA_XML='https://fukushima-jinjacho.or.jp/cms/wp-content/themes/style-jinjatyou/search/search_locate.php?q='


def parse_fukushima(page):
    import xml.etree.ElementTree as ET
    root=ET.fromstring(page.body)
    if root.tag!='Locations': raise ValueError('Fukushima XML root changed')
    records=[]
    for i,node in enumerate(root.findall('Locate'),1):
        name=node.findtext('name',''); raw=node.findtext('furigana',''); address=node.findtext('address','')
        if not name or not address: raise ValueError('Fukushima identity fields missing')
        records.append(record(page,name,raw,address,f'/Locations/Locate[{i}]',
            municipality=node.findtext('tinzati2',''),official_url=node.findtext('url','') or None))
    if not records: raise ValueError('Fukushima XML records missing')
    return records


def collect_fukushima(client,limit=None):
    start=client.fetch('https://fukushima-jinjacho.or.jp/search/')
    if FUKUSHIMA_XML.removesuffix('=') not in decode(start): raise ValueError('Fukushima official XML endpoint reference changed')
    page=client.fetch(FUKUSHIMA_XML); records=parse_fukushima(page)
    return _dataset('fukushima',records[:limit] if limit is not None else records,[start,page],limit,
        'all records returned by the official empty-keyword public map search; not prefectural completeness')


REGISTRY['fukushima']=dict(code='07',prefecture='福島県',agency='福島県神社庁',collect=collect_fukushima)


def parse_hokkaido(page):
    root=Document(decode(page)).root; rows=[]
    for lineup in root.all(cls='lineup'):
        for i,box in enumerate(lineup.all(cls='block'),1):
            names=list(box.all('h4')); addresses=list(box.all(cls='address'))
            if len(names)!=1 or len(addresses)!=1: raise ValueError('Hokkaido list card changed')
            a=next(names[0].all('a'),None)
            if a is None: raise ValueError('Hokkaido shrine URL missing')
            rows.append(record(page,names[0].text(),'',addresses[0].text(),f'.lineup .block[{i}]',source_id=urljoin(page.url,a.attrs['href'])))
    if not rows: raise ValueError('Hokkaido lineup missing')
    return rows


def parse_aomori(page):
    root=Document(decode(page)).root; rows=[]
    for box in root.all('div'):
        if not re.fullmatch(r'list_\d+',box.attrs.get('id','')): continue
        for i,tr in enumerate(box.all('tr'),1):
            th=list(tr.all('th')); cells=list(tr.all('td'))
            if len(th)!=1 or len(cells)!=2: raise ValueError('Aomori row changed')
            if not re.fullmatch(r'[0-9０-９]+',th[0].text()): raise ValueError('Aomori record number missing')
            rows.append(record(page,cells[0].text(),'',cells[1].text(),f'#{box.attrs["id"]} tr[{i}]'))
    if not rows: raise ValueError('Aomori facility tables missing')
    return rows


def parse_yamagata(page):
    root=Document(decode(page)).root; titles=list(root.all('h1','p-detail__name'))
    if len(titles)!=1: raise ValueError('Yamagata title changed')
    title=titles[0]; small=list(title.all('small')); raw=''
    if len(small)>1: raise ValueError('Yamagata readings ambiguous')
    if small:
        match=re.fullmatch(r'（([^（）]+)）',small[0].text())
        if not match: raise ValueError('Yamagata title reading changed')
        raw=match.group(1)
    name=''.join(c.text() if isinstance(c,Node) else c for c in title.children if c not in small).strip()
    addresses=[]
    for li in root.all('li'):
        labels=list(li.all('span','p-detail__item'))
        if len(labels)==1 and labels[0].text()=='鎮座地': addresses.append(li.text().removeprefix('鎮座地').strip())
    if len(addresses)!=1: raise ValueError('Yamagata location missing')
    return [record(page,name,raw,addresses[0],'.p-detail__name; li 鎮座地',source_id=urlsplit(page.url).path.rstrip('/').split('/')[-1])]


def parse_kanagawa(page):
    root=Document(decode(page)).root; rows=[]
    for box in root.all(cls='shrineList'):
        names=list(box.all(cls='shrineName')); addresses=list(box.all(cls='address'))
        if len(names)!=1 or len(addresses)!=1: raise ValueError('Kanagawa detail identity changed')
        titles=list(names[0].all('h2')); readings=list(names[0].all(cls='ruby'))
        if len(titles)!=1 or len(readings)>1: raise ValueError('Kanagawa detail title changed')
        address_raw=addresses[0].text(); address=re.sub(r'^住所[：:]\s*','',address_raw)
        address=re.sub(r'^〒\d{3}-\d{4}\s*','',address)
        rows.append(record(page,titles[0].text(),readings[0].text() if readings else '',address,
            '.shrineList .shrineName; .address',address_raw=address_raw,source_id=urlsplit(page.url).path.rstrip('/').split('/')[-1]))
    if len(rows)!=1: raise ValueError('Kanagawa detail not recognized')
    return rows


def parse_saitama(page):
    root=Document(decode(page)).root
    names=[n for n in root.all('caption') if n.attrs.get('id')=='shrine_name']
    addresses=[n for n in root.all('span') if n.attrs.get('id')=='shrine_address']
    if len(names)!=1 or len(addresses)!=1: raise ValueError('Saitama detail identity changed')
    readings=list(root.all('span','name_kana'))
    if len(readings)>1:raise ValueError('Saitama name readings ambiguous')
    raw=readings[0].text() if readings else ''
    return [record(page,names[0].text(),raw,addresses[0].text(),
        'caption#shrine_name; span.name_kana if published; span#shrine_address',source_id=urlsplit(page.url).path.rstrip('/').split('/')[-1])]


def collect_hokkaido(client,limit=None):
    start=client.fetch('https://hokkaidojinjacho.jp/jinja/'); pages=[start]; records=[]
    queue=links(Document(decode(start)).root,start.url,lambda a:'/jinja-area/' in a.attrs['href']); seen=set()
    if not queue: raise ValueError('Hokkaido branch links missing')
    while queue:
        url=queue.pop(0)
        if url in seen: continue
        seen.add(url); page=client.fetch(url); pages.append(page); records.extend(parse_hokkaido(page))
        queue.extend(links(Document(decode(page)).root,page.url,lambda a:'/jinja-area/' in a.attrs['href'] and '/page/' in a.attrs['href']))
        if limit is not None and len(records)>=limit: records=records[:limit];break
    return _dataset('hokkaido',records,pages,limit,'all linked branch list pages; readings absent from lists')


def collect_aomori(client,limit=None):
    start=client.fetch('http://www.aomori-jinjacho.or.jp/sub_1.html'); pages=[start]; records=[]
    queue=links(Document(decode(start)).root,start.url,lambda a:bool(re.fullmatch(r'jinja/sub_1[a-h]\.html',a.attrs['href'])))
    if not queue: raise ValueError('Aomori region links missing')
    for url in queue:
        page=client.fetch(url);pages.append(page);records.extend(parse_aomori(page))
        if limit is not None and len(records)>=limit: records=records[:limit];break
    return _dataset('aomori',records,pages,limit,'all eight linked region lists; readings absent from lists')


def _detail_walk(client,key,start_url,detail_links,next_links,parse,limit):
    queue=[start_url]; visited=set(); seen=set(); records=[]; pages=[]
    while queue:
        url=queue.pop(0)
        if url in visited:continue
        visited.add(url); page=client.fetch(url);pages.append(page);root=Document(decode(page)).root
        detail_urls=detail_links(root,page.url)
        if not detail_urls: raise ValueError(key+' detail links missing')
        for url in detail_urls:
            if url in seen: continue
            seen.add(url); detail=client.fetch(url);pages.append(detail);records.extend(parse(detail))
            if limit is not None and len(records)>=limit:break
        if limit is not None and len(records)>=limit:break
        queue.extend(next_links(root,page.url))
    return _dataset(key,records[:limit] if limit is not None else records,pages,limit,
        'all linked search pages and detail records' if limit is None else 'limited search detail selection')


def collect_yamagata(client,limit=None):
    return _detail_walk(client,'yamagata','https://yamagata-jinjyacho.or.jp/shrine_search',
        lambda root,base:links(root,base,lambda a:'c-list__card' in a.attrs.get('class','').split()),
        lambda root,base:links(root,base,lambda a:'c-pager__next' in a.attrs.get('class','').split()),parse_yamagata,limit)


def collect_kanagawa(client,limit=None):
    def details(root,base):
        urls=[]
        for box in root.all(cls='shrineName'): urls.extend(links(box,base,lambda a:True))
        return list(dict.fromkeys(urls))
    return _detail_walk(client,'kanagawa','https://www.kanagawa-jinja.or.jp/?search_element_2=&s_keyword_3=&csp=search_add&feadvns_max_line_3=4&fe_form_no=3',
        details,lambda root,base:links(root,base,lambda a:'next' in a.attrs.get('class','').split() and 'page-numbers' in a.attrs.get('class','').split()),parse_kanagawa,limit)


def collect_saitama(client,limit=None):
    from urllib.parse import urlencode
    start=client.fetch('https://www.saitama-jinjacho.or.jp/search/'); pages=[start];records=[];seen=set()
    root=Document(decode(start)).root
    selects=[n for n in root.all('select') if n.attrs.get('name')=='search_element_1']
    if len(selects)!=1:raise ValueError('Saitama municipality selector missing')
    for opt in selects[0].all('option'):
        value=opt.attrs.get('value','')
        if not value:continue
        params=dict(s_keyword_0='',search_element_1=value,csp='search_add',feadvns_max_line_0='3',fe_form_no='0')
        queue=['https://www.saitama-jinjacho.or.jp/?'+urlencode(params)]; visited=set()
        while queue:
            url=queue.pop(0)
            if url in visited:continue
            visited.add(url);page=client.fetch(url);pages.append(page);r=Document(decode(page)).root
            detail_urls=[]
            for h in r.all('h2','shrine_name'):detail_urls.extend(links(h,page.url,lambda a:True))
            if not detail_urls: raise ValueError('Saitama municipality results missing: '+value)
            for url in detail_urls:
                if url in seen:continue
                seen.add(url);detail=client.fetch(url);pages.append(detail);records.extend(parse_saitama(detail))
                if limit is not None and len(records)>=limit:break
            if limit is not None and len(records)>=limit:break
            queue.extend(links(r,page.url,lambda a:'next' in a.attrs.get('class','').split()))
        if limit is not None and len(records)>=limit:break
    return _dataset('saitama',records[:limit] if limit is not None else records,pages,limit,
        'all municipality search pages and details' if limit is None else 'limited municipality detail selection')


REGISTRY.update(hokkaido=dict(code='01',prefecture='北海道',agency='北海道神社庁',collect=collect_hokkaido),
    aomori=dict(code='02',prefecture='青森県',agency='青森県神社庁',collect=collect_aomori),
    yamagata=dict(code='06',prefecture='山形県',agency='山形県神社庁',collect=collect_yamagata),
    saitama=dict(code='11',prefecture='埼玉県',agency='埼玉県神社庁',collect=collect_saitama),
    kanagawa=dict(code='14',prefecture='神奈川県',agency='神奈川県神社庁',collect=collect_kanagawa))


def parse_toyama(page):
    root=Document(decode(page)).root; values={}
    for tr in root.all('tr'):
        th=[n for n in tr.children if isinstance(n,Node) and n.tag=='th']
        td=[n for n in tr.children if isinstance(n,Node) and n.tag=='td']
        if len(th)==1 and len(td)==1 and th[0].text() in ('神社名','社名カナ','鎮座地'):
            label=th[0].text()
            if label in values:raise ValueError('Toyama repeated shrine field')
            values[label]=td[0].text()
    if any(label not in values for label in ('神社名','社名カナ','鎮座地')):raise ValueError('Toyama shrine field structure changed')
    if not any(values.values()):return []
    if not values['神社名']:return []
    # The post title and the field 住所 describe a parish area. Neither is the
    # shrine location. The homepage is labelled 宮司所在神社, not this facility.
    identity={} if values['鎮座地'] else dict(source_id=page.url)
    return [record(page,values['神社名'],values.get('社名カナ',''),values['鎮座地'],
        'table 神社名 / 社名カナ / 鎮座地',address_context='氏神検索: parish post title and 住所 not used as shrine location',**identity)]


def parse_ibaraki(page):
    root=Document(decode(page)).root; records=[]
    for i,tr in enumerate(root.all('tr'),1):
        cells=[n for n in tr.children if isinstance(n,Node) and n.tag=='td']
        if len(cells)!=4:continue
        anchors=list(cells[1].all('a'))
        if len(anchors)!=1 or not re.fullmatch(r'jinja/\d+\.html',anchors[0].attrs.get('href','')):continue
        name=cells[1].text();raw=cells[2].text();city=cells[3].text()
        if not name or not city: raise ValueError('Ibaraki list identity changed')
        records.append(record(page,name,raw,city,f'tr[{i}]',source_id=urljoin(page.url,anchors[0].attrs['href']),
            municipality=city,address_context='municipality only in regional list; street address not collected'))
    if not records: raise ValueError('Ibaraki regional shrine rows missing')
    return records


def collect_ibaraki(client,limit=None):
    start=client.fetch('https://www.ibarakiken-jinjacho.or.jp/ibaraki/');pages=[start];records=[]
    root=Document(decode(start)).root
    urls=list(dict.fromkeys(urljoin(start.url,a.attrs['href']) for a in root.all('area') if re.fullmatch(r'(?:kenhoku|kenou|kensei|rokko|kennan)/index\.html',a.attrs.get('href',''))))
    if len(urls)!=5:raise ValueError('Ibaraki five regional map links missing')
    for url in urls:
        page=client.fetch(url);pages.append(page);records.extend(parse_ibaraki(page))
        if limit is not None and len(records)>=limit:records=records[:limit];break
    return _dataset('ibaraki',records,pages,limit,'all five regional introduction lists; municipality-only addresses retained verbatim')


def collect_toyama(client,limit=None):
    from urllib.parse import urlencode
    start=client.fetch('https://toyama-jinjacho.sakura.ne.jp/%E5%AF%8C%E5%B1%B1%E7%9C%8C%E6%B0%8F%E7%A5%9E%E7%A5%9E%E7%A4%BE%E6%A4%9C%E7%B4%A2')
    if 'https://toyama-jinjacho.sakura.ne.jp/ujigami/' not in decode(start):raise ValueError('Toyama official embedded search reference missing')
    pages=[start];records=[];seen=set();visited=set();unusable=[]
    # Search terms select explicit municipal-address titles, never infer names
    # or readings. The resulting scope is stated rather than called complete.
    for term in ('市','町','村'):
        queue=['https://toyama-jinjacho.sakura.ne.jp/ujigami/?'+urlencode({'s':term})]
        while queue:
            url=queue.pop(0)
            if url in visited:continue
            visited.add(url);page=client.fetch(url);pages.append(page);root=Document(decode(page)).root
            detail_urls=[]
            for h in root.all(cls='entry-title'):detail_urls.extend(links(h,page.url,lambda a:True))
            if not detail_urls:raise ValueError('Toyama municipal search results missing')
            for url in detail_urls:
                if url in seen:continue
                seen.add(url);detail=client.fetch(url);pages.append(detail);parsed=parse_toyama(detail);records.extend(parsed)
                if not parsed:unusable.append(dict(url=detail.url,reason='published shrine name is empty; parish address or kana alone cannot establish a named facility'))
                if limit is not None and len(records)>=limit:break
            if limit is not None and len(records)>=limit:break
            queue.extend(toyama_next(root,page.url))
        if limit is not None and len(records)>=limit:break
    data=_dataset('toyama',records[:limit] if limit is not None else records,pages,limit,
        'municipal-title search scopes 市 / 町 / 村, all linked pages; same name+shrine-location parish records reconciled by canonical builder; not a completeness claim')
    data['collection']['unusable_parish_records']=unusable
    return data


REGISTRY.update(ibaraki=dict(code='08',prefecture='茨城県',agency='茨城県神社庁',collect=collect_ibaraki),
    toyama=dict(code='16',prefecture='富山県',agency='富山県神社庁',collect=collect_toyama))


def parse_iwate(page):
    root=Document(decode(page)).root; records=[]
    blocks=[n for n in root.all('div') if n.attrs.get('id')=='block142']
    if len(blocks)!=1:raise ValueError('Iwate prefectural shrine link block missing')
    for section in blocks[0].all('section'):
        a=next(section.all('a'),None)
        if a is None:raise ValueError('Iwate shrine official link missing')
        match=re.fullmatch(r'(.+?)\s*[（(](.+?)鎮座[）)]',a.text())
        if not match:raise ValueError('Iwate shrine name/location changed')
        name,address=match.groups()
        records.append(record(page,name.strip(),'',address.strip(),f'section#{section.attrs.get("id", "")}',
            official_url=urljoin(page.url,a.attrs['href']),source_id=section.attrs.get('data-record-id')))
    if not records:raise ValueError('Iwate shrine links missing')
    return records


def collect_iwate(client,limit=None):
    page=client.fetch('https://www.jinjacho.jp/pages/62/')
    return _dataset('iwate',parse_iwate(page)[:limit] if limit is not None else parse_iwate(page),[page],limit,
        'all three prefectural shrine links on agency link page; readings not present; not prefectural completeness')


REGISTRY['iwate']=dict(code='03',prefecture='岩手県',agency='岩手県神社庁',collect=collect_iwate)


CHIBA_LIST='https://hiroba.jinja.ne.jp/ycDB/Board.cgi/001/db/ycDB-pc-jinja_list.html'


def parse_chiba(page):
    root=Document(decode(page)).root; records=[]
    for i,tr in enumerate(root.all('tr'),1):
        cells=[n for n in tr.children if isinstance(n,Node) and n.tag=='td']
        if len(cells)!=5 or cells[1].attrs.get('rowspan')!='3':continue
        anchors=list(cells[1].all('a'))
        if len(anchors)!=1:raise ValueError('Chiba shrine name link changed')
        sid=re.search(r'search:word=(\d+)',anchors[0].attrs.get('href',''))
        if sid is None:raise ValueError('Chiba native shrine id missing')
        raw=''.join(c.text() if isinstance(c,Node) else c for c in cells[1].children if c is not anchors[0]).strip()
        address_raw=cells[3].text();address=' '.join(address_raw.split())
        records.append(record(page,anchors[0].text(),raw,address,f'tr[{i}] rowspan shrine cell',
            source_id=sid.group(1),address_raw=address_raw,address_context='whitespace and HTML line breaks collapsed to single spaces'))
    if not records:raise ValueError('Chiba search table missing')
    return records


def collect_chiba(client,limit=None):
    from urllib.parse import urlencode
    agency=client.fetch('https://www.jinjacho.or.jp/')
    if 'jinja.ne.jp' not in decode(agency):raise ValueError('Chiba agency external search link not found')
    start=client.fetch('https://hiroba.jinja.ne.jp/exploration/index.html')
    if '監修' not in decode(start) or '千葉県神社庁' not in decode(start) or '/ycDB/Board.cgi/001/db/ycDB-pc-jinja_list.html' not in decode(start):
        raise ValueError('Chiba official supervised search relationship changed')
    pages=[agency,start];records=[];number=None;seen=set()
    params={'mode:search':'1','search:method':'group','view:sort':'jinja_id','s:j_ADDR_PREF:fb:1:ADDR:and':'千葉県','s:j_ADDR_1:like:1:ADDR:and':''}
    while True:
        query=dict(params)
        if number is not None:query['view:page']=str(number)
        url=CHIBA_LIST+'?'+urlencode(query,encoding='shift_jis')
        if url in seen:raise ValueError('Chiba pagination cycle')
        seen.add(url);page=client.fetch(url);pages.append(page);records.extend(parse_chiba(page))
        if limit is not None and len(records)>=limit:records=records[:limit];break
        root=Document(decode(page)).root
        form=next((n for n in root.all('form') if n.attrs.get('name')=='viewPages'),None)
        if form is None:raise ValueError('Chiba page form missing')
        params={n.attrs['name']:n.attrs.get('value','') for n in form.all('input') if n.attrs.get('type','').lower()=='hidden' and n.attrs.get('name') and n.attrs['name']!='view:page'}
        next_links=[a for a in root.all('a') if '次の30件' in a.text()]
        if not next_links:break
        match=re.fullmatch(r'javascript:viewPage\(\s*(\d+)\s*\);',next_links[0].attrs.get('href',''))
        if match is None:raise ValueError('Chiba pagination link changed')
        number=int(match.group(1))
    return _dataset('chiba',records,pages,limit,'all public Chiba prefecture search results, including honmu and kenmu; not shrine count of entire prefecture')


REGISTRY['chiba']=dict(code='12',prefecture='千葉県',agency='千葉県神社庁（神社のひろば監修）',collect=collect_chiba)


def toyama_next(root,base):
    return links(root,base,lambda a:a.text().startswith('次へ') and urlsplit(urljoin(base,a.attrs['href'])).hostname==urlsplit(base).hostname and bool(re.search(r'/ujigami/page/\d+/',urljoin(base,a.attrs['href']))))


def tokyo_subareas(root,base):
    return links(root,base,lambda a:bool(re.search(r'[市町村]$',a.text())) and urljoin(base,a.attrs['href']).startswith(base) and urljoin(base,a.attrs['href'])!=base)
