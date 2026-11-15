"""One authoritative record per source: observations, adopted values and evidence.

Version-one projections exist only in memory for the established validators and
the explicit migration audit. Normal generation never reads legacy overlays.
"""
import argparse
from collections import Counter
import copy
from contextlib import contextmanager
import fcntl
import json
from pathlib import Path
import re
import shutil
import tempfile

from njd.storage import load_dataset, write_json

INDEX = 'research_index.json'
LEGACY = ('locations.json', 'corrections.json', 'reviews.json', 'decisions.json',
          'identities.json', 'source_aliases.json', 'reading_research.json',
          'source_catalog.json', 'manifest.json')
RESERVED = {'source_record', 'judgments', 'research', 'observation_history'}
DERIVED_EVIDENCE = {'correction', 'human_review', 'source_alias_resolution',
                    'location_research', 'location_supplement'}
# name, document, dictionary path, target collection
BINDINGS = (
    ('locations', 'locations.json', ('facilities',), 'facilities'),
    ('location_history', 'locations.json', ('superseded_facilities',), 'facilities'),
    ('location_research', 'locations.json', ('research', 'facilities'), 'facilities'),
    ('corrections', 'corrections.json', ('entries',), 'entries'),
    ('reviews', 'reviews.json', ('entries',), 'entries'),
    ('decisions', 'decisions.json', (), 'entries'),
    ('source_aliases', 'source_aliases.json', ('resolutions',), 'facilities'),
)


def is_canonical(root):
    return (Path(root) / 'sources' / INDEX).exists() or (Path(root) / '.canonical-transaction.json').exists()


@contextmanager
def repository_lock(root, *, exclusive=False, recovery=False):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    with (root / '.canonical.lock').open('a') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
        try:
            if not recovery and (root / '.canonical-transaction.json').exists():
                raise ValueError('unfinished canonical transaction; recover before reading or writing')
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def _mapping(document, path):
    for key in path:
        document = document.get(key, {})
    if not isinstance(document, dict):
        raise ValueError('invalid judgment mapping')
    return document


def _strip(record):
    return {k: copy.deepcopy(v) for k, v in record.items() if k not in RESERVED | DERIVED_EVIDENCE}


def raw_collection(document):
    if document.get('schema_version') != 2:
        return copy.deepcopy(document)
    result = copy.deepcopy(document.get('source_metadata', {}))
    result.update(schema_version=1, collection=copy.deepcopy(document['collection']))
    for kind in ('facilities', 'entries'):
        result[kind] = [copy.deepcopy(r['source_record']) for r in document[kind]
                        if r.get('source_record') is not None]
    return result


def _read(root):
    root = Path(root)
    if not is_canonical(root):
        raise ValueError('canonical schema v2 is required; run python3 -m njd.canonical migrate')
    if any((root / name).exists() for name in LEGACY) or (root / 'common.json').exists():
        raise ValueError('legacy inputs coexist with canonical data; two editable authorities are forbidden')
    index = load_dataset(root / 'sources' / INDEX)
    if index.get('schema_version') != 2 or index.get('kind') != 'canonical_index':
        raise ValueError('invalid canonical index')
    documents = {}
    for path in sorted((root / 'sources').glob('*.json')):
        if path.name == INDEX:
            continue
        doc = load_dataset(path)
        if doc.get('schema_version') != 2 or doc.get('collection', {}).get('source_key') != path.stem:
            raise ValueError('invalid or mixed canonical source: ' + path.stem)
        documents[path.stem] = doc
    if set(documents) != set(index['source_keys']):
        raise ValueError('canonical source set differs from index')
    return documents, index


def _project(documents, index):
    result = copy.deepcopy(index['metadata'])
    records = {kind: {} for kind in ('facilities', 'entries')}
    research = {}
    catalogs = {}
    for key, doc in documents.items():
        result['sources/' + key + '.json'] = raw_collection(doc)
        if 'identity_links' in doc:
            result['identities.json'][key] = copy.deepcopy(doc['identity_links'])
        for item in doc.get('catalog_entries', []):
            catalogs[item['position']] = copy.deepcopy(item['record'])
        for kind in records:
            for record in doc[kind]:
                rid = record['id']
                if rid in records[kind]:
                    raise ValueError('duplicate canonical record id: ' + rid)
                records[kind][rid] = record
                judgments = record.get('judgments')
                allowed = {name for name, _, _, target in BINDINGS if target == kind}
                if not isinstance(judgments, dict) or set(judgments) - allowed:
                    raise ValueError('unknown or invalid canonical judgment: ' + rid)
                if any(not isinstance(value, (dict, list)) for value in judgments.values()):
                    raise ValueError('invalid canonical judgment value: ' + rid)
                if 'research' in record:
                    if kind != 'entries' or rid in research:
                        raise ValueError('duplicate or invalid research target')
                    item = record['research']
                    if (not isinstance(item, dict) or item.get('entry_id') != rid
                            or item.get('facility_id') != record.get('facility_id')):
                        raise ValueError('research is not bound to its owning entry/facility: ' + rid)
                    research[rid] = copy.deepcopy(record['research'])
    for name, filename, path, kind in BINDINGS:
        if filename not in result:
            if not any(name in r['judgments'] for r in records[kind].values()):
                continue
            result[filename] = {} if filename == 'decisions.json' else dict(schema_version=1)
        target = result[filename]
        for part in path:
            target = target.setdefault(part, {})
        if not isinstance(target, dict):
            raise ValueError('invalid canonical judgment mapping')
        for rid, record in records[kind].items():
            if name in record.get('judgments', {}):
                target[rid] = copy.deepcopy(record['judgments'][name])
    if 'reading_research.json' in result:
        order = index.get('research_order', [])
        if set(order) != set(research) or len(order) != len(research):
            raise ValueError('research record index differs')
        result['reading_research.json']['records'] = [research[eid] for eid in order]
    if 'source_catalog.json' in result:
        for item in index.get('uncollected_catalog_entries', []):
            catalogs[item['position']] = copy.deepcopy(item['record'])
        if sorted(catalogs) != list(range(index['catalog_size'])):
            raise ValueError('source catalog index differs')
        result['source_catalog.json']['prefectures'] = [catalogs[i] for i in sorted(catalogs)]
    return result


def export_legacy(root):
    """Lossless, explicit audit projection; never a second stored authority."""
    with repository_lock(root):
        return _project(*_read(root))


def _merged_raw(legacy):
    from njd.nationwide import default_states, ensure_public_metadata
    from njd.validation import blocking_problems
    sources = {}; facilities = []; entries = []
    for name, raw in sorted(legacy.items()):
        if not name.startswith('sources/'):
            continue
        key = Path(name).stem
        ensure_public_metadata(raw)
        if raw['collection']['source_key'] != key or blocking_problems(raw):
            raise ValueError('invalid source observation: ' + key)
        sources[key] = copy.deepcopy(raw['collection'])
        facilities.extend(copy.deepcopy(raw['facilities']))
        entries.extend(copy.deepcopy(raw['entries']))
    states = default_states()
    states.update(copy.deepcopy(legacy.get('manifest.json', {}).get('prefectures', {})))
    for key, source in sources.items():
        code = source['prefecture_code']
        if states[code]['status'] == 'not_collected':
            reference = source.get('listing_basis') in ('wikipedia_reference', 'association_reference')
            states[code] = dict(states[code], status='collected_reference' if reference else 'collected',
                reason='saved reference-only records; agency publication not asserted' if reference
                    else 'saved official listing records; coverage stated per source', source_key=key)
    facilities.sort(key=lambda f: (f['prefecture_code'], f['id']))
    entries.sort(key=lambda e: (e['facility_id'], e['id']))
    return dict(schema_version=1, facilities=facilities, entries=entries, collection=dict(
        source_key='national', sources=sources, prefecture_states=states,
        source_rows_observed=sum(s.get('source_rows_observed', 0) for s in sources.values()),
        selected_rows=len(facilities),
        coverage=('observed agency listings and user-authorized reference-only records; see source basis and prefecture scope'
            if any(s.get('listing_basis') in ('wikipedia_reference', 'association_reference') for s in sources.values())
            else 'observed official listings only; see each prefecture state and source coverage'),
        redistribution_status='see source-specific conditions'))


def _evaluate(legacy):
    from njd.locations import apply_locations
    from njd.corrections import apply_corrections
    from njd.reviews import apply_reviews
    from njd.storage import apply_decisions
    from njd.source_aliases import apply_source_aliases
    from njd.validation import blocking_problems
    data = _merged_raw(legacy)
    for filename, apply in (('locations.json', apply_locations),
                            ('corrections.json', apply_corrections),
                            ('reviews.json', apply_reviews), ('decisions.json', apply_decisions)):
        if filename in legacy:
            data = apply(data, legacy[filename])
    if 'source_aliases.json' in legacy:
        decisions = legacy.get('decisions.json', {})
        protected = {e['id'] for e in data['entries'] if decisions.get(e['id'], {}).get('status') == 'pending'
            and decisions[e['id']].get('expected_source_hash') == e.get('source_hash')}
        data = apply_source_aliases(data, legacy['source_aliases.json'], protected_pending_entry_ids=protected)
    issues = blocking_problems(data)
    if issues:
        raise ValueError('canonical evidence validation failed: ' + str(issues[:5]))
    return data


def _validate(documents, index):
    from njd.nationwide import ensure_public_metadata
    ensure_public_metadata(index)
    for doc in documents.values():
        ensure_public_metadata(doc)
        for kind in ('facilities', 'entries'):
            for record in doc[kind]:
                if DERIVED_EVIDENCE & record.keys():
                    raise ValueError('derived evidence must not duplicate canonical judgments')
    _validate_identity_links(documents)
    legacy = _project(documents, index)
    expected = _evaluate(legacy)
    for kind in ('facilities', 'entries'):
        actual = {r['id']: _strip(r) for doc in documents.values() for r in doc[kind]}
        wanted = {r['id']: _strip(r) for r in expected[kind]}
        if actual != wanted:
            changed = sorted(k for k in actual.keys() | wanted.keys() if actual.get(k) != wanted.get(k))
            raise ValueError('adopted values differ from source evidence/judgments: ' + str(changed[:5]))
    return expected


def _validate_identity_links(documents):
    known = {}
    for doc in documents.values():
        for fid, item in doc['collection'].get('identity_history', {}).items():
            known.setdefault(fid, set()).add(item.get('source_hash'))
        facilities = list(doc['facilities']) + [a['record']
            for a in doc.get('source_metadata', {}).get('retired_records', []) if a['kind'] == 'facilities']
        for record in facilities:
            for observation in [record.get('source_record')] + record.get('observation_history', []):
                if observation:
                    known.setdefault(record['id'], set()).add(observation.get('source_hash'))
    for doc in documents.values():
        links = doc.get('identity_links', {})
        if not isinstance(links, dict):
            raise ValueError('invalid identity links')
        for source_id, link in links.items():
            if not isinstance(link, dict) or not link.get('reason'):
                raise ValueError('identity link requires evidence and reason')
            target = link.get('facility_id')
            expected = link.get('expected_source_hash', '')
            if target not in known or not isinstance(expected, str) or not re.fullmatch('[0-9a-f]{64}', expected):
                raise ValueError('identity link has unknown target or invalid hash')
            if expected not in known.get(source_id, set()) | known[target]:
                raise ValueError('identity link hash does not match current or historical observation')


def load_effective(root):
    with repository_lock(root):
        return _validate(*_read(root))


def read_judgments(root, kind):
    return export_legacy(root).get(kind + '.json',
        dict(schema_version=1, entries={}) if kind in ('corrections', 'reviews') else {})


def research_summary(root):
    """Compute current research counts; never trust historical snapshot totals."""
    with repository_lock(root):
        documents, index = _read(root)
        effective = _validate(documents, index)
        tracking = index['metadata'].get('reading_research.json', {}).get('completion_tracking', {})
        targets = set(index.get('research_order', [])) | set(tracking.get('resolved_entry_ids', []))
        entries = {e['id']: e for e in effective['entries']}
        records = {e['id']: e['research'] for d in documents.values() for e in d['entries'] if 'research' in e}
        retired = {a['record']['id']: a['record'] for d in documents.values()
                   for a in d.get('source_metadata', {}).get('retired_records', [])
                   if a['kind'] == 'entries' and ('research' in a['record'] or a['record']['id'] in targets)}
        targets.update(eid for eid, e in retired.items() if 'research' in e)
        inactive = {eid: e for eid, e in retired.items() if eid not in entries}
        entries.update(inactive)
        records.update({eid: e['research'] for eid, e in inactive.items() if 'research' in e})
        if targets - entries.keys():
            raise ValueError('research target missing from active and retired canonical entries')
        pending = {eid for eid in targets if entries[eid]['status'] == 'pending'}
        categories = Counter(records.get(eid, {}).get('category', 'unclassified_pending') for eid in pending)
        return dict(targets=len(targets), pending=len(pending), resolved=len(targets-pending), retired=len(inactive),
            categories=dict(sorted(categories.items())),
            notice='Current canonical states; resolution counts do not assert full prefecture coverage.')


def initialize(root):
    """Start a new empty canonical repository; never implicitly convert old data."""
    root = Path(root)
    with repository_lock(root, exclusive=True):
        if any((root / name).exists() for name in LEGACY) or list((root / 'sources').glob('*.json')):
            raise ValueError('existing inputs require explicit migration')
        documents, index = _pack({})
        _write_sources(root / 'sources', documents, index)


def _commit_sources(root, documents, index, *, retire_legacy=False):
    stage = Path(tempfile.mkdtemp(prefix='.canonical-stage-', dir=root))
    journal = root / '.canonical-transaction.json'
    moved = installed = False
    cleanup = False
    retired = []
    try:
        _write_sources(stage / 'sources', documents, index)
        _validate(*_read(stage))
        write_json(journal, dict(stage=stage.name))
        (root / 'sources').rename(stage / 'previous')
        moved = True
        (stage / 'sources').rename(root / 'sources')
        installed = True
        if retire_legacy:
            (stage / 'legacy').mkdir()
            for name in LEGACY:
                if (root / name).exists():
                    (root / name).rename(stage / 'legacy' / name)
                    retired.append(name)
        journal.unlink()
        cleanup = True
    except BaseException:
        if installed:
            shutil.rmtree(root / 'sources')
        if moved:
            (stage / 'previous').rename(root / 'sources')
        for name in retired:
            (stage / 'legacy' / name).rename(root / name)
        journal.unlink(missing_ok=True)
        cleanup = True
        raise
    finally:
        # If rollback itself failed, the journal and backup are the only
        # recovery path. Never discard them in that case.
        if cleanup:
            shutil.rmtree(stage, ignore_errors=True)


def recover(root):
    """Roll back a crashed generation switch under the same writer lock."""
    root = Path(root)
    with repository_lock(root, exclusive=True, recovery=True):
        journal = root / '.canonical-transaction.json'
        if not journal.exists():
            return
        name = load_dataset(journal).get('stage', '')
        if not name.startswith('.canonical-stage-') or Path(name).name != name:
            raise ValueError('invalid canonical recovery path')
        stage = root / name
        if (stage / 'previous').exists():
            if (root / 'sources').exists():
                shutil.rmtree(root / 'sources')
            (stage / 'previous').rename(root / 'sources')
        elif not (root / 'sources').exists():
            raise ValueError('canonical recovery has no previous generation')
        for path in (stage / 'legacy').glob('*.json'):
            if path.name not in LEGACY or (root / path.name).exists():
                raise ValueError('canonical recovery legacy-file conflict')
            path.rename(root / path.name)
        journal.unlink()
        shutil.rmtree(stage, ignore_errors=True)


def update_repository(root, change, *, apply=True):
    """Validate one in-memory edit, then switch the entire generation atomically."""
    root = Path(root)
    with repository_lock(root, exclusive=True):
        documents, index = _read(root)
        previous = _validate(documents, index)
        legacy = _project(documents, index)
        result = change(legacy)
        _retire_disappeared(documents, legacy)
        after, new_index = _pack(legacy)
        current = _evaluate(legacy)
        states = {e['id']: e for e in current['entries']}
        old_entries = {e['id']: e for e in previous['entries']}
        for key, doc in after.items():
            before = documents.get(key, {})
            for kind in ('facilities', 'entries'):
                old = {r['id']: r for r in before.get(kind, [])}
                for record in doc[kind]:
                    prior = old.get(record['id'])
                    if not prior:
                        continue
                    history = copy.deepcopy(prior.get('observation_history', []))
                    if prior['source_record'] != record['source_record'] and prior['source_record'] is not None:
                        history.append(copy.deepcopy(prior['source_record']))
                    if history:
                        record['observation_history'] = history
                    if kind == 'entries' and 'research' in record:
                        old_status = old_entries.get(record['id'], {}).get('status')
                        new_status = states[record['id']]['status']
                        if old_status != new_status:
                            resolution = dict(previous_status=old_status, status=new_status,
                                reason=states[record['id']]['reason'], reading=states[record['id']]['reading'])
                            record['research'].setdefault('resolution_history', []).append(resolution)
                            record['research']['resolution'] = resolution
        _validate(after, new_index)
        if apply and (after != documents or new_index != index):
            _commit_sources(root, after, new_index)
        return result


def _retire_disappeared(documents, legacy):
    """Preserve vanished observations/derived rows without keeping them active."""
    def retire(key, kind, record):
        raw = legacy['sources/' + key + '.json']
        archive = raw.setdefault('retired_records', [])
        item = dict(kind=kind, record=copy.deepcopy(record),
            reason='Absent from complete source snapshot or no longer derived by valid source-bound review.')
        if item not in archive:
            archive.append(item)
        for name, filename, path, target in BINDINGS:
            if target == kind and filename in legacy:
                _mapping(legacy[filename], path).pop(record['id'], None)
        if kind == 'entries' and 'reading_research.json' in legacy:
            research = legacy['reading_research.json']
            research['records'] = [r for r in research.get('records', []) if r['entry_id'] != record['id']]

    for key, doc in documents.items():
        raw = legacy.get('sources/' + key + '.json')
        if raw is None:
            raise ValueError('source removal requires an explicit archive')
        prior_archive = doc.get('source_metadata', {}).get('retired_records', [])
        if prior_archive:
            raw.setdefault('retired_records', copy.deepcopy(prior_archive))
        for kind in ('facilities', 'entries'):
            ids = {r['id'] for r in raw[kind]}
            for record in doc[kind]:
                if record['source_record'] is not None and record['id'] not in ids:
                    retire(key, kind, record)
    _restore_returned(legacy)
    # A changed parent can invalidate a split and remove its children even
    # when no raw observation disappeared. Archive those judgments as well.
    effective = _evaluate(legacy)
    active = {e['id'] for e in effective['entries']}
    for key, doc in documents.items():
        for record in doc['entries']:
            if record['source_record'] is None and record['id'] not in active:
                retire(key, 'entries', record)


def _restore_returned(legacy):
    """Exact reappearances retain prior decisions, including derived exclusions."""
    archives = [a for name, raw in legacy.items() if name.startswith('sources/')
                for a in raw.get('retired_records', [])]
    if not archives:
        return
    # Locations can change the bound hash; reviews can create derived rows.
    # Re-evaluate after each restored layer rather than guessing their state.
    for _ in range(len(BINDINGS) + 1):
        effective = _evaluate(legacy)
        current = {kind: {r['id']: r for r in effective[kind]} for kind in ('facilities', 'entries')}
        changed = False
        for archived in reversed(archives):
            kind = archived['kind']; record = archived['record']; rid = record['id']
            active = current[kind].get(rid)
            original = record.get('source_record') or record
            if active is None or original.get('source_hash') != active.get('source_hash'):
                continue
            for name, filename, path, target in BINDINGS:
                if target != kind or name not in record['judgments']:
                    continue
                document = legacy.setdefault(filename, {} if filename == 'decisions.json' else dict(schema_version=1))
                for part in path:
                    document = document.setdefault(part, {})
                if rid not in document:
                    document[rid] = copy.deepcopy(record['judgments'][name])
                    changed = True
            if kind == 'entries' and 'research' in record:
                research = legacy.setdefault('reading_research.json', dict(schema_version=1, records=[]))
                if not any(r['entry_id'] == rid for r in research['records']):
                    research['records'].append(copy.deepcopy(record['research']))
                    changed = True
        if not changed:
            break


def _pack(legacy):
    legacy = copy.deepcopy(legacy)
    effective = _evaluate(legacy)
    adopted = {kind: {r['id']: r for r in effective[kind]} for kind in ('facilities', 'entries')}
    documents = {}; targets = {kind: {} for kind in adopted}; owners = {}
    for filename, raw in sorted(legacy.items()):
        if not filename.startswith('sources/'):
            continue
        key = Path(filename).stem
        doc = dict(schema_version=2, collection=copy.deepcopy(raw['collection']),
            source_metadata={k: copy.deepcopy(v) for k, v in raw.items()
                             if k not in ('schema_version', 'facilities', 'entries', 'collection')})
        for kind in targets:
            doc[kind] = []
            for source in raw[kind]:
                current = _strip(adopted[kind][source['id']])
                if RESERVED & current.keys():
                    raise ValueError('reserved canonical field in legacy record')
                current.update(source_record=copy.deepcopy(source), judgments={})
                if current['id'] in targets[kind]:
                    raise ValueError('duplicate source id')
                targets[kind][current['id']] = current
                doc[kind].append(current)
                if kind == 'facilities':
                    owners[current['id']] = key
        documents[key] = doc
    for eid, entry in adopted['entries'].items():
        if eid not in targets['entries']:
            current = _strip(entry)
            current.update(source_record=None, judgments={})
            targets['entries'][eid] = current
            documents[owners[entry['facility_id']]]['entries'].append(current)
    metadata = {k: copy.deepcopy(v) for k, v in legacy.items() if not k.startswith('sources/')}
    for name, filename, path, kind in BINDINGS:
        if filename not in metadata:
            continue
        mapping = _mapping(metadata[filename], path)
        for rid, judgment in list(mapping.items()):
            if rid not in targets[kind]:
                raise ValueError('unmatched judgment target: ' + rid)
            targets[kind][rid]['judgments'][name] = mapping.pop(rid)
    for key, links in list(metadata.get('identities.json', {}).items()):
        if key not in documents:
            raise ValueError('unmatched identity source: ' + key)
        documents[key]['identity_links'] = metadata['identities.json'].pop(key)
    index = dict(schema_version=2, kind='canonical_index', source_keys=sorted(documents), metadata=metadata,
        metadata_basis='Inherited collection/research snapshots, including old counts and hashes; generate current counts from adopted records.')
    research = metadata.get('reading_research.json')
    if research is not None:
        records = research.pop('records', [])
        index['research_order'] = []
        for record in records:
            eid = record['entry_id']
            if eid not in targets['entries'] or 'research' in targets['entries'][eid]:
                raise ValueError('unmatched or duplicate research target: ' + eid)
            targets['entries'][eid]['research'] = record
            index['research_order'].append(eid)
    catalog = metadata.get('source_catalog.json')
    if catalog is not None:
        records = catalog.pop('prefectures', [])
        index.update(catalog_size=len(records), uncollected_catalog_entries=[])
        by_code = {}
        for key, doc in documents.items():
            by_code.setdefault(doc['collection']['prefecture_code'], key)
        for pos, record in enumerate(records):
            item = dict(position=pos, record=record)
            key = by_code.get(record.get('prefecture_code'))
            if key:
                documents[key].setdefault('catalog_entries', []).append(item)
            else:
                index['uncollected_catalog_entries'].append(item)
    if _project(documents, index) != legacy:
        raise ValueError('migration would lose legacy source or editorial information')
    return documents, index


def _write_sources(destination, documents, index):
    for key, document in documents.items():
        write_json(destination / (key + '.json'), document)
    write_json(destination / INDEX, index)


def migrate(root, destination):
    """Explicit offline v1 -> v2 migration into a fresh directory, never in place."""
    root = Path(root); destination = Path(destination)
    if destination.exists():
        raise ValueError('migration destination must not exist')
    if is_canonical(root):
        raise ValueError('migration input must be legacy schema v1')
    paths = sorted((root / 'sources').glob('*.json'))
    if not paths:
        raise ValueError('no source collections to migrate')
    paths += [root / name for name in LEGACY if (root / name).exists()]
    before = {str(p.relative_to(root)): p.read_bytes() for p in paths}
    legacy = {name: json.loads(content) for name, content in before.items()}
    documents, index = _pack(legacy)
    _validate(documents, index)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix='.canonical-migrate-', dir=destination.parent))
    try:
        _write_sources(temporary / 'sources', documents, index)
        _validate(*_read(temporary))
        if before != {str(p.relative_to(root)): p.read_bytes() for p in paths}:
            raise ValueError('migration inputs changed during review')
        temporary.rename(destination)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    return dict(sources=len(documents), facilities=sum(len(d['facilities']) for d in documents.values()),
                entries=sum(len(d['entries']) for d in documents.values()), lossless=True)


def install_migration(root, migrated):
    """Install a reviewed migration only if every original input still matches."""
    root = Path(root)
    with repository_lock(migrated):
        documents, index = _read(migrated)
        _validate(documents, index)
        expected = _project(documents, index)
    with repository_lock(root, exclusive=True):
        if is_canonical(root):
            raise ValueError('installation target must still be schema v1')
        paths = list((root / 'sources').glob('*.json'))
        paths += [root / name for name in LEGACY if (root / name).exists()]
        actual = {str(p.relative_to(root)): load_dataset(p) for p in paths}
        if actual != expected:
            raise ValueError('migration input has changed; regenerate and review before installation')
        _commit_sources(root, documents, index, retire_legacy=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    command = sub.add_parser('migrate')
    command.add_argument('--data-dir', type=Path, default=Path('data'))
    command.add_argument('--destination', type=Path, required=True)
    recovery = sub.add_parser('recover')
    recovery.add_argument('--data-dir', type=Path, default=Path('data'))
    summary = sub.add_parser('summary')
    summary.add_argument('--data-dir', type=Path, default=Path('data'))
    install = sub.add_parser('install')
    install.add_argument('--data-dir', type=Path, default=Path('data'))
    install.add_argument('--migrated', type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == 'recover':
        recover(args.data_dir)
        return 0
    if args.command == 'summary':
        print(json.dumps(research_summary(args.data_dir), ensure_ascii=False))
        return 0
    if args.command == 'install':
        install_migration(args.data_dir, args.migrated)
        return 0
    print(json.dumps(migrate(args.data_dir, args.destination), ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
