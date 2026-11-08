"""Offline structural and evidence consistency checks; not URL authentication."""
from collections import Counter
from datetime import datetime
import re
from urllib.parse import urlsplit
from njd.normalize import normalize_reading

STATUSES={'verified','pending','excluded'}

def _url(v):
    try: return urlsplit(v).scheme in ('http','https') and bool(urlsplit(v).hostname)
    except (ValueError,TypeError): return False

def validate(data: dict) -> list[dict]:
    problems=[]
    def add(kind,rid,reason): problems.append(dict(kind=kind,id=rid,reason=reason))
    fs=data.get('facilities',[]); es=data.get('entries',[])
    for kind,records in [('facility',fs),('entry',es)]:
        counts=Counter(r.get('id') for r in records)
        for rid,n in counts.items():
            if not rid or n>1: add('global',rid,'missing or duplicate '+kind+' id')
        for r in records:
            rid=r.get('id')
            if r.get('status') not in STATUSES: add(kind,rid,'invalid status')
            if r.get('status')!='verified' and not r.get('reason'): add(kind,rid,'missing review/exclusion reason')
            for field in ['fetched_at','checked_at']:
                if r.get('status')!='verified' and field=='checked_at': continue
                try: datetime.fromisoformat(r[field])
                except (ValueError,TypeError,KeyError): add(kind,rid,'missing/invalid '+field)
            for field in ['source_hash','page_hash']:
                if not re.fullmatch('[0-9a-f]{64}',r.get(field,'')): add(kind,rid,'missing/invalid '+field)
            for field in ['listing_url']:
                if not _url(r.get(field)): add(kind,rid,'missing/invalid '+field)
    fmap={f.get('id'):f for f in fs}
    for f in fs:
        for field in ['listed_name','name_raw','prefecture','municipality','address','agency','source_locator']:
            if not f.get(field): add('facility',f.get('id'),'missing '+field)
        code=f.get('prefecture_code','')
        if code not in {f'{i:02}' for i in range(1,48)}: add('facility',f.get('id'),'invalid prefecture code')
        if f.get('listed_name')!=f.get('name_raw'): add('facility',f.get('id'),'name differs from source')
    seen=set()
    for e in es:
        eid=e.get('id'); f=fmap.get(e.get('facility_id'))
        if not f: add('entry',eid,'orphan facility reference'); continue
        for field in ['surface','name_raw']:
            if e.get(field)!=f.get('listed_name'): add('entry',eid,'surface must equal agency listed name')
        if e.get('listing_url')!=f.get('listing_url'): add('entry',eid,'listing URL differs from facility')
        if e.get('source_hash')!=f.get('source_hash') or e.get('page_hash')!=f.get('page_hash'):
            add('entry',eid,'source fingerprint differs from facility')
        if e.get('semantic_type')!='proper_noun': add('entry',eid,'unsupported semantic type')
        if e.get('status')=='verified':
            if not _url(e.get('reading_url')): add('entry',eid,'missing/invalid reading URL')
            if not e.get('evidence'): add('entry',eid,'missing evidence')
            if not e.get('reading_source_kind') in ('agency','shrine_official'): add('entry',eid,'invalid reading source kind')
            if e.get('reading_source_kind')=='agency' and e.get('reading_url')!=f.get('listing_url'):
                add('entry',eid,'agency reading URL differs from listing')
            try:
                if normalize_reading(e.get('reading',''))!=e.get('reading'): raise ValueError()
                if normalize_reading(e.get('reading_raw',''))!=e.get('reading'): raise ValueError()
            except ValueError: add('entry',eid,'invalid or ungrounded reading')
        key=(e.get('facility_id'),e.get('reading'),e.get('surface'))
        if key in seen: add('entry',eid,'duplicate facility entry')
        seen.add(key)
        for field in ['surface','reading']:
            if any(ord(c)<32 or ord(c)==127 for c in e.get(field,'')): add('entry',eid,'control character in '+field)
    return problems

def eligible(data: dict) -> list[dict]:
    problems=validate(data)
    if any(p['kind']=='global' for p in problems): return []
    bad_f={p['id'] for p in problems if p['kind']=='facility'}
    bad_e={p['id'] for p in problems if p['kind']=='entry'}
    fmap={f['id']:f for f in data['facilities']}
    return [e for e in data['entries'] if e['status']=='verified' and e['id'] not in bad_e
        and e['facility_id'] not in bad_f and fmap.get(e['facility_id'],{}).get('status')=='verified']
