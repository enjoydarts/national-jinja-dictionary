"""Conservative adapters for official central-Japan shrine listings.

Only explicit same-row readings are accepted. Missing readings remain empty.
Raw HTML and working datasets belong in a private cache, never this package.
"""
from html.parser import HTMLParser
import re
from urllib.parse import urljoin, urlsplit


class Node:
    def __init__(self, tag='', attrs=()):
        self.tag=tag; self.attrs=dict(attrs); self.children=[]
    def text(self):
        return ''.join(x.text() if isinstance(x,Node) else x for x in self.children)
    def find(self, tag):
        result=[]
        for x in self.children:
            if isinstance(x,Node):
                if x.tag==tag: result.append(x)
                result.extend(x.find(tag))
        return result


class Document(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.root=Node(); self.stack=[self.root]; self.feed(html)
    def handle_starttag(self,tag,attrs):
        node=Node(tag,attrs); self.stack[-1].children.append(node)
        if tag=='br': node.children.append('\n')
        if tag not in ('area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'):
            self.stack.append(node)
    def handle_startendtag(self,tag,attrs):
        self.handle_starttag(tag,attrs)
        if self.stack[-1].tag==tag:self.stack.pop()
    def handle_endtag(self,tag):
        for i in range(len(self.stack)-1,0,-1):
            if self.stack[i].tag==tag:
                del self.stack[i:];break
    def handle_data(self,data):
        self.stack[-1].children.append(data)


def decode_html(page):
    content_type=page.headers.get('content-type','')
    match=re.search(r'charset\s*=\s*["\']?([\w-]+)',content_type,re.I)
    if not match:
        match=re.search(rb'charset\s*=\s*["\']?([\w-]+)',page.body[:4096],re.I)
    encoding=match.group(1) if match else 'utf-8'
    if isinstance(encoding,bytes):encoding=encoding.decode('ascii')
    if encoding.lower() in ('shift_jis','shift-jis','sjis'):encoding='cp932'
    return page.body.decode(encoding,errors='strict')


def clean(text): return re.sub(r'\s+',' ',text).strip()

def cells(row):
    return [x for x in row.children if isinstance(x,Node) and x.tag in ('td','th')]

def row_result(name,reading,address,row,index,**kwargs):
    return dict(name=clean(name),reading_raw=clean(reading),address=clean(address),
        locator=f'table tr[{index}]',evidence=clean(row.text()),**kwargs)


def parse_nara(html):
    records=[]
    for i,row in enumerate(Document(html).root.find('tr'),1):
        cs=cells(row)
        if len(cs)!=3:continue
        address=re.sub(r'^〒\d{3}-\d{4}\s*','',cs[1].text().strip())
        if not re.search('[市町村]',address):continue
        kana=[s for s in cs[0].find('span') if 'kana' in s.attrs.get('class','').split()]
        reading=kana[0].text() if len(kana)==1 else ''
        name=cs[0].text().replace(reading,'',1) if reading else cs[0].text()
        if not clean(name):continue
        links=cs[2].find('a')
        records.append(row_result(name,reading,address,row,i,official_url=links[0].attrs.get('href') if links else None))
    return records


def parse_osaka(html):
    records=[]
    for i,row in enumerate(Document(html).root.find('tr'),1):
        cs=cells(row)
        if len(cs)!=3 or not clean(cs[0].text()).isdigit():continue
        match=re.fullmatch(r'\s*(.+?)\s*[（(]([ぁ-ゖー\s]+)[）)]\s*',cs[1].text(),re.S)
        if not match:continue
        lines=[clean(x) for x in cs[2].text().splitlines() if clean(x)]
        if not lines or not re.search('[市町村]',lines[-1]):continue
        links=cs[1].find('a')
        records.append(row_result(match[1],match[2],lines[-1],row,i,
            detail_url=links[0].attrs.get('href') if links else None))
    return records


def parse_rows(html,kind):
    records=[]
    for table in Document(html).root.find('table'):
        rows=table.find('tr'); recognized=False
        for i,row in enumerate(rows,1):
            cs=cells(row); values=[clean(c.text()) for c in cs]
            if kind=='shimane':
                if values[:3]==['神社名(正称)','主祭神','鎮座地']:recognized=True;continue
                if not recognized or len(cs)!=4:continue
                name,address=values[0],values[2]
            elif kind=='yamanashi':
                if len(cs)!=6 or not values[0].isdigit():continue
                name,address=values[1:3]
            else:raise ValueError('unknown table kind')
            if not name or not address or not re.search('[市町村]',address):continue
            links=cs[0 if kind=='shimane' else 1].find('a')
            records.append(row_result(name,'',address,row,i,
                source_id=values[0] if kind=='yamanashi' else None,
                detail_url=links[0].attrs.get('href') if links else None))
    return records


def parse_shizuoka(html):
    records=[]
    for table in Document(html).root.find('table'):
        recognized=False
        for i,row in enumerate(table.find('tr'),1):
            cs=cells(row); values=[clean(c.text()) for c in cs]
            if values[:3]==['神社名','よみがな','鎮座地']:recognized=True;continue
            if not recognized or len(cs)!=4:continue
            if not values[0] or not re.search('[市町村]',values[2]):continue
            a=cs[0].find('a');href=a[0].attrs.get('href','') if a else ''
            match=re.search(r'id=(\d+)',href)
            records.append(row_result(values[0],values[1],values[2],row,i,source_id=match[1] if match else None))
    return records


def parse_nagano(html):
    records=[]
    for table in Document(html).root.find('table'):
        nested={id(row) for child in table.find('table') for row in child.find('tr')}
        recognized=False
        for i,row in enumerate((r for r in table.find('tr') if id(r) not in nested),1):
            cs=cells(row);values=[clean(c.text()) for c in cs]
            if values==['神社名','〒','住所']:recognized=True;continue
            if recognized and len(cs)==3 and values[0] and re.search('[市町村]',values[2]):
                records.append(row_result(values[0],'',values[2],row,i))
    return records


def parse_ishikawa(html):
    root=Document(html).root
    cards=[n for n in root.find('li') if 'search_li' in n.attrs.get('class','').split()]
    if cards:
        records=[]
        for i,card in enumerate(cards,1):
            rubies=card.find('ruby');addresses=[]
            if len(rubies)!=1:continue
            ruby=rubies[0];readings=ruby.find('rt')
            name=''.join(n if isinstance(n,str) else n.text() for n in ruby.children if not isinstance(n,Node) or n.tag not in ('rt','rp'))
            for dl in card.find('dl'):
                children=[n for n in dl.children if isinstance(n,Node)]
                for a,b in zip(children,children[1:]):
                    if a.tag=='dt' and clean(a.text())=='[鎮座地]' and b.tag=='dd':addresses.append(clean(b.text()))
            detail=[a.attrs['href'] for a in card.find('a') if not clean(a.text()) and re.search(r'/shrine/j\d+/?$',a.attrs.get('href',''))]
            if len(addresses)!=1 or len(detail)!=1 or not re.search('[市町村]',addresses[0]):continue
            records.append(dict(name=clean(name),reading_raw=clean(readings[0].text()) if len(readings)==1 else '',
                address=addresses[0],source_id=detail[0],locator=f'li.search_li[{i}] ruby; dl dt[[鎮座地]] + dd',
                evidence=clean(ruby.text())+' / [鎮座地] '+addresses[0]))
        return records
    title=[n for n in root.find('h1') if n.find('ruby')]
    # Fixtures may use a div title; production pages use h1.title.
    if not title:title=[n for n in root.find('div') if n.attrs.get('class')=='jinja_title']
    if len(title)!=1:return []
    ruby=title[0].find('ruby')[0]; rt=ruby.find('rt')
    name=''.join(n if isinstance(n,str) else n.text() for n in ruby.children if not isinstance(n,Node) or n.tag not in ('rt','rp'))
    address=''
    for dl in root.find('dl'):
        children=[n for n in dl.children if isinstance(n,Node)]
        for a,b in zip(children,children[1:]):
            if a.tag=='dt' and clean(a.text())=='鎮座地' and b.tag=='dd':address=clean(b.text())
    if not address or not re.search('[市町村]',address):return []
    return [dict(name=clean(name),reading_raw=clean(rt[0].text()) if len(rt)==1 else '',address=address,
        locator='h1.title ruby; dl dt[鎮座地] + dd',evidence=clean(title[0].text())+' / 鎮座地 '+address)]


def parse_tottori(html):
    records=[]
    for table in Document(html).root.find('table'):
        fields={};inventory=False
        for i,row in enumerate(table.find('tr'),1):
            cs=cells(row)
            if len(cs)==2:fields[clean(cs[0].text())]=clean(cs[1].text())
            values=[clean(c.text()) for c in cs]
            if values==['番号','神社名','鎮座地']:inventory=True;continue
            if inventory and len(cs)==3 and values[0].isdigit() and not cs[1].find('a') and values[1] and re.search('[市町村]',values[2]):
                records.append(row_result(values[1],'',values[2],row,i,_unlinked=True))
        if fields.get('神社名') and re.search('[市町村]',fields.get('住所','')):
            records.append(dict(name=fields['神社名'],reading_raw=fields.get('よみ',''),address=fields['住所'],
                locator='table labeled rows 神社名/よみ/住所',evidence=' / '.join(k+'='+fields.get(k,'') for k in ('神社名','よみ','住所'))))
    return records


def parse_shiga(html):
    records=[]
    # Pair each title with its immediately following postal-address span.
    pattern=r'<a\b[^>]*href=["\']([^"\']*view:oid=(\d+))[^>]*>(.*?)</a>\s*<br\s*/?>\s*(?:&nbsp;|\s)*<span[^>]*>(〒.*?)</span>'
    for i,m in enumerate(re.finditer(pattern,html,re.S|re.I),1):
        name=re.sub(r'^〔[^〕]*〕\s*','',clean(Document(m[3]).root.text()))
        address=re.sub(r'^〒\d{7}\s*','',clean(Document(m[4]).root.text()))
        if not name or not re.search('[市町村]',address):continue
        records.append(dict(name=name,reading_raw='',address=address,source_id=m[2],
            locator=f'a.news_title[{i}] + postal address span',evidence=clean(Document(m[0]).root.text())))
    return records


def table_html(node):
    return ''.join('<a href="'+n.attrs['href']+'"></a>' for n in node.find('a') if n.attrs.get('href'))


def parse_fukui(html):
    records=[]
    for i,row in enumerate(Document(html).root.find('div'),1):
        cs=[x for x in row.children if isinstance(x,Node) and x.tag=='div']
        names=[x for x in cs if x.attrs.get('class')=='result_shrine']
        addresses=[x for x in cs if x.attrs.get('class')=='result_enshrined']
        if len(names)!=1 or len(addresses)!=1:continue
        reading=names[0].find('span');anchors=names[0].find('a')
        if len(reading)!=1 or len(anchors)!=1:continue
        raw=clean(reading[0].text());name=clean(names[0].text().replace(reading[0].text(),'',1))
        address=clean(addresses[0].text());m=re.search(r"clickDetail\('([^']+)'\)",anchors[0].attrs.get('href',''))
        if name and re.search('[市町村]',address):
            records.append(row_result(name,raw,address,row,i,source_id=m[1] if m else None))
    return records


def links(html,url,pattern):
    return sorted({urljoin(url,a.attrs['href']).split('#')[0]
        for a in Document(html).root.find('a') if a.attrs.get('href')
        and re.search(pattern,urljoin(url,a.attrs['href']))
        and urlsplit(urljoin(url,a.attrs['href'])).netloc==urlsplit(url).netloc})


CONFIG={
    'nara':('29','奈良県','奈良県神社庁','https://www.naraken-jinjacho.jp/jinja.html',r'/jinja(?:\d+)?\.html$',parse_nara),
    'osaka':('27','大阪府','大阪府神社庁','https://www.osaka-jinjacho.jp/funai_jinja/index.html',r'/funai_jinja/dai\d+shibu/[^/]+/[^/]+\.html$',parse_osaka),
    'yamanashi':('19','山梨県','山梨県神社庁','https://www.yamanashi-jinjacho.or.jp/intro/',r'/intro/list/map/\d+(?:/\d+)?$',lambda h:parse_rows(h,'yamanashi')),
    'shimane':('32','島根県','島根県神社庁','https://www.shimane-jinjacho.or.jp/search/index.html',r'/(?:matsue|yasugi|izumo|unnan|okuizumo|iinan|oda|misato|kawamoto|onan|gotsu|hamada|masuda|tsuwano|yoshika|nishinoshima|chibumura|ama|okinoshima)/index\.html$',lambda h:parse_rows(h,'shimane')),
}

CONFIG.update({
    'fukui':('18','福井県','福井県神社庁','https://www.jinja-fukui.jp/result/?SearchType=1&Chiku=01',r'(?!)',parse_fukui),
    'shizuoka':('22','静岡県','静岡県神社庁','http://www.shizuoka-jinjacho.or.jp/shokai/',r'/shokai/(?:area\.php\?area=\d+|search\.php\?mode=city&[^#]+)(?:&[^#]*)?$',parse_shizuoka),
    'nagano':('20','長野県','長野県神社庁','https://www.nagano-jinjacho.jp/j-syoukai.html',r'/shibu/[^/]+\.htm$',parse_nagano),
    'ishikawa':('17','石川県','石川県神社庁','https://www.ishikawa-jinjacho.or.jp/?s=',r'/page/\d+/\?s=?$',parse_ishikawa),
    'shiga':('25','滋賀県','滋賀県神社庁','https://www.shiga-jinjacho.jp/ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-search.html?mode:search=1&view:term=100',r'(?!)',parse_shiga),
    'tottori':('31','鳥取県','鳥取縣神社廳','https://tottori-jinjacho.jp/pages/961/',r'/pages/(?:95[89]|96[01]|5[6-9]|6\d|7[0-3])/$',parse_tottori),
})


def collect_source(source_key,client,limit=None):
    from njd.records import build_dataset
    code,prefecture,agency,start,pattern,parser=CONFIG[source_key]
    queue=[start]; seen=set(); records=[]; pages=[]; errors=[]; observed=0
    while queue:
        url=queue.pop(0)
        if url in seen:continue
        seen.add(url)
        try:page=client.fetch(url); html=decode_html(page)
        except Exception as exc:
            errors.append(dict(url=url,error=str(exc)));continue
        pages.append(dict(url=page.url,sha256=page.sha256,fetched_at=page.fetched_at))
        extracted=parser(html);observed+=len(extracted)
        for r in extracted:
            if limit is not None and len(records)>=limit:break
            r['url']=page.url;r['fetched_at']=page.fetched_at;r['page_hash']=page.sha256
            detail=r.pop('detail_url',None)
            unlinked=r.pop('_unlinked',False)
            if source_key in ('ishikawa','tottori') and not unlinked and not r.get('source_id'):r['source_id']=page.url
            if detail and source_key=='shimane':r['source_id']=urljoin(page.url,detail)
            records.append(r)
        if limit is not None and len(records)>=limit:break
        if source_key=='shiga' and len(extracted)==100:
            match=re.search(r'view:page=(\d+)',url)
            next_page=int(match[1])+1 if match else 2
            base=url.split('&view:page=')[0]
            queue.append(base+'&view:page='+str(next_page))
        if source_key=='tottori':
            for table in Document(html).root.find('table'):
                if any('神社名' in r.text() and '鎮座地' in r.text() for r in table.find('tr')):
                    queue.extend(u for u in links(table_html(table),page.url,r'/pages/\d+/$') if u not in seen and u not in queue)
        if source_key!='osaka' or url==start:
            queue.extend(u for u in links(html,page.url,pattern) if u not in seen and u not in queue)
    if not records:raise ValueError(f'{source_key}: no recognized facility rows; {errors}')
    return build_dataset(source_key,code,prefecture,agency,records,pages=pages,metadata=dict(
        source_rows_observed=observed,pages_fetched=len(pages),errors=errors,
        remaining_scope=queue,limit=limit,coverage='public linked listing pages only; not all prefectural shrines',
        redistribution_status='unconfirmed'))


def _collector(key):
    return lambda client,limit=None:collect_source(key,client,limit)

REGISTRY={k:dict(code=v[0],prefecture=v[1],agency=v[2],collect=_collector(k)) for k,v in CONFIG.items()}
