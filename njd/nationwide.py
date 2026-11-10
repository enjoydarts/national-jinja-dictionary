"""Versioned per-source canonical data, checkpointed acquisition and offline merge."""
import re
import copy
from pathlib import Path
from njd.http import Client
from njd.report import PREFECTURES
from njd.storage import load_dataset, write_json, reconcile_identity
from njd.validation import validate, eligible, blocking_problems


class PartialSnapshotError(ValueError):
    def __init__(self,omitted_count):
        self.omitted_count=omitted_count
        super().__init__(f'partial acquisition omits {omitted_count} saved facility records; previous canonical snapshot preserved')


class CuratedSourceReviewError(ValueError):
    def __init__(self,count,kind):
        self.count=count;self.kind=kind
        super().__init__(f'{count} individually curated source records {kind}; previous canonical snapshot preserved')


def _curated_material(facility):
    return {k:copy.deepcopy(facility.get(k)) for k in ('listed_name','address','source_hash','page_hash','listing_url','source_locator','source_reference','additional_source_references')}


def _preserve_curated_sources(old,result,reviewed):
    if type(reviewed) is not bool:raise ValueError('reviewed_curated must be an explicit boolean')
    if not old:return
    before={f['id']:f for f in old['facilities'] if f.get('curated_source_record') is True or isinstance(f.get('source_reference'),dict) and f['source_reference'].get('acquisition_method')=='individual_source_review'}
    after={f['id']:f for f in result['facilities']}
    missing=set(before)-set(after)
    if missing:raise CuratedSourceReviewError(len(missing),'omitted from new acquisition')
    changed={fid for fid,f in before.items() if _curated_material(f)!=_curated_material(after[fid])}
    if changed and not reviewed:raise CuratedSourceReviewError(len(changed),'changed and require individual source review')
    for fid,previous in before.items():
        current=after[fid];current['curated_source_record']=True
        history=copy.deepcopy(previous.get('curated_reference_history',[]))
        if not isinstance(history,list) or any(not isinstance(v,dict) for v in history):raise ValueError('invalid curated reference history')
        material=_curated_material(previous)
        if fid in changed and material not in history:history.append(material)
        if history or 'curated_reference_history' in previous:current['curated_reference_history']=history
        else:current.pop('curated_reference_history',None)


def _partial_scope(source):
    if source.get('limit') or any(source.get(k) is False for k in ('traversal_complete','acquisition_complete','collection_complete')):return True
    remaining=source.get('remaining_scope')
    return bool((isinstance(remaining,list) and remaining) or (isinstance(remaining,dict) and remaining.get('unvisited')))

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


def ensure_public_metadata(value):
    """Reject work-environment paths instead of silently editing evidence."""
    if isinstance(value,dict):
        for child in value.values():ensure_public_metadata(child)
    elif isinstance(value,list):
        for child in value:ensure_public_metadata(child)
    elif isinstance(value,str) and not value.startswith(('https://','http://')):
        pattern=r'(?:^|\s|["\'(=:])(?:/Users/|/home/|/private/tmp/|/private/var/|/var/folders/|[A-Za-z]:[\\/]Users[\\/])'
        if re.search(pattern,value):raise ValueError('local filesystem information cannot enter public canonical metadata')


def prepare_collection(data_dir,key,data,*,reviewed_curated=False):
    """Validate and reconcile an incoming snapshot without replacing its source."""
    ensure_public_metadata(data)
    if data.get('collection',{}).get('source_key')!=key: raise ValueError('source key differs from dataset')
    issues=blocking_problems(data)
    if issues: raise ValueError('source dataset validation failed: '+str(issues[:5]))
    path=source_path(data_dir,key)
    old=load_dataset(path) if path.exists() else None
    links_path=Path(data_dir)/'identities.json'
    all_links=load_dataset(links_path) if links_path.exists() else {}
    links=all_links.get(key,{})
    result=reconcile_identity(old,data,links)
    _preserve_curated_sources(old,result,reviewed_curated)
    if blocking_problems(result): raise ValueError('identity reconciliation produced invalid records')
    if old and _partial_scope(result['collection']):
        omitted={f['id'] for f in old['facilities']}-{f['id'] for f in result['facilities']}
        if omitted:raise PartialSnapshotError(len(omitted))
    ensure_public_metadata(result)
    return result


def save_collection(data_dir,key,data,*,reviewed_curated=False):
    """Save authoritative source facts; caches and work history live elsewhere."""
    result=prepare_collection(data_dir,key,data,reviewed_curated=reviewed_curated)
    write_json(source_path(data_dir,key),result)
    return result


def merge_collections(data_dir,*,states=None):
    """Merge repository canonical source files entirely offline, in memory."""
    data_dir=Path(data_dir); facilities=[]; entries=[]; sources={}
    for path in sorted((data_dir/'sources').glob('*.json')):
        data=load_dataset(path);ensure_public_metadata(data); key=path.stem
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
    ensure_public_metadata(states)
    for key,source in sources.items():
        code=source['prefecture_code']
        if states[code]['status']=='not_collected':
            reference_only=source.get('listing_basis') in ('wikipedia_reference','association_reference')
            states[code]=dict(states[code],status='collected_reference' if reference_only else 'collected',
                reason=('saved reference-only records; agency publication not asserted' if reference_only
                    else 'saved official listing records; coverage stated per source'),source_key=key)
    facilities.sort(key=lambda f:(f['prefecture_code'],f['id']))
    entries.sort(key=lambda e:(e['facility_id'],e['id']))
    result=dict(schema_version=1,facilities=facilities,entries=entries,collection=dict(
        source_key='national',sources=sources,prefecture_states=states,
        source_rows_observed=sum(s.get('source_rows_observed',0) for s in sources.values()),
        selected_rows=len(facilities),
        coverage=('observed agency listings and user-authorized reference-only records; see source basis and prefecture scope'
            if any(s.get('listing_basis') in ('wikipedia_reference','association_reference') for s in sources.values())
            else 'observed official listings only; see each prefecture state and source coverage'),
        redistribution_status='see source-specific conditions'))
    issues=blocking_problems(result)
    if issues: raise ValueError('merged canonical validation failed: '+str(issues[:5]))
    return result


def public_failure(exc):
    """Controlled public reason: never publish exception messages or paths."""
    from njd.http import FetchError
    if isinstance(exc,CuratedSourceReviewError):return f'curated_source_review_required ({exc.count}; {exc.kind}); previous snapshot preserved'
    if isinstance(exc,PartialSnapshotError):return f'partial_acquisition_omits_saved_records ({exc.omitted_count}); previous snapshot preserved'
    if isinstance(exc,OSError):return f'local_io_error ({type(exc).__name__}, errno={exc.errno})'
    if isinstance(exc,UnicodeError):return 'declared_encoding_decode_error'
    if isinstance(exc,FetchError):
        status=re.search(r'HTTP ([1-5][0-9]{2})',str(exc))
        if status:return 'source_http_error ('+status.group(1)+')'
        if 'robots' in str(exc).lower():return 'source_robots_policy_unavailable_or_disallowed'
        return 'source_fetch_failed; inspect private diagnostics'
    if isinstance(exc,ValueError):return 'source_structure_or_canonical_validation_failed'
    return 'unexpected_collection_failure; inspect private diagnostics'


def run_collections(data_dir,registry,keys,*,offline=False,refresh=False,limit=None,cache_dir=None):
    data_dir=Path(data_dir);states=load_states(data_dir)
    manifest_path=data_dir/'manifest.json'
    manifest=load_dataset(manifest_path) if manifest_path.exists() else {}
    cache_dir=Path(cache_dir) if cache_dir is not None else Path.home()/'.cache'/'national-jinja-dictionary'/'http'
    repository=Path(__file__).resolve().parents[1]
    resolved=cache_dir.expanduser().resolve()
    if resolved==repository or repository in resolved.parents:
        raise ValueError('HTTP caches must stay outside the public repository')
    for key in keys:
        spec=registry[key];code=spec['code'];path=source_path(data_dir,key)
        try:
            client=Client(resolved,offline=offline,reviewed_html_robots=spec.get('reviewed_html_robots',()))
            # Guarded adapters check every redirect before requesting its target.
            client.refresh_requested=refresh
            if refresh:
                original=client.fetch
                client.fetch=lambda url,**kwargs: original(url,refresh=True,**{k:v for k,v in kwargs.items() if k!='refresh'})
                original_post=client.post_json
                client.post_json=lambda url,payload,**kwargs: original_post(url,payload,refresh=True,**{k:v for k,v in kwargs.items() if k!='refresh'})
            data=spec['collect'](client,limit=limit)
            saved=prepare_collection(data_dir,key,data)
            from njd.overlays import apply_saved_overlays
            from njd.report import _counts
            counts=_counts(apply_saved_overlays(saved,data_dir))
            # Malformed/stale overlay evidence must not leave a new snapshot
            # behind while the manifest claims the previous one was retained.
            write_json(path,saved)
            states[code]=dict(states[code],source_key=key,status=collection_status(saved),reason='saved explicit source fields; see source authority and coverage',
                facilities=counts['facilities'],facility_records=counts['facility_records'],source_alias_records=counts['source_alias_records'],verified_facilities=counts['verified_facilities'],
                dictionary_rows=counts['dictionary_rows'],pending_entries=counts['entry_status_counts'].get('pending',0),
                source_rows_observed=saved['collection'].get('source_rows_observed',0),
                remaining_scope=saved['collection'].get('remaining_scope',[]))
        except Exception as exc:
            states[code]=dict(states[code],source_key=key,status='failed_using_previous' if path.exists() else 'failed',reason=public_failure(exc))
            try:
                write_json(resolved/'diagnostics'/(key+'.json'),dict(source_key=key,exception_type=type(exc).__name__,message=str(exc)))
            except OSError:
                pass  # Cache permission failures must not abort independent sources.
        write_json(manifest_path,dict(manifest,schema_version=1,prefectures=states))
    return states


def collection_status(data):
    source=data['collection']
    if source.get('authority_status') in ('pending','unconfirmed'):return 'authority_pending'
    if _partial_scope(source):return 'partial'
    return 'collected'
