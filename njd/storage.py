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
        allowed={'expected_source_hash','status','reason','reading','reading_raw','reading_url','evidence','checked_at','reading_source_kind'}
        if set(decision)-allowed: raise ValueError('unsupported human decision fields')
        if not decision.get('reason'): raise ValueError('human decision requires reason')
        e.update({k:v for k,v in decision.items() if k!='expected_source_hash'})
    return result
