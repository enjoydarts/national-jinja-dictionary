"""Official Gunma shrine table: th=name, first two td=kana/address.

The contact and homepage columns use rowspan. Do not inherit them as shrine
identity or reading evidence. Structure changes fail closed.
"""
import hashlib
from html.parser import HTMLParser
import re
from uuid import uuid5, NAMESPACE_URL
from njd.normalize import normalize_reading

URL = 'https://www.gunma-jinjacho.jp/jinja/'
AGENCY = '群馬県神社庁'

class TableParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows=[]; self.cells=[]; self.cell=None; self.section=''; self.in_row=False
    def handle_starttag(self, tag, attrs):
        attrs=dict(attrs)
        if tag=='section': self.section=attrs.get('id','')
        if tag=='tr': self.cells=[]; self.in_row=True
        if tag in ('th','td') and self.in_row: self.cell={'tag':tag,'text':'','links':[]}
        if tag=='br' and self.cell is not None: self.cell['text']+='\n'
        if tag=='a' and self.cell is not None: self.cell['links'].append(attrs.get('href',''))
    def handle_data(self,data):
        if self.cell is not None: self.cell['text']+=data
    def handle_endtag(self,tag):
        if tag in ('th','td') and self.cell is not None:
            self.cell['text']=self.cell['text'].strip()
            self.cells.append(self.cell); self.cell=None
        if tag=='tr' and self.in_row:
            self.rows.append((self.section,self.cells)); self.in_row=False

def parse(html: str, fetched_at: str, source_hash: str, limit: int | None=None) -> dict:
    p=TableParser(); p.feed(html)
    facilities=[]; entries=[]; headers=False; total=0
    for row_number,(section,cells) in enumerate(p.rows,1):
        if [c['text'] for c in cells[:3]]==['神社名','カナ','所在地']:
            headers=True; continue
        if not headers or len(cells)<3 or cells[0]['tag']!='th': continue
        if cells[1]['tag']!='td' or cells[2]['tag']!='td': continue
        name,raw,address=[c['text'] for c in cells[:3]]
        total+=1
        if limit is not None and len(facilities)>=limit: continue
        # Deterministic identity seed. A moved/renamed shrine is a diff requiring
        # human identity reconciliation, never an automatic same-name merge.
        identity=f'gunma|{name}|{address}'
        fid=str(uuid5(NAMESPACE_URL,identity)); eid=str(uuid5(NAMESPACE_URL,f'{fid}|primary'))
        try:
            reading=normalize_reading(raw); status='verified'; reason=''
        except ValueError as exc:
            reading=''; status='pending'; reason=str(exc)
        city_match=re.match(r'(.+?郡.+?[町村]|.+?[市町村])',address)
        municipality=city_match.group(1) if city_match else ''
        if not name or not address or not municipality:
            status='pending'; reason='missing name, address or municipality'
        locator=f'section#{section} table tr (document row {row_number})'
        # Row digest lets unrelated changes elsewhere on the page leave a human
        # decision applicable; whole-page digest is also retained for auditing.
        row_hash=hashlib.sha256(('\0'.join((name,raw,address))).encode()).hexdigest()
        facility=dict(id=fid,agency=AGENCY,prefecture_code='10',prefecture='群馬県',
            listed_name=name,name_raw=name,municipality=municipality,address=address,
            listing_url=URL,source_locator=locator,source_hash=row_hash,page_hash=source_hash,
            fetched_at=fetched_at,checked_at=fetched_at,status=status,reason=reason,
            official_site_url=(cells[0]['links'] or [None])[0])
        entry=dict(id=eid,facility_id=fid,surface=name,reading=reading,
            semantic_type='proper_noun',name_raw=name,reading_raw=raw,
            listing_url=URL,reading_url=URL,
            evidence=f'{locator}: same row th=名称; td[1]=掲載カナ; td[2]=所在地',
            normalization=['NFKC reading only','katakana to hiragana'],
            source_hash=row_hash,page_hash=source_hash,fetched_at=fetched_at,
            checked_at=fetched_at,status=status,reason=reason,
            reading_source_kind='agency')
        facilities.append(facility); entries.append(entry)
    if not headers or not facilities:
        raise ValueError('Gunma table structure not recognized; no records accepted')
    return dict(schema_version=1,facilities=facilities,entries=entries,
        collection=dict(agency=AGENCY,prefecture_code='10',listing_url=URL,
            source_rows_observed=total,selected_rows=len(facilities),limit=limit,
            coverage='selected rows only; not a claim of prefectural completeness',
            redistribution_status='unconfirmed',page_hash=source_hash,fetched_at=fetched_at))
