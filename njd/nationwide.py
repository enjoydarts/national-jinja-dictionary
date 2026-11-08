"""Versioned per-source canonical data, checkpointed acquisition and offline merge."""
import re
from pathlib import Path
from njd.http import Client
from njd.report import PREFECTURES
from njd.storage import load_dataset, write_json, reconcile_identity
from njd.validation import validate, eligible, blocking_problems

SOURCE_KEYS='hokkaido aomori iwate miyagi akita yamagata fukushima ibaraki tochigi gunma saitama chiba tokyo kanagawa niigata toyama ishikawa fukui yamanashi nagano gifu shizuoka aichi mie shiga kyoto osaka hyogo nara wakayama tottori shimane okayama hiroshima yamaguchi tokushima kagawa ehime kochi fukuoka saga nagasaki kumamoto oita miyazaki kagoshima okinawa'.split()


def source_path(data_dir,key):
    if not re.fullmatch(r'[a-z][a-z0-9_]*',key): raise ValueError('invalid source key')
    return Path(data_dir)/'sources'/(key+'.json')


def default_states():
    return {f'{i:02}':dict(prefecture_code=f'{i:02}',prefecture=pref,source_key=SOURCE_KEYS[i-1],
        status='not_collected',reason='no saved source collection') for i,pref in enumerate(PREFECTURES,1)}


def load_states(data_dir):
    states=default_states(); path=Path(data_dir)/'manifest.json'
    if path.exists(): states.update(load_dataset(path).get('prefectures',{}))
    return states


def save_collection(data_dir,key,data):
    """Save authoritative source facts; caches and work history live elsewhere."""
    if data.get('collection',{}).get('source_key')!=key: raise ValueError('source key differs from dataset')
    issues=blocking_problems(data)
    if issues: raise ValueError('source dataset validation failed: '+str(issues[:5]))
    path=source_path(data_dir,key)
    old=load_dataset(path) if path.exists() else None
    links_path=Path(data_dir)/'identities.json'
    all_links=load_dataset(links_path) if links_path.exists() else {}
    links=all_links.get(key,{})
    result=reconcile_identity(old,data,links)
    if blocking_problems(result): raise ValueError('identity reconciliation produced invalid records')
    write_json(path,result)
    return result


def merge_collections(data_dir,*,states=None):
    """Merge repository canonical source files entirely offline, in memory."""
    data_dir=Path(data_dir); facilities=[]; entries=[]; sources={}
    for path in sorted((data_dir/'sources').glob('*.json')):
        data=load_dataset(path); key=path.stem
        if data.get('collection',{}).get('source_key')!=key: raise ValueError('source file/key mismatch: '+key)
        issues=blocking_problems(data)
        if issues: raise ValueError('invalid canonical source '+key+': '+str(issues[:3]))
        facilities.extend(data['facilities']);entries.extend(data['entries'])
        sources[key]=data['collection']
    if not sources:
        legacy=data_dir/'common.json'
        if legacy.exists(): return load_dataset(legacy)
        raise ValueError('no canonical source files; acquire or import data first')
    states=states or load_states(data_dir)
    for key,source in sources.items():
        code=source['prefecture_code']
        if states[code]['status']=='not_collected':
            states[code]=dict(states[code],status='collected',reason='saved official listing records; coverage stated per source',source_key=key)
    facilities.sort(key=lambda f:(f['prefecture_code'],f['id']))
    entries.sort(key=lambda e:(e['facility_id'],e['id']))
    result=dict(schema_version=1,facilities=facilities,entries=entries,collection=dict(
        source_key='national',sources=sources,prefecture_states=states,
        source_rows_observed=sum(s.get('source_rows_observed',0) for s in sources.values()),
        selected_rows=len(facilities),
        coverage='observed official listings only; see each prefecture state and source coverage',
        redistribution_status='see source-specific conditions'))
    issues=blocking_problems(result)
    if issues: raise ValueError('merged canonical validation failed: '+str(issues[:5]))
    return result


def run_collections(data_dir,registry,keys,*,offline=False,refresh=False,limit=None,cache_dir=None):
    data_dir=Path(data_dir);states=load_states(data_dir)
    if cache_dir is None: cache_dir=data_dir.parent/'acquisition-cache'
    for key in keys:
        spec=registry[key];code=spec['code'];path=source_path(data_dir,key)
        client=Client(Path(cache_dir),offline=offline)
        if refresh:
            # Refresh requests are explicitly propagated without changing the
            # adapter contract or performing surprise online work at release.
            original=client.fetch
            client.fetch=lambda url,**kwargs: original(url,refresh=True,**{k:v for k,v in kwargs.items() if k!='refresh'})
        try:
            data=spec['collect'](client,limit=limit)
            saved=save_collection(data_dir,key,data)
            states[code]=dict(states[code],source_key=key,status='collected',reason='saved explicit source fields',
                facilities=len(saved['facilities']),verified_facilities=len({e['facility_id'] for e in eligible(saved)}))
        except Exception as exc:
            # One source failure never erases its previous canonical data or
            # prevents independently available prefectures from continuing.
            states[code]=dict(states[code],source_key=key,status='failed_using_previous' if path.exists() else 'failed',
                reason=f'{type(exc).__name__}: {exc}')
        write_json(data_dir/'manifest.json',dict(schema_version=1,prefectures=states))
    return states
