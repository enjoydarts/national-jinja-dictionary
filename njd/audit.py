"""Independent source-row comparison, separate from the table extraction parser."""
from html import unescape
import hashlib
import re
from njd.adapters.gunma import URL
from njd.normalize import normalize_reading

def audit_gunma(data,html,page_hash):
    triples=set()
    for row in re.findall(r'<tr\b[^>]*>(.*?)</tr\s*>',html,re.I|re.S):
        cells=re.findall(r'<(th|td)\b[^>]*>(.*?)</\1\s*>',row,re.I|re.S)
        if len(cells)<3 or [t.lower() for t,_ in cells[:3]]!=['th','td','td']: continue
        values=tuple(unescape(re.sub(r'<[^>]+>','',re.sub(r'<br\s*/?>','\n',content,flags=re.I))).strip() for _,content in cells[:3])
        triples.add(values)
    facilities={f['id']:f for f in data['facilities']}
    mismatches=[]
    for e in data['entries']:
        f=facilities[e['facility_id']]
        values=(f['name_raw'],e['reading_raw'],f['address'])
        digest=hashlib.sha256('\0'.join(values).encode()).hexdigest()
        reasons=[]
        if values not in triples: reasons.append('name, raw kana and address do not match a single source row')
        if f['listed_name']!=values[0] or e['surface']!=values[0]: reasons.append('surface changed from source')
        if e['source_hash']!=digest or f['source_hash']!=digest: reasons.append('source-row fingerprint mismatch')
        if e['page_hash']!=page_hash or f['page_hash']!=page_hash: reasons.append('source-page fingerprint mismatch')
        if e['listing_url']!=URL or f['listing_url']!=URL: reasons.append('listing URL differs from adapter source')
        if e['status']=='verified' and e['reading_source_kind']=='agency':
            try:
                if normalize_reading(values[1])!=e['reading']: reasons.append('reading not mechanical normalization of source')
            except ValueError: reasons.append('source kana cannot be mechanically normalized')
        if reasons: mismatches.append(dict(entry_id=e['id'],reasons=reasons))
    return dict(checked_entries=len(data['entries']),source_triples_observed=len(triples),
        page_hash=page_hash,mismatches=mismatches,
        method='independent tr/cell pattern extraction compared against exact raw triples',
        limitation='source consistency audit; not a pronunciation judgment or an actual IME import')
