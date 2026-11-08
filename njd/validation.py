"""Offline structural and evidence consistency checks; not URL authentication."""
from collections import Counter
import hashlib
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
    if not isinstance(data,dict): return [dict(kind='global',id=None,reason='dataset must be an object')]
    if data.get('schema_version')!=1 or not all(k in data for k in ['facilities','entries','collection']) or not isinstance(data.get('collection'),dict):
        return [dict(kind='global',id=None,reason='missing required dataset fields or unsupported schema version')]
    fs=data.get('facilities',[]); es=data.get('entries',[])
    for kind,records,fields in [
        ('facility',fs,['id','status','listed_name','name_raw','prefecture','prefecture_code','municipality','address','agency','source_locator','source_hash','page_hash','listing_url','fetched_at','checked_at','reason']),
        ('entry',es,['id','facility_id','status','surface','reading','name_raw','reading_raw','source_hash','page_hash','listing_url','reading_url','evidence','semantic_type','reading_source_kind','fetched_at','checked_at','reason'])]:
        if not isinstance(records,list) or any(not isinstance(r,dict) for r in records):
            return [dict(kind='global',id=None,reason='invalid '+kind+' collection')]
        for r in records:
            for field in fields:
                if field in r and not isinstance(r[field],str):
                    return [dict(kind='global',id=r.get('id'),reason='invalid field type: '+field)]
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
        row_material='\0'.join((f.get('name_raw',''),e.get('reading_raw',''),f.get('address','')))
        if hashlib.sha256(row_material.encode()).hexdigest()!=e.get('source_hash'):
            add('entry',eid,'acquired original differs from source-row fingerprint')
        if e.get('status')=='verified':
            if not _url(e.get('reading_url')): add('entry',eid,'missing/invalid reading URL')
            if not e.get('evidence'): add('entry',eid,'missing evidence')
            if not e.get('reading_source_kind') in ('agency','shrine_official'): add('entry',eid,'invalid reading source kind')
            if e.get('reading_source_kind')=='agency' and e.get('reading_url')!=f.get('listing_url'):
                add('entry',eid,'agency reading URL differs from listing')
            try:
                if normalize_reading(e.get('reading',''))!=e.get('reading'): raise ValueError()
                if e.get('reading_source_kind')=='agency':
                    raw=e.get('reading_raw','')
                else:
                    raw=e.get('supplemental_reading_raw','')
                    if e.get('reading_raw'): raise ValueError('agency reading already present')
                    official_host=urlsplit(f.get('official_site_url') or '').hostname
                    proof=e.get('supplemental_official_verification')
                    if proof is not None:
                        if not isinstance(proof,dict): raise ValueError('invalid official identity evidence')
                        if proof.get('status')!='verified' or not proof.get('evidence'): raise ValueError('official identity unverified')
                        if proof.get('name_raw')!=f.get('listed_name') or proof.get('address_raw')!=f.get('address'): raise ValueError('official identity mismatch')
                        if not _url(proof.get('url')) or not _url(proof.get('evidence_url')): raise ValueError('official identity URL missing')
                        datetime.fromisoformat(proof.get('checked_at',''))
                        official_host=urlsplit(proof['url']).hostname
                        if urlsplit(proof['evidence_url']).hostname!=official_host: raise ValueError('official evidence outside official host')
                    if not official_host or urlsplit(e.get('reading_url','')).hostname!=official_host: raise ValueError('official identity not established')
                    if e.get('supplemental_name')!=f.get('listed_name') or e.get('supplemental_address')!=f.get('address'): raise ValueError('name/address mismatch')
                if normalize_reading(raw)!=e.get('reading'): raise ValueError()
            except (ValueError,TypeError): add('entry',eid,'invalid or ungrounded reading')
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
