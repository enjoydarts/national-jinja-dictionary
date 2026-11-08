"""Canonical records from explicit adapter fields, never inferred readings."""
import hashlib
import re
from uuid import uuid5, NAMESPACE_URL
from njd.normalize import normalize_reading


def municipality_from_address(address, prefecture):
    value=address.removeprefix(prefecture).strip()
    county=re.match(r'(.+?郡[^市区]+?[町村])',value)
    city=re.match(r'(.+?市市|.+?市)([^市町村区0-9\s]+?区)?',value)
    if county: return county.group(0)
    if city: return city.group(0)
    ward=re.match(r'(.+?区)',value)
    if ward: return ward.group(0)
    town=re.match(r'(.+?[町村])',value)
    return town.group(0) if town else ''


def build_dataset(source_key, code, prefecture, agency, records, pages=None, metadata=None):
    facilities=[]; entries=[]; known={}
    for row in records:
        for required in ('name','address','url','fetched_at','page_hash','locator','evidence'):
            if not isinstance(row.get(required),str):
                raise ValueError('missing or invalid explicit source field: '+required)
        name=row['name']; raw=row.get('reading_raw',''); address=row['address']
        if not isinstance(raw,str): raise ValueError('reading_raw must be source text or empty')
        digest=hashlib.sha256('\0'.join((name,raw,address)).encode()).hexdigest()
        source_id=row.get('source_id')
        seed=f'{source_key}|native|{source_id}' if source_id is not None else f'{source_key}|{name}|{address}'
        fid=str(uuid5(NAMESPACE_URL,seed)); eid=str(uuid5(NAMESPACE_URL,f'{fid}|primary'))
        occurrence=dict(url=row['url'],locator=row['locator'],page_hash=row['page_hash'],fetched_at=row['fetched_at'])
        if fid in known:
            f,e=known[fid]
            if occurrence not in f['listing_occurrences']: f['listing_occurrences'].append(occurrence)
            if digest!=f['source_hash']:
                conflict=dict(name_raw=name,reading_raw=raw,address=address,**occurrence)
                f.setdefault('source_conflicts',[]).append(conflict)
                f['status']=e['status']='pending'
                f['reason']=e['reason']='conflicting source rows for the same source identity'
            continue
        municipality=row.get('municipality') or municipality_from_address(address,prefecture)
        fstatus='verified'; freason=''
        if not name or not address or not municipality:
            fstatus='pending'; freason='missing name, address or municipality'
        if any(ord(c)<32 or ord(c)==127 for c in name):
            fstatus='pending';freason='control or layout characters in source name; explicit review required'
        if '\n' in address or '\r' in address:
            fstatus='pending'; freason='multiple address lines; facility identity requires review'
        try:
            reading=normalize_reading(raw); status='verified'; reason=''
        except ValueError as exc:
            reading=''; status='pending'; reason='missing agency reading' if not raw else str(exc)
        if fstatus!='verified': status='pending';reason=freason
        f=dict(id=fid,agency=agency,prefecture_code=code,prefecture=prefecture,
            listed_name=name,name_raw=name,municipality=municipality,address=address,
            listing_url=row['url'],source_locator=row['locator'],source_hash=digest,
            page_hash=row['page_hash'],fetched_at=row['fetched_at'],checked_at=row['fetched_at'],
            status=fstatus,reason=freason,official_site_url=row.get('official_url'),
            source_key=source_key,native_source_id=source_id,listing_occurrences=[occurrence])
        for field in ('address_raw','address_context'):
            if field in row: f[field]=row[field]
        e=dict(id=eid,facility_id=fid,surface=name,reading=reading,semantic_type='proper_noun',
            name_raw=name,reading_raw=raw,listing_url=row['url'],reading_url=row['url'],
            evidence=row['evidence'],normalization=['NFKC reading only','katakana to hiragana'],
            source_hash=digest,page_hash=row['page_hash'],fetched_at=row['fetched_at'],
            checked_at=row['fetched_at'],status=status,reason=reason,reading_source_kind='agency')
        facilities.append(f); entries.append(e);known[fid]=(f,e)
    collection=dict(source_key=source_key,agency=agency,prefecture_code=code,
        source_rows_observed=len(records),selected_rows=len(facilities),
        pages=pages or [],coverage='observed official listings only; not all shrines in the prefecture',
        redistribution_status='unconfirmed')
    if metadata: collection.update(metadata)
    collection['source_key']=source_key;collection['prefecture_code']=code
    return dict(schema_version=1,facilities=facilities,entries=entries,collection=collection)
