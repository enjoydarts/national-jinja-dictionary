"""Evidence-bound aliases for duplicated Kochi publication rows.

Original source records and human overlays are retained. A resolution only marks
one publication row as another observation of an existing facility; it never
normalizes names, guesses readings or deletes source data.
"""
import copy
from datetime import datetime
import re
from pathlib import Path
from urllib.parse import parse_qs,unquote,urlsplit

FIELDS=('id','source_key','prefecture_code','prefecture','name_raw','address','address_raw','address_context','native_source_id','source_hash')
KIND='kochi_explicit_duplicate_listing'


def _snapshot(f):return {k:f.get(k) for k in FIELDS}


def _listing(f):
    try:
        p=urlsplit(f.get('listing_url',''));q=parse_qs(p.query,keep_blank_values=True)
        return (p.scheme=='https' and p.netloc=='www.kochi-jinjyacho.com' and unquote(p.path)=='/高知県神社一覧'
            and not p.fragment and (not q or set(q)=={'comp-ljqfjyd6_page'} and len(q['comp-ljqfjyd6_page'])==1 and bool(re.fullmatch('[1-9][0-9]*',q['comp-ljqfjyd6_page'][0]))))
    except (TypeError,ValueError):return False


def _pair_problems(primary,duplicate):
    if not isinstance(primary,dict) or not isinstance(duplicate,dict):return ['alias pair member missing']
    problems=[]
    if (primary.get('id')==duplicate.get('id') or any(f.get('source_key')!='kochi' or f.get('prefecture_code')!='39' or f.get('prefecture')!='高知県' or not _listing(f) for f in [primary,duplicate])):
        problems.append('alias pair is not two distinct Kochi official listing records')
    if not primary.get('name_raw') or primary.get('name_raw')!=duplicate.get('name_raw'):problems.append('alias names differ')
    addresses=[f.get('address') for f in [primary,duplicate]]
    if any(not isinstance(v,str) or not re.search('[0-9０-９]',v) for v in addresses):problems.append('full numeric addresses required')
    elif addresses[0].removeprefix('高知県')!=addresses[1].removeprefix('高知県'):problems.append('alias full addresses differ beyond prefecture prefix')
    structured=[f for f in [primary,duplicate] if isinstance(f.get('address_context'),str) and f['address_context'].startswith('高知県')]
    full=[f for f in [primary,duplicate] if f.get('address_context')=='']
    if (len(structured)!=1 or len(full)!=1 or structured[0].get('address')!=structured[0]['address_context']+str(structured[0].get('address_raw','')) or full[0].get('address_raw')!=full[0].get('address')):
        problems.append('two complementary original publication layouts required')
    native=[f.get('native_source_id') for f in [primary,duplicate]]
    if any(not isinstance(v,str) or not re.fullmatch('[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}',v) for v in native) or native[0]==native[1]:problems.append('distinct stable CMS observation IDs required')
    return problems


def make_resolution(primary,duplicate,*,checked_at,reason):
    record=dict(kind=KIND,primary_id=primary['id'],duplicate_id=duplicate['id'],
        snapshots=dict(primary=_snapshot(primary),duplicate=_snapshot(duplicate)),checked_at=checked_at,reason=reason,
        evidence=[dict(url=f['listing_url'],locator=f['source_locator'],page_hash=f['page_hash'],fetched_at=f['fetched_at'],native_source_id=f['native_source_id']) for f in [primary,duplicate]])
    problems=resolution_problems(record,primary,duplicate)
    if problems:raise ValueError('; '.join(problems))
    return record


def resolution_problems(record,primary,duplicate):
    if not isinstance(record,dict):return ['missing source alias resolution']
    problems=_pair_problems(primary,duplicate)
    if problems:return problems
    if record.get('kind')!=KIND or record.get('primary_id')!=primary.get('id') or record.get('duplicate_id')!=duplicate.get('id'):problems.append('source alias resolution identity differs')
    if record.get('snapshots')!=dict(primary=_snapshot(primary),duplicate=_snapshot(duplicate)):problems.append('source alias snapshot is stale')
    try:
        if datetime.fromisoformat(record.get('checked_at','')).tzinfo is None:raise ValueError()
    except (TypeError,ValueError):problems.append('source alias review date absent')
    if not isinstance(record.get('reason'),str) or not record['reason']:problems.append('source alias review reason absent')
    evidence=record.get('evidence')
    if not isinstance(evidence,list) or len(evidence)!=2 or any(not isinstance(v,dict) for v in evidence):return problems+['two original source witnesses required']
    for ref,f in zip(evidence,[primary,duplicate]):
        expected=dict(url=f.get('listing_url'),locator=f.get('source_locator'),page_hash=f.get('page_hash'),fetched_at=f.get('fetched_at'),native_source_id=f.get('native_source_id'))
        if ref!=expected:problems.append('source alias witness is stale or differs from the inspected observation')
        if (ref.get('native_source_id')!=f.get('native_source_id') or not isinstance(ref.get('locator'),str)
            or f['native_source_id'] not in ref['locator'] or not _listing(dict(listing_url=ref.get('url')))
            or not isinstance(ref.get('page_hash'),str) or not re.fullmatch('[0-9a-f]{64}',ref['page_hash'])):problems.append('source alias source witness differs')
        try:datetime.fromisoformat(ref.get('fetched_at',''))
        except (TypeError,ValueError):problems.append('source alias acquisition date absent')
    return problems


def _document(document):
    if not isinstance(document,dict) or document.get('schema_version')!=1 or not isinstance(document.get('resolutions'),dict):raise ValueError('invalid source alias document')
    records=document['resolutions'];primaries=set()
    for duplicate_id,record in records.items():
        if not isinstance(record,dict) or record.get('duplicate_id')!=duplicate_id or not isinstance(record.get('primary_id'),str) or record['primary_id']==duplicate_id:raise ValueError('invalid source alias group identity')
        primaries.add(record['primary_id'])
    if primaries&set(records) or len(primaries)!=len(records):raise ValueError('chained, cyclic or overlapping source alias groups are not supported')
    return records


def apply_source_aliases(data,document,*,protected_pending_entry_ids=()):
    from njd.nationwide import ensure_public_metadata
    ensure_public_metadata(document)
    records=_document(document);result=copy.deepcopy(data);protected=set(protected_pending_entry_ids)
    facilities={f['id']:f for f in result['facilities']};entries={}
    for e in result['entries']:entries.setdefault(e['facility_id'],[]).append(e)
    reviews=[];resolved=0
    def hold(members,reason):
        for f in members:
            if not f:continue
            f['source_alias_review_reason']=reason
            if f.get('status') not in ('pending','excluded'):f.update(status='pending',reason=reason)
            for e in entries.get(f['id'],[]):
                e['source_alias_review_reason']=reason
                if e.get('status') not in ('pending','excluded'):e.update(status='pending',reason=reason)
        reviews.append(dict(facility_ids=[f['id'] for f in members if f],reason=reason))
    for duplicate_id,record in records.items():
        primary=facilities.get(record['primary_id']);duplicate=facilities.get(duplicate_id)
        if duplicate is None:continue # Removed publisher observation does not invalidate the remaining facility.
        problems=resolution_problems(record,primary,duplicate)
        if problems:hold([primary,duplicate],'source alias identity requires review: '+'; '.join(problems));continue
        pe=entries.get(primary['id'],[]);de=entries.get(duplicate_id,[])
        if len(pe)!=1 or len(de)!=1:hold([primary,duplicate],'source alias multiple-entry identity requires review');continue
        p,e=pe[0],de[0]
        def pending_review(entry):
            return (entry.get('status')=='pending' and (entry['id'] in protected or entry.get('reading') or entry.get('reading_raw')
                or entry.get('reason')!='missing agency reading' or entry.get('correction') or entry.get('human_review') or entry.get('identity_review_required')))
        if pending_review(p) or pending_review(e) or primary.get('status')=='pending' or duplicate.get('status')=='pending':
            hold([primary,duplicate],'source alias existing pending review; original judgment and reason retained');continue
        alias_active=e.get('status')=='verified' and duplicate.get('status')=='verified'
        primary_active=p.get('status')=='verified' and primary.get('status')=='verified'
        if alias_active and (not primary_active or any(e.get(k)!=p.get(k) for k in ('surface','reading','semantic_type'))):
            hold([primary,duplicate],'source alias output conflict; existing readings and judgments retained');continue
        primary['source_alias_ids']=sorted(set(primary.get('source_alias_ids',[]))|{duplicate_id})
        duplicate.update(source_alias_of=primary['id'],source_alias_resolution=copy.deepcopy(record))
        if duplicate.get('status')!='excluded':duplicate.update(status='excluded',reason='duplicate publication observation of facility '+primary['id'])
        e['source_alias_entry_of']=p['id']
        if e.get('status')!='excluded':e.update(status='excluded',reason='duplicate publication observation; original source and judgments retained')
        resolved+=1
    result['collection']['source_alias_summary']=dict(resolved_records=resolved,review_groups=reviews,
        counting_notice='Source aliases are retained management observations, not additional physical facilities or IME rows.')
    return result


def metadata_problems(data):
    # Missing mandatory identifiers are reported by the central structural
    # validator; do not index those records while checking optional metadata.
    if any(not isinstance(f.get('id'),str) for f in data['facilities']) or any(not isinstance(e.get('id'),str) or not isinstance(e.get('facility_id'),str) for e in data['entries']):return []
    facilities={f['id']:f for f in data['facilities']};entries={}
    for e in data['entries']:entries.setdefault(e['facility_id'],[]).append(e)
    problems=[]
    for f in data['facilities']:
        if 'source_alias_of' in f or 'source_alias_resolution' in f:
            target=f.get('source_alias_of');primary=facilities.get(target) if isinstance(target,str) else None
            reasons=resolution_problems(f.get('source_alias_resolution'),primary,f)
            if f.get('status')!='excluded':reasons.append('source alias must be excluded as a duplicate observation')
            if not primary or not isinstance(primary.get('source_alias_ids'),list) or f['id'] not in primary['source_alias_ids']:reasons.append('primary source alias relation missing')
            pe=entries.get(primary['id'],[]) if primary else [];de=entries.get(f['id'],[])
            if len(pe)!=1 or len(de)!=1 or de[0].get('status')!='excluded' or de[0].get('source_alias_entry_of')!=pe[0]['id']:reasons.append('duplicate entry source alias differs')
            for reason in reasons:problems.append(dict(kind='global',id=f['id'],reason=reason,severity='error'))
        ids=f.get('source_alias_ids',[])
        if not isinstance(ids,list) or any(not isinstance(v,str) for v in ids):problems.append(dict(kind='global',id=f['id'],reason='invalid primary source aliases',severity='error'));continue
        for alias in ids:
            if alias not in facilities or facilities[alias].get('source_alias_of')!=f['id']:problems.append(dict(kind='global',id=f['id'],reason='dangling primary source alias',severity='error'))
    for e in data['entries']:
        if 'source_alias_entry_of' in e and not facilities.get(e.get('facility_id'),{}).get('source_alias_of'):
            problems.append(dict(kind='global',id=e['id'],reason='orphan source alias entry marker',severity='error'))
    return problems


def apply_saved_source_aliases(data,data_dir):
    from njd.storage import load_dataset
    root=Path(data_dir);path=root/'source_aliases.json'
    if not path.exists():return data
    decisions_path=root/'decisions.json';protected=set()
    if decisions_path.exists():
        decisions=load_dataset(decisions_path)
        for e in data['entries']:
            decision=decisions.get(e.get('id'),{})
            if isinstance(decision,dict) and decision.get('status')=='pending' and decision.get('expected_source_hash')==e.get('source_hash'):protected.add(e['id'])
    return apply_source_aliases(data,load_dataset(path),protected_pending_entry_ids=protected)
