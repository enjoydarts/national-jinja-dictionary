"""Offline structural and evidence consistency checks; not URL authentication."""
from collections import Counter
import hashlib
from datetime import datetime
import re
from urllib.parse import urlsplit
from njd.normalize import normalize_reading
from njd.corrections import correction_problems, discovery_only
from njd.reviews import reviewed_output

STATUSES={'verified','pending','excluded'}

def _url(v):
    try: return urlsplit(v).scheme in ('http','https') and bool(urlsplit(v).hostname)
    except (ValueError,TypeError): return False

def validate(data: dict) -> list[dict]:
    problems=[]
    def add(kind,rid,reason,severity='error'): problems.append(dict(kind=kind,id=rid,reason=reason,severity=severity))
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
                if discovery_only(r.get(field)):add(kind,rid,'discovery-only directory cannot serve as listing evidence')
    fmap={f.get('id'):f for f in fs}
    corrected_names=set()
    for e in es:
        f=fmap.get(e.get('facility_id'))
        if not f:continue
        source=data['collection'].get('sources',{}).get(f.get('source_key'),data['collection'])
        correction=e.get('correction')
        if isinstance(correction,dict) and correction.get('changes',{}).get('surface')==e.get('surface') and not correction_problems(correction,f,e,source):
            corrected_names.add(f['id'])
        if reviewed_output(e.get('human_review'),f,e,source):corrected_names.add(f['id'])
    for f in fs:
        source=data['collection'].get('sources',{}).get(f.get('source_key'),data['collection'])
        if source.get('authority_status') in ('pending','unconfirmed'):
            add('facility',f.get('id'),'official source authority not established',severity='review' if f.get('status')!='verified' else 'error')
        for field in ['listed_name','name_raw','prefecture','municipality','address','agency','source_locator']:
            if not f.get(field):
                if field in ('listed_name','name_raw') and f['id'] in corrected_names:continue
                add('facility',f.get('id'),'missing '+field,severity='review' if f.get('status')!='verified' and field in ('municipality','address','listed_name','name_raw') else 'error')
        if 'address_source' in f:
            evidence=f['address_source'];severity='review' if f.get('status')!='verified' else 'error'
            if not isinstance(evidence,dict):
                add('facility',f.get('id'),'invalid address source',severity=severity)
            else:
                try:
                    if not _url(evidence.get('url')) or not re.fullmatch('[0-9a-f]{64}',evidence.get('page_hash','')):raise ValueError()
                    datetime.fromisoformat(evidence.get('fetched_at',''))
                    applied=evidence.get('applied',evidence.get('address_raw')==f.get('address'))
                    if applied and (evidence.get('name_raw')!=f.get('name_raw') or evidence.get('address_raw')!=f.get('address')):raise ValueError()
                    if urlsplit(evidence['url']).hostname!=urlsplit(f['listing_url']).hostname:raise ValueError()
                    native=f.get('native_source_id')
                    if _url(native) and (evidence.get('link_url') or evidence['url'])!=native:raise ValueError()
                except (ValueError,TypeError):add('facility',f.get('id'),'address detail does not match the listed facility/source',severity=severity)
        code=f.get('prefecture_code','')
        if code not in {f'{i:02}' for i in range(1,48)}: add('facility',f.get('id'),'invalid prefecture code')
        if f.get('listed_name')!=f.get('name_raw'): add('facility',f.get('id'),'name differs from source')
    seen=set()
    for e in es:
        eid=e.get('id'); f=fmap.get(e.get('facility_id'))
        if discovery_only(e.get('reading_url')):add('entry',eid,'discovery-only directory cannot serve as reading evidence')
        if not f: add('entry',eid,'orphan facility reference'); continue
        source=data['collection'].get('sources',{}).get(f.get('source_key'),data['collection'])
        correction=e.get('correction')
        correction_valid=isinstance(correction,dict) and not correction_problems(correction,f,e,source)
        review_valid=reviewed_output(e.get('human_review'),f,e,source)
        if e.get('name_raw')!=f.get('listed_name'):add('entry',eid,'name raw must equal acquired agency name')
        if e.get('surface')!=f.get('listed_name') and not review_valid and not (correction_valid and correction.get('changes',{}).get('surface')==e.get('surface')):
            add('entry',eid,'surface differs without verified correction evidence')
        if f.get('name_rendering_status') in ('external_glyph','unrenderable') and e.get('status')=='verified' and not (correction_valid or review_valid):
            add('entry',eid,'external glyph has no verified Unicode correction')
        if e.get('listing_url')!=f.get('listing_url'): add('entry',eid,'listing URL differs from facility')
        if e.get('source_hash')!=f.get('source_hash') or e.get('page_hash')!=f.get('page_hash'):
            add('entry',eid,'source fingerprint differs from facility')
        if e.get('semantic_type')!='proper_noun': add('entry',eid,'unsupported semantic type')
        row_material='\0'.join((f.get('name_raw',''),e.get('reading_raw',''),f.get('address','')))
        if hashlib.sha256(row_material.encode()).hexdigest()!=e.get('source_hash'):
            add('entry',eid,'acquired original differs from source-row fingerprint')
        if e.get('status')=='verified':
            human_only=review_valid and any(o.get('basis')=='user_confirmation' and o.get('reading')==e.get('reading') and o.get('surface')==e.get('surface') for o in e['human_review']['outputs'])
            if not _url(e.get('reading_url')) and not human_only: add('entry',eid,'missing/invalid reading URL')
            if not e.get('evidence'): add('entry',eid,'missing evidence')
            if not e.get('reading_source_kind') in ('agency','shrine_official','reference','user_review'): add('entry',eid,'invalid reading source kind')
            if e.get('reading_source_kind')=='agency' and e.get('reading_url')!=f.get('listing_url'):
                add('entry',eid,'agency reading URL differs from listing')
            try:
                if normalize_reading(e.get('reading',''))!=e.get('reading'): raise ValueError()
                if e.get('reading_source_kind')=='user_review':
                    if not review_valid:raise ValueError('human review no longer matches')
                    raw=e['reading']
                elif e.get('reading_source_kind')=='agency':
                    raw=e.get('reading_raw','')
                elif e.get('reading_source_kind')=='reference':
                    if not correction_valid or correction.get('changes',{}).get('reading')!=e.get('reading'):raise ValueError('reference correction not verified')
                    matches=[]
                    for ref in correction['references']:
                        try:
                            if ref['url']==e['reading_url'] and normalize_reading(ref.get('reading_raw',''))==e['reading'] and ref.get('reading_raw','') in ref.get('excerpt',''):matches.append(ref['reading_raw'])
                        except (TypeError,ValueError):pass
                    if not matches:raise ValueError('reference reading source mismatch')
                    raw=matches[0]
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
            if any(ord(c)<32 or ord(c)==127 for c in e.get(field,'')): add('entry',eid,'control character in '+field,severity='review' if e.get('status')!='verified' else 'error')
    return problems

def eligible(data: dict) -> list[dict]:
    problems=validate(data)
    if any(p['kind']=='global' for p in problems): return []
    bad_f={p['id'] for p in problems if p['kind']=='facility'}
    bad_e={p['id'] for p in problems if p['kind']=='entry'}
    fmap={f['id']:f for f in data['facilities']}
    return [e for e in data['entries'] if e['status']=='verified' and e['id'] not in bad_e
        and e['facility_id'] not in bad_f and fmap.get(e['facility_id'],{}).get('status')=='verified']


def blocking_problems(data):
    return [p for p in validate(data) if p.get('severity','error')=='error']
