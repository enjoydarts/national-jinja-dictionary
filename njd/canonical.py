"""One authoritative record per source: observations, adopted values and evidence.

Version-one projections exist only in memory for the established validators and
the explicit migration audit. Normal generation never reads legacy overlays.
"""
import argparse
import copy
from contextlib import contextmanager
import fcntl
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

from njd.storage import json_bytes, load_dataset, write_json

INDEX = 'research_index.json'
LEGACY = ('locations.json', 'corrections.json', 'reviews.json', 'decisions.json',
          'identities.json', 'source_aliases.json', 'reading_research.json',
          'source_catalog.json', 'manifest.json')
RESERVED = {'source_record', 'judgments', 'research'}
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
    return (Path(root) / 'sources' / INDEX).exists()


@contextmanager
def repository_lock(root, *, exclusive=False):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    with (root / '.canonical.lock').open('a') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
        try:
            if (root / '.canonical-transaction.json').exists():
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
    return {k: copy.deepcopy(v) for k, v in record.items() if k not in RESERVED}


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
                if 'research' in record:
                    if kind != 'entries' or rid in research:
                        raise ValueError('duplicate or invalid research target')
                    research[rid] = copy.deepcopy(record['research'])
    for name, filename, path, kind in BINDINGS:
        if filename not in result:
            continue
        target = _mapping(result[filename], path)
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
    legacy = _project(documents, index)
    expected = _evaluate(legacy)
    for kind in ('facilities', 'entries'):
        actual = {r['id']: _strip(r) for doc in documents.values() for r in doc[kind]}
        wanted = {r['id']: r for r in expected[kind]}
        if actual != wanted:
            changed = sorted(k for k in actual.keys() | wanted.keys() if actual.get(k) != wanted.get(k))
            raise ValueError('adopted values differ from source evidence/judgments: ' + str(changed[:5]))
    return expected


def load_effective(root):
    with repository_lock(root):
        return _validate(*_read(root))


def read_judgments(root, kind):
    return export_legacy(root).get(kind + '.json',
        dict(schema_version=1, entries={}) if kind in ('corrections', 'reviews') else {})


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
                current = copy.deepcopy(adopted[kind][source['id']])
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
            current = copy.deepcopy(entry)
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
    index = dict(schema_version=2, kind='canonical_index', source_keys=sorted(documents), metadata=metadata)
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


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    command = sub.add_parser('migrate')
    command.add_argument('--data-dir', type=Path, default=Path('data'))
    command.add_argument('--destination', type=Path, required=True)
    args = parser.parse_args(argv)
    print(json.dumps(migrate(args.data_dir, args.destination), ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
