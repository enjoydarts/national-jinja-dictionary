"""Canonical JSON, immutable snapshots and separately maintained human decisions."""
import copy
import hashlib
import json
from pathlib import Path

def json_bytes(value):
    return (json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode('utf-8')

def write_json(path: Path, value):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+'.tmp'); tmp.write_bytes(json_bytes(value)); tmp.replace(path)

def load_dataset(path): return json.loads(Path(path).read_text(encoding='utf-8'))

def save_dataset(path, data):
    path=Path(path); old=load_dataset(path) if path.exists() else None
    delta={}
    for collection in ['facilities','entries']:
        before={r['id']:r for r in old[collection]} if old else {}
        after={r['id']:r for r in data[collection]}
        delta['added_'+collection]=sorted(after.keys()-before.keys())
        delta['removed_'+collection]=sorted(before.keys()-after.keys())
        delta['changed_'+collection]=sorted(k for k in before.keys() & after.keys() if before[k]!=after[k])
    if old is not None:
        digest=hashlib.sha256(json_bytes(old)).hexdigest()
        write_json(path.parent/'snapshots'/f'{digest}.json',old)
    write_json(path,data); write_json(path.parent/'changes.json',delta)
    return delta

def apply_decisions(data, decisions):
    result=copy.deepcopy(data)
    for e in result['entries']:
        decision=decisions.get(e['id'])
        if not decision: continue
        if decision.get('expected_source_hash')!=e.get('source_hash'):
            e['status']='pending'; e['reason']='human decision is stale; source row changed'; continue
        allowed={'expected_source_hash','status','reason','reading','supplemental_reading_raw','supplemental_name','supplemental_address','supplemental_official_verification','reading_url','evidence','checked_at','reading_source_kind'}
        if set(decision)-allowed: raise ValueError('unsupported human decision fields')
        if not decision.get('reason'): raise ValueError('human decision requires reason')
        e.update({k:v for k,v in decision.items() if k!='expected_source_hash'})
    return result


def reconcile_identity(old, new, links):
    """Conservative identity transitions; never merge facilities by name.

    Without a native source ID, renamed/moved source rows require a human
    link. Concurrent removal/addition quarantines additions. Quarantine is
    durable across refetches until a separate human decision resolves it.
    """
    from uuid import uuid5, NAMESPACE_URL
    result=copy.deepcopy(new)
    old_facilities={f['id']:f for f in old['facilities']} if old else {}
    old_entries={e['facility_id']:e for e in old['entries']} if old else {}
    history=copy.deepcopy(old.get('collection',{}).get('identity_history',{})) if old else {}
    history.update({fid:{k:f[k] for k in ['listed_name','address','source_hash','listing_url']} for fid,f in old_facilities.items()})
    linked_targets=set()
    entries={e['facility_id']:e for e in result['entries']}
    for f in result['facilities']:
        original_id=f['id']; link=links.get(original_id)
        if not link: continue
        target=link.get('facility_id')
        if not link.get('reason') or link.get('expected_source_hash')!=f['source_hash']:
            raise ValueError('identity link requires a reason and matching source-row fingerprint')
        if target not in history: raise ValueError('identity link target absent from persistent identity history')
        linked_targets.add(target)
        f['id']=target
        e=entries[original_id]; e['facility_id']=target
        e['id']=str(uuid5(NAMESPACE_URL,f'{target}|primary'))
        f['identity_link_reason']=link['reason']
    ids=[f['id'] for f in result['facilities']]
    if len(ids)!=len(set(ids)): raise ValueError('identity mapping would merge source facilities')
    removed=set(history)-set(ids)
    for f,e in zip(result['facilities'],result['entries']):
        previous=old_entries.get(f['id'])
        if f['id'] not in linked_targets and ((removed and f['id'] not in old_facilities) or (previous and previous.get('identity_review_required'))):
            e['identity_review_required']=True
            e['status']='pending'; e['reason']='source identity changed; human reconciliation required'
            e['identity_candidates']=sorted(removed) if removed else previous.get('identity_candidates',[])
    history.update({f['id']:{k:f[k] for k in ['listed_name','address','source_hash','listing_url']} for f in result['facilities']})
    result['collection']['identity_history']=history
    return result
