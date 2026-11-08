"""Conservative collectors for official western Japan shrine agency listings.

Page bodies stay in the caller's private HTTP cache. Redistribution permission
is deliberately distinct from collecting factual records for local review.
"""
from html.parser import HTMLParser
import re
from urllib.parse import urljoin, urlsplit

class Node:
    def __init__(self,tag='',attrs=None):
        self.tag=tag; self.attrs=dict(attrs or []); self.children=[]
    @property
    def raw_text(self):
        return ''.join(c.raw_text if isinstance(c,Node) else c for c in self.children)
    @property
    def text(self):return self.raw_text.strip()
    def find(self,tag=None,cls=None):
        found=[]
        for c in self.children:
            if not isinstance(c,Node):continue
            if (tag is None or c.tag==tag) and (cls is None or cls in c.attrs.get('class','').split()):found.append(c)
            found.extend(c.find(tag,cls))
        return found

class Tree(HTMLParser):
    def __init__(self,html):
        super().__init__(convert_charrefs=True);self.root=Node();self.stack=[self.root];self.feed(html)
    def handle_starttag(self,tag,attrs):
        n=Node(tag,attrs);self.stack[-1].children.append(n)
        if tag=='br':n.children.append('\n')
        if tag not in ('br','img','input','meta','link','hr','source','area','wbr','embed','param'):self.stack.append(n)
    def handle_endtag(self,tag):
        for i in range(len(self.stack)-1,0,-1):
            if self.stack[i].tag==tag:del self.stack[i:];break
    def handle_data(self,data):self.stack[-1].children.append(data)

def record(page,name,reading,address,locator,**extra):
    return dict(name=name,reading_raw=reading,address=address,url=page.url,
        fetched_at=page.fetched_at,page_hash=page.sha256,locator=locator,
        evidence=f'{locator}: 名称={name}; 掲載読み={reading}; 所在地={address}',**extra)

def parse_okayama(page):
    out=[]
    for n in Tree(page.text).root.find('a','shrineList__row'):
        c=n.find('div','shrineList__cell');addresses=n.find('span','item-address')
        if len(c)<5 or len(addresses)!=1:raise ValueError('Okayama record structure changed')
        r=record(page,c[1].text,c[2].text,addresses[0].text,
                 'a.shrineList__row[href="'+n.attrs.get('href','')+'"]',source_id=c[0].text)
        # Listing URL contains the original row evidence; native code gives identity.
        r['official_url']=None
        out.append(r)
    if not out:raise ValueError('Okayama listing structure not recognized')
    return out

def parse_kagoshima(page):
    out=[]
    for n in Tree(page.text).root.find('div','shrine_detail'):
        fields={}
        for li in n.find('li'):
            k,sep,v=li.text.partition('：')
            if sep:fields[k.strip()]=v.strip()
        if '神社名' not in fields or '鎮座地' not in fields:raise ValueError('Kagoshima record structure changed')
        detail=[a for a in n.find('a') if 'この神社の詳細を見る' in a.text]
        if len(detail)!=1:raise ValueError('Kagoshima detail identity missing')
        href=urljoin(page.url,detail[0].attrs['href']); native=urlsplit(href).path.strip('/').split('/')[-1]
        address=re.sub(r'^〒\s*\d{3}-?\d{4}\s*','',fields['鎮座地'])
        out.append(record(page,fields['神社名'],fields.get('神社名カナ',''),address,
            'div.shrine_detail a[href="'+detail[0].attrs['href']+'"]',source_id=native,
            address_raw=fields['鎮座地']))
    if not out:raise ValueError('Kagoshima listing structure not recognized')
    return out

def _collect(client,key,code,prefecture,agency,starts,parser,page_pattern,limit=None):
    from njd.records import build_dataset
    queue=list(starts);seen=set();pages=[];records=[];observed=0
    while queue:
        url=queue.pop(0)
        if url in seen:continue
        seen.add(url);p=client.fetch(url)
        pages.append(dict(url=p.url,sha256=p.sha256,fetched_at=p.fetched_at))
        current=parser(p);observed+=len(current)
        for r in current:
            records.append(r)
            if limit is not None and len(records)>=limit:break
        if limit is not None and len(records)>=limit:break
        links=Tree(p.text).root.find('a')
        for a in links:
            href=urljoin(p.url,a.attrs.get('href',''))
            if re.fullmatch(page_pattern,href) and href not in seen and href not in queue:queue.append(href)
    return build_dataset(key,code,prefecture,agency,records,pages=pages,metadata=dict(
        limit=limit,source_rows_observed=observed,pages_fetched=len(pages),
        traversal_complete=not queue and limit is None,redistribution_status='unconfirmed',
        coverage='all discoverable listing pages' if limit is None else 'limited local sample'))

def collect_okayama(client,limit=None):
    return _collect(client,'okayama','33','岡山県','岡山県神社庁',
        ['https://www.okayama-jinjacho.or.jp/search/list/'],parse_okayama,
        r'https://www\.okayama-jinjacho\.or\.jp/search/list/(?:page/\d+/)?',limit)

def collect_kagoshima(client,limit=None):
    entry=client.fetch('https://www.kagojinjacho.or.jp/search-page/')
    starts=[]
    for a in Tree(entry.text).root.find('a'):
        href=urljoin(entry.url,a.attrs.get('href',''))
        if re.fullmatch(r'https://www\.kagojinjacho\.or\.jp/category/shrine-search/[^/]+/',href) and href not in starts:starts.append(href)
    if not starts:raise ValueError('Kagoshima area links absent')
    return _collect(client,'kagoshima','46','鹿児島県','鹿児島県神社庁',starts,parse_kagoshima,
        r'https://www\.kagojinjacho\.or\.jp/category/shrine-search/[^/]+/(?:page/\d+/)?',limit)

REGISTRY={
    'okayama':dict(code='33',prefecture='岡山県',agency='岡山県神社庁',collect=collect_okayama),
    'kagoshima':dict(code='46',prefecture='鹿児島県',agency='鹿児島県神社庁',collect=collect_kagoshima),
}

def parse_ehime(page):
    fields={}
    for table in Tree(page.text).root.find('table'):
        for tr in table.find('tr'):
            th=tr.find('th');td=tr.find('td')
            if len(th)==len(td)==1:fields[th[0].text]=td[0].text
    if not fields.get('神社名'):raise ValueError('Ehime detail structure changed')
    source_id=re.search(r'[?&]p=(\d+)',page.url)
    return [record(page,fields['神社名'],fields.get('ふりがな',''),fields.get('神社鎮座地',''),
        'table tr th=神社名/ふりがな/神社鎮座地',source_id=source_id.group(1) if source_id else page.url)]

def collect_ehime(client,limit=None):
    entry=client.fetch('https://ehime-jinjacho.jp/jinja/')
    # Both visible modal links and map balloon links point to the same public details.
    starts=list(dict.fromkeys(re.findall(r'https://ehime-jinjacho\.jp/jinja/\?p=\d+',entry.text)))
    if not starts:raise ValueError('Ehime facility links absent')
    return _collect(client,'ehime','38','愛媛県','愛媛県神社庁',starts,parse_ehime,r'(?!)',limit)

def parse_okinawa(page):
    out=[]
    for p in Tree(page.text).root.find('p'):
        if not p.attrs.get('id'):continue
        names=p.find('b')
        if len(names)!=1:continue
        name=names[0].text.splitlines()[0].strip()
        if not name.endswith(('宮','神社')):continue
        lines=[x.strip() for x in p.text.split('\n') if x.strip()]
        addresses=[x for x in lines[1:] if re.match(r'(?:沖縄県)?[^:：]+?[市郡町村]',x)]
        if len(addresses)!=1:raise ValueError('Okinawa address structure changed')
        links=[urljoin(page.url,a.attrs.get('href','')) for a in p.find('a') if a.attrs.get('href','').startswith(('http://','https://'))]
        out.append(record(page,name,'',addresses[0],'p#'+p.attrs['id'],
            source_id=p.attrs['id']+'|'+name,official_url=links[0] if links else None))
    if not out:raise ValueError('Okinawa shrine list structure not recognized')
    return out

def collect_okinawa(client,limit=None):
    return _collect(client,'okinawa','47','沖縄県','沖縄県神社庁',
        ['https://jinjacho.naminouegu.jp/'],parse_okinawa,r'(?!)',limit)

REGISTRY.update({
    'ehime':dict(code='38',prefecture='愛媛県',agency='愛媛県神社庁',collect=collect_ehime),
    'okinawa':dict(code='47',prefecture='沖縄県',agency='沖縄県神社庁',collect=collect_okinawa),
})

def parse_kagawa(page):
    out=[]
    for item in Tree(page.text).root.find('li','c-entries__item'):
        names=item.find('h2','c-entry-summary__title');addresses=item.find('div','location');links=item.find('a')
        if len(names)!=len(addresses) or len(names)!=1 or len(links)!=1:raise ValueError('Kagawa listing structure changed')
        href=urljoin(page.url,links[0].attrs['href'])
        out.append(record(page,names[0].text,'',addresses[0].text,
            'li.c-entries__item a[href="'+links[0].attrs['href']+'"]',source_id=href))
    if not out:raise ValueError('Kagawa listing structure not recognized')
    return out

def collect_kagawa(client,limit=None):
    return _collect(client,'kagawa','37','香川県','香川県神社庁',
        ['https://kagawakenjinjacho.or.jp/shrine/'],parse_kagawa,
        r'https://kagawakenjinjacho\.or\.jp/shrine/(?:page/\d+/)?',limit)

def parse_kumamoto(page):
    out=[]
    for table in Tree(page.text).root.find('table','c-table'):
        if '対象神社名' not in table.text:continue
        for tr in table.find('tr'):
            names=tr.find('th');cells=tr.find('td');links=[a for a in tr.find('a') if a.text=='詳細を見る']
            if not cells:continue
            if len(names)!=1 or len(cells)<4 or len(links)!=1:raise ValueError('Kumamoto listing structure changed')
            href=urljoin(page.url,links[0].attrs['href'])
            out.append(record(page,names[0].text,'',re.sub(r'\s+','',cells[0].text),
                'table.c-table tr a[href="'+links[0].attrs['href']+'"]',source_id=href))
    if not out:raise ValueError('Kumamoto listing structure not recognized')
    return out

def collect_kumamoto(client,limit=None):
    return _collect(client,'kumamoto','43','熊本県','熊本県神社庁',
        ['https://kumamotokenjinjacho.jp/patron-god/'],parse_kumamoto,
        r'https://kumamotokenjinjacho\.jp/patron-god/page/\d+/',limit)

REGISTRY.update({
    'kagawa':dict(code='37',prefecture='香川県',agency='香川県神社庁',collect=collect_kagawa),
    'kumamoto':dict(code='43',prefecture='熊本県',agency='熊本県神社庁',collect=collect_kumamoto),
})

def parse_saga(page):
    root=Tree(page.text).root
    titles=[n for n in root.find('h1') if n.attrs.get('id')=='pageTit']
    contents=root.find('div','entry-content')
    if len(titles)!=1 or len(contents)!=1:raise ValueError('Saga detail structure changed')
    address=''
    for p in contents[0].find('p'):
        if p.text.startswith('【鎮座地】'):address=p.text.removeprefix('【鎮座地】').strip()
    native=contents[0].attrs.get('id') or page.url
    return [record(page,titles[0].text,'',address,'h1#pageTit; div.entry-content p=【鎮座地】',source_id=native)]

def saga_links(page):
    links=[]
    for w in Tree(page.text).root.find('div','textwidget'):
        if '【' not in w.text:continue
        for a in w.find('a'):
            href=urljoin(page.url,a.attrs.get('href',''))
            if href.startswith('https://saga-jinjacho.jp/') and href not in links:links.append(href)
    if not links:raise ValueError('Saga regional shrine links absent')
    return links

def collect_saga(client,limit=None):
    entry=client.fetch('https://saga-jinjacho.jp/jinja-map/')
    return _collect(client,'saga','41','佐賀県','佐賀県神社庁',saga_links(entry),parse_saga,r'(?!)',limit)

def parse_nagasaki(page):
    root=Tree(page.text).root;out=[]
    # These two site-authored blocks hold the prefectural shrine link collection.
    for block in root.find('div'):
        if block.attrs.get('id') not in ('bk17860131','bk17860132'):continue
        for a in block.find('a'):
            href=a.attrs.get('href','')
            if not href.startswith(('https://','http://')) or not a.text:continue
            out.append(record(page,a.text,'','','div#'+block.attrs['id']+' a[href="'+href+'"]',
                source_id=href,official_url=href))
    if not out:raise ValueError('Nagasaki prefectural shrine link blocks not recognized')
    return out

def collect_nagasaki(client,limit=None):
    return _collect(client,'nagasaki','42','長崎県','長崎県神社庁',
        ['https://nagasaki-jinjacho.or.jp/link.html'],parse_nagasaki,r'(?!)',limit)

REGISTRY.update({
    'saga':dict(code='41',prefecture='佐賀県',agency='佐賀県神社庁',collect=collect_saga),
    'nagasaki':dict(code='42',prefecture='長崎県',agency='長崎県神社庁',collect=collect_nagasaki),
})

def parse_kochi(page):
    out=[]
    for item in Tree(page.text).root.find('div','wixui-repeater__item'):
        iid=item.attrs.get('id','')
        if not iid.startswith('comp-ljqf2796__'):continue
        fields={n.attrs.get('id','').split('__')[0]:n.text for n in item.find('div','wixui-rich-text')}
        required=['comp-ljqf2799','comp-ljqf279d','comp-ljqlom9b']
        if any(k not in fields for k in required):raise ValueError('Kochi rendered row structure changed')
        name,street,municipality=[fields[k] for k in required]
        out.append(record(page,name,'',municipality+street,'div#'+iid,source_id=iid.split('__',1)[1],
            address_raw=street,address_context=municipality))
    if not out:raise ValueError('Kochi rendered initial listing not recognized')
    return out

def collect_kochi(client,limit=None):
    from njd.records import build_dataset
    url='https://www.kochi-jinjyacho.com/%E9%AB%98%E7%9F%A5%E7%9C%8C%E7%A5%9E%E7%A4%BE%E4%B8%80%E8%A6%A7'
    p=client.fetch(url);rows=parse_kochi(p)
    return build_dataset('kochi','39','高知県','高知県神社庁',rows[:limit],
        pages=[dict(url=p.url,sha256=p.sha256,fetched_at=p.fetched_at)],metadata=dict(
            source_rows_observed=len(rows),traversal_complete=False,
            coverage='initial server-rendered rows only; next-list button is dynamic with no linked URL',
            remaining_scope='dynamic next-list navigation unresolved; do not interpret initial rows as complete'))

REGISTRY['kochi']=dict(code='39',prefecture='高知県',agency='高知県神社庁',collect=collect_kochi)
