import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_records import build, row
from test_corrections import correction
from njd.nationwide import save_collection
from njd.storage import load_dataset, write_json
from njd.exporters import render


class CanonicalTests(unittest.TestCase):
    def setup_repository(self, directory):
        root = Path(directory) / 'old'
        data = build([row(reading_raw='')])
        save_collection(root, 'example', data)
        eid = data['entries'][0]['id']
        proposal = correction(data, {'reading': 'かくうじんじゃ'})
        write_json(root / 'corrections.json', proposal)
        research = dict(schema_version=1, records=[dict(entry_id=eid,
            facility_id=data['facilities'][0]['id'], reason='以前の確認記録',
            expected_source_hash=data['entries'][0]['source_hash'])],
            external_source_attempts=[dict(id='attempt', reason='調査履歴')])
        write_json(root / 'reading_research.json', research)
        return root, data, proposal, research

    def test_migration_preserves_raw_judgments_research_and_dictionary_bytes(self):
        from njd.canonical import migrate, load_effective, export_legacy
        from njd.__main__ import _effective
        with tempfile.TemporaryDirectory() as td:
            root, data, proposal, research = self.setup_repository(td)
            before = _effective(root, legacy=True)
            destination = Path(td) / 'new'
            migrate(root, destination)
            document = load_dataset(destination / 'sources/example.json')
            self.assertEqual(document['schema_version'], 2)
            entry = document['entries'][0]
            self.assertEqual(entry['reading'], 'かくうじんじゃ')
            self.assertEqual(entry['source_record'], data['entries'][0])
            self.assertEqual(entry['judgments']['corrections'], proposal['entries'][entry['id']])
            self.assertEqual(entry['research'], research['records'][0])
            old = export_legacy(destination)
            self.assertEqual(old['sources/example.json'], load_dataset(root / 'sources/example.json'))
            self.assertEqual(old['corrections.json'], proposal)
            self.assertEqual(old['reading_research.json'], research)
            self.assertFalse((destination / 'corrections.json').exists())
            after = load_effective(destination)
            self.assertEqual(before, after)
            for fmt in ('mozc', 'google', 'atok', 'atok_unicode', 'msime', 'macos'):
                self.assertEqual(render(before, fmt).content, render(after, fmt).content)

    def test_changed_adopted_reading_without_matching_evidence_is_rejected(self):
        from njd.canonical import migrate, load_effective
        with tempfile.TemporaryDirectory() as td:
            root, _, _, _ = self.setup_repository(td)
            destination = Path(td) / 'new'
            migrate(root, destination)
            path = destination / 'sources/example.json'
            doc = load_dataset(path)
            doc['entries'][0]['reading'] = 'すいそく'
            write_json(path, doc)
            with self.assertRaisesRegex(ValueError, 'adopted|採用'):
                load_effective(destination)

    def test_old_overlay_alongside_canonical_data_is_rejected(self):
        from njd.canonical import migrate, load_effective
        with tempfile.TemporaryDirectory() as td:
            root, _, proposal, _ = self.setup_repository(td)
            destination = Path(td) / 'new'
            migrate(root, destination)
            write_json(destination / 'corrections.json', proposal)
            with self.assertRaisesRegex(ValueError, 'legacy|旧'):
                load_effective(destination)

    def test_failed_migration_leaves_source_and_existing_destination_untouched(self):
        from njd.canonical import migrate
        with tempfile.TemporaryDirectory() as td:
            root, _, _, _ = self.setup_repository(td)
            before = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*.json')}
            destination = Path(td) / 'new'
            destination.mkdir()
            (destination / 'keep').write_text('keep')
            with self.assertRaises(ValueError):
                migrate(root, destination)
            self.assertEqual((destination / 'keep').read_text(), 'keep')
            self.assertEqual(before, {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*.json')})

    def test_unmatched_judgment_is_not_silently_discarded(self):
        from njd.canonical import migrate
        with tempfile.TemporaryDirectory() as td:
            root, _, proposal, _ = self.setup_repository(td)
            proposal['entries']['missing-id'] = copy.deepcopy(next(iter(proposal['entries'].values())))
            write_json(root / 'corrections.json', proposal)
            destination = Path(td) / 'new'
            with self.assertRaises(ValueError):
                migrate(root, destination)
            self.assertFalse(destination.exists())

    def test_cli_and_release_read_only_the_new_canonical_sources(self):
        import contextlib
        import io
        import zipfile
        from njd.canonical import migrate
        from njd.__main__ import main
        from njd.release import create_release
        with tempfile.TemporaryDirectory() as td:
            root, _, _, _ = self.setup_repository(td)
            destination = Path(td) / 'new'
            migrate(root, destination)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(['--data-dir', str(destination), '--output-dir',
                                       str(Path(td) / 'validate'), 'validate']), 0)
            with patch('njd.http.request', side_effect=AssertionError('must stay offline')):
                result = create_release(destination, Path(td) / 'out', 'test', 'a' * 40)
            with zipfile.ZipFile(result['archive']) as archive:
                self.assertEqual(archive.read('national/mozc.txt'),
                                 'かくうじんじゃ\t架空神社\t固有名詞\n'.encode())
                provenance = __import__('json').loads(archive.read('SOURCE.json'))
                self.assertIn('sources/research_index.json', provenance['data_files'])
                self.assertNotIn('corrections.json', provenance['data_files'])

    def test_normal_generation_requires_explicit_migration_of_legacy_inputs(self):
        from njd.__main__ import main
        with tempfile.TemporaryDirectory() as td:
            root, _, _, _ = self.setup_repository(td)
            with self.assertRaisesRegex(ValueError, 'migrat|v2'):
                main(['--data-dir', str(root), '--output-dir', str(Path(td) / 'out'), 'validate'])

    def test_proposal_updates_canonical_entry_without_creating_overlay_file(self):
        from njd.canonical import migrate, load_effective, research_summary
        from njd.proposals import import_proposals
        with tempfile.TemporaryDirectory() as td:
            root, data, proposal, _ = self.setup_repository(td)
            (root / 'corrections.json').unlink()
            destination = Path(td) / 'new'
            migrate(root, destination)
            self.assertEqual(research_summary(destination)['pending'], 1)
            original = load_dataset(destination / 'sources/example.json')['entries'][0]['source_record']
            self.assertEqual(import_proposals(destination, proposal)['added'], 1)
            self.assertEqual(load_effective(destination)['entries'][0]['reading'], '')
            self.assertEqual(import_proposals(destination, proposal, apply=True)['added'], 1)
            entry = load_dataset(destination / 'sources/example.json')['entries'][0]
            self.assertEqual(entry['reading'], 'かくうじんじゃ')
            self.assertEqual(entry['source_record'], original)
            self.assertTrue(entry['research']['resolution'])
            self.assertEqual(research_summary(destination)['pending'], 0)
            self.assertFalse((destination / 'corrections.json').exists())
            self.assertEqual(import_proposals(destination, proposal, apply=True)['unchanged'], 1)

    def test_refetch_preserves_judgments_and_quarantines_changed_source(self):
        from njd.canonical import migrate, load_effective
        with tempfile.TemporaryDirectory() as td:
            root, data, proposal, _ = self.setup_repository(td)
            destination = Path(td) / 'new'
            migrate(root, destination)
            save_collection(destination, 'example', data)
            self.assertEqual(load_effective(destination)['entries'][0]['reading'], 'かくうじんじゃ')
            changed = build([row(reading_raw='', address='架空市乙町2')])
            save_collection(destination, 'example', changed)
            entry = load_dataset(destination / 'sources/example.json')['entries'][0]
            self.assertEqual(entry['status'], 'pending')
            self.assertEqual(entry['reading'], '')
            self.assertEqual(entry['judgments']['corrections'], proposal['entries'][entry['id']])
            self.assertEqual(entry['observation_history'][-1], data['entries'][0])

    def test_write_failure_restores_previous_generation(self):
        from njd.canonical import migrate, load_effective
        from njd.proposals import import_proposals
        with tempfile.TemporaryDirectory() as td:
            root, _, proposal, _ = self.setup_repository(td)
            (root / 'corrections.json').unlink()
            destination = Path(td) / 'new'
            migrate(root, destination)
            before = {p.name: p.read_bytes() for p in (destination / 'sources').glob('*.json')}
            rename = Path.rename
            def fail_install(path, target):
                if path.name == 'sources' and path.parent.name.startswith('.canonical-stage-'):
                    raise OSError('injected installation failure')
                return rename(path, target)
            with patch.object(Path, 'rename', fail_install):
                with self.assertRaises(OSError):
                    import_proposals(destination, proposal, apply=True)
            self.assertEqual(before, {p.name: p.read_bytes() for p in (destination / 'sources').glob('*.json')})
            self.assertEqual(load_effective(destination)['entries'][0]['reading'], '')

    def test_interrupted_transaction_is_rejected_until_explicit_recovery(self):
        from njd.canonical import migrate, load_effective, recover
        with tempfile.TemporaryDirectory() as td:
            root, _, _, _ = self.setup_repository(td)
            destination = Path(td) / 'new'
            migrate(root, destination)
            stage = destination / '.canonical-stage-test'
            stage.mkdir()
            (destination / 'sources').rename(stage / 'previous')
            write_json(destination / '.canonical-transaction.json', dict(stage=stage.name))
            with self.assertRaisesRegex(ValueError, 'transaction'):
                load_effective(destination)
            recover(destination)
            self.assertEqual(load_effective(destination)['entries'][0]['reading'], 'かくうじんじゃ')

    def test_collection_updates_and_failures_never_create_legacy_manifest(self):
        from njd.canonical import migrate, load_effective
        from njd.nationwide import run_collections
        with tempfile.TemporaryDirectory() as td:
            root, data, _, _ = self.setup_repository(td)
            destination = Path(td) / 'new'
            migrate(root, destination)
            registry = dict(example=dict(code='11', collect=lambda client, limit: data))
            with patch('njd.nationwide.Client'):
                result = run_collections(destination, registry, ['example'], cache_dir=Path(td) / 'cache')
            self.assertEqual(result['11']['status'], 'collected')
            self.assertEqual(load_effective(destination)['entries'][0]['reading'], 'かくうじんじゃ')
            registry['example']['collect'] = lambda *args, **kwargs: (_ for _ in ()).throw(OSError('failure'))
            with patch('njd.nationwide.Client'):
                result = run_collections(destination, registry, ['example'], cache_dir=Path(td) / 'cache')
            self.assertEqual(result['11']['status'], 'failed_using_previous')
            self.assertFalse((destination / 'manifest.json').exists())
            self.assertEqual(load_effective(destination)['entries'][0]['reading'], 'かくうじんじゃ')

    def test_aliases_and_exclusions_survive_without_duplicate_application(self):
        from njd.canonical import migrate, load_effective, export_legacy
        from test_source_aliases import data, document
        from njd.__main__ import _effective
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'old'
            fixture = data()
            save_collection(root, 'kochi', fixture)
            aliases = document(fixture)
            write_json(root / 'source_aliases.json', aliases)
            expected = _effective(root, legacy=True)
            destination = Path(td) / 'new'
            migrate(root, destination)
            self.assertEqual(load_effective(destination), expected)
            self.assertEqual(export_legacy(destination)['source_aliases.json'], aliases)

    def test_research_targets_use_source_records_and_skip_index(self):
        from njd.canonical import migrate
        from njd.wikipedia import pending_targets
        with tempfile.TemporaryDirectory() as td:
            root, _, _, _ = self.setup_repository(td)
            (root / 'corrections.json').unlink()
            destination = Path(td) / 'new'
            migrate(root, destination)
            targets = pending_targets(destination, {'11'})
            self.assertEqual(len(targets), 1)
            self.assertNotIn('source_record', targets[0]['entry'])

    def test_install_migration_retires_old_inputs_and_summary_is_generated(self):
        import contextlib
        import io
        import json
        from njd.canonical import migrate, install_migration, load_effective, main
        with tempfile.TemporaryDirectory() as td:
            root, _, _, _ = self.setup_repository(td)
            destination = Path(td) / 'new'
            migrate(root, destination)
            install_migration(root, destination)
            self.assertFalse((root / 'corrections.json').exists())
            self.assertFalse((root / 'reading_research.json').exists())
            self.assertEqual(load_effective(root)['entries'][0]['reading'], 'かくうじんじゃ')
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(main(['summary', '--data-dir', str(root)]), 0)
            self.assertEqual(json.loads(out.getvalue())['resolved'], 1)

    def test_installation_failure_restores_legacy_files_and_source_generation(self):
        from njd.canonical import migrate, install_migration
        with tempfile.TemporaryDirectory() as td:
            root, _, _, _ = self.setup_repository(td)
            destination = Path(td) / 'new'
            migrate(root, destination)
            before = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*.json')}
            rename = Path.rename
            def fail_retirement(path, target):
                if path == root / 'corrections.json':
                    raise OSError('injected retirement failure')
                return rename(path, target)
            with patch.object(Path, 'rename', fail_retirement):
                with self.assertRaises(OSError):
                    install_migration(root, destination)
            self.assertEqual(before, {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*.json')})

    def test_failed_rollback_keeps_backup_and_journal_for_explicit_recovery(self):
        from njd.canonical import migrate, recover, load_effective
        from njd.proposals import import_proposals
        with tempfile.TemporaryDirectory() as td:
            root, _, proposal, _ = self.setup_repository(td)
            (root / 'corrections.json').unlink()
            destination = Path(td) / 'new'
            migrate(root, destination)
            rename = Path.rename
            def fail_install_and_rollback(path, target):
                if path.parent.name.startswith('.canonical-stage-') and path.name in ('sources', 'previous'):
                    raise OSError('injected install/rollback failure')
                return rename(path, target)
            with patch.object(Path, 'rename', fail_install_and_rollback):
                with self.assertRaises(OSError):
                    import_proposals(destination, proposal, apply=True)
            self.assertTrue(any((p / 'previous').exists() for p in destination.glob('.canonical-stage-*')))
            self.assertTrue((destination / '.canonical-transaction.json').exists())
            recover(destination)
            self.assertEqual(load_effective(destination)['entries'][0]['reading'], '')

    def test_new_repository_cannot_ignore_judgments_without_metadata_templates(self):
        from njd.canonical import initialize, load_effective
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            initialize(root)
            fixture = build([row()])
            save_collection(root, 'example', fixture)
            path = root / 'sources/example.json'
            doc = load_dataset(path)
            entry = doc['entries'][0]
            entry['judgments']['decisions'] = dict(status='excluded', reason='資料の相違',
                expected_source_hash=entry['source_hash'])
            write_json(path, doc)
            with self.assertRaisesRegex(ValueError, 'adopted'):
                load_effective(root)
            entry.update(status='excluded', reason='資料の相違')
            write_json(path, doc)
            self.assertEqual(load_effective(root)['entries'][0]['status'], 'excluded')
            save_collection(root, 'example', fixture)
            self.assertIn('decisions', load_dataset(path)['entries'][0]['judgments'])

    def test_unknown_judgment_is_rejected_instead_of_silently_lost(self):
        from njd.canonical import migrate, load_effective
        with tempfile.TemporaryDirectory() as td:
            root, _, _, _ = self.setup_repository(td)
            destination = Path(td) / 'new'
            migrate(root, destination)
            path = destination / 'sources/example.json'
            doc = load_dataset(path)
            doc['entries'][0]['judgments']['typo_decision'] = dict(status='excluded')
            write_json(path, doc)
            with self.assertRaisesRegex(ValueError, 'judgment'):
                load_effective(destination)

    def test_complete_refetch_retires_missing_corrected_and_researched_record(self):
        from njd.canonical import migrate, load_effective, research_summary
        with tempfile.TemporaryDirectory() as td:
            root, original, _, _ = self.setup_repository(td)
            destination = Path(td) / 'new'
            migrate(root, destination)
            path = destination / 'sources/example.json'
            prior = load_dataset(path)['entries'][0]
            save_collection(destination, 'example', build([]))
            current = load_effective(destination)
            self.assertEqual(current['entries'], [])
            self.assertEqual(render(current, 'mozc').content, b'')
            archives = load_dataset(path)['source_metadata']['retired_records']
            archived = next(item['record'] for item in archives if item['kind'] == 'entries')
            self.assertEqual(archived, prior)
            self.assertEqual(research_summary(destination)['targets'], 1)
            self.assertEqual(research_summary(destination)['retired'], 1)
            save_collection(destination, 'example', build([]))
            self.assertEqual(load_dataset(path)['source_metadata']['retired_records'], archives)
            save_collection(destination, 'example', original)
            returned = load_dataset(path)['entries'][0]
            self.assertEqual(returned['reading'], 'かくうじんじゃ')
            self.assertEqual(returned['judgments'], prior['judgments'])
            self.assertEqual(research_summary(destination)['targets'], 1)

    def test_partial_refetch_rejects_missing_corrected_record_and_keeps_old_bytes(self):
        from njd.canonical import migrate
        with tempfile.TemporaryDirectory() as td:
            root, _, _, _ = self.setup_repository(td)
            destination = Path(td) / 'new'
            migrate(root, destination)
            path = destination / 'sources/example.json'
            before = path.read_bytes()
            incoming = build([])
            incoming['collection']['traversal_complete'] = False
            with self.assertRaises(ValueError):
                save_collection(destination, 'example', incoming)
            self.assertEqual(path.read_bytes(), before)

    def test_prefecture_counts_include_all_sources_in_the_same_prefecture(self):
        from njd.canonical import initialize
        from njd.nationwide import load_states
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            initialize(root)
            save_collection(root, 'example', build([row()]))
            other = build([row(source_id='other', name='別架空神社', reading_raw='ベツカクウジンジャ')])
            other['collection']['source_key'] = 'other'
            other['facilities'][0]['source_key'] = 'other'
            save_collection(root, 'other', other)
            self.assertEqual(load_states(root)['11']['facilities'], 2)
            self.assertEqual(load_states(root)['11']['facility_records'], 2)

    def test_stale_split_archives_disappearing_child_and_its_manual_judgment(self):
        from njd.canonical import migrate, load_effective
        from njd.reviews import apply_reviews
        from test_reviews import decision
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'old'
            fixture = build([row(name='架空神社 別神社', reading_raw='かくうじんじゃ べつじんじゃ')])
            save_collection(root, 'example', fixture)
            outputs = [dict(surface=s, reading=r, basis='agency_component',
                reading_url=fixture['facilities'][0]['listing_url'])
                for s, r in [('架空神社', 'かくうじんじゃ'), ('別神社', 'べつじんじゃ')]]
            review = decision(fixture, outputs, split=True, excluded_name_prefix='', excluded_reading_prefix='')
            write_json(root / 'reviews.json', review)
            child = apply_reviews(fixture, review)['entries'][1]
            manual = dict(expected_source_hash=child['source_hash'], status='excluded', reason='既存の除外')
            write_json(root / 'decisions.json', {child['id']: manual})
            destination = Path(td) / 'new'
            migrate(root, destination)
            changed = build([row(name='架空神社 別神社', reading_raw='かくうじんじゃ べつじんじゃ', address='架空市乙町2')])
            save_collection(destination, 'example', changed)
            current = load_effective(destination)
            self.assertEqual(len(current['entries']), 1)
            self.assertEqual(current['entries'][0]['status'], 'pending')
            archives = load_dataset(destination / 'sources/example.json')['source_metadata']['retired_records']
            retired = next(a['record'] for a in archives if a['record']['id'] == child['id'])
            self.assertEqual(retired['judgments']['decisions'], manual)
            save_collection(destination, 'example', fixture)
            returned = next(e for e in load_effective(destination)['entries'] if e['id'] == child['id'])
            self.assertEqual(returned['status'], 'excluded')
            self.assertEqual(returned['reason'], '既存の除外')

    def test_research_must_be_bound_to_owning_entry_and_facility(self):
        from njd.canonical import migrate, load_effective
        for field in ('entry_id', 'facility_id'):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as td:
                root, _, _, _ = self.setup_repository(td)
                destination = Path(td) / 'new'
                migrate(root, destination)
                path = destination / 'sources/example.json'
                doc = load_dataset(path)
                doc['entries'][0]['research'][field] = 'nonexistent'
                write_json(path, doc)
                with self.assertRaisesRegex(ValueError, 'research'):
                    load_effective(destination)

    def test_identity_links_require_known_target_and_matching_observation(self):
        from njd.canonical import migrate
        for change in ('target', 'hash'):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as td:
                root, fixture, _, _ = self.setup_repository(td)
                facility = fixture['facilities'][0]
                link = dict(facility_id=facility['id'], reason='過去の対応', expected_source_hash=facility['source_hash'])
                if change == 'target':
                    link['facility_id'] = 'nonexistent'
                else:
                    link['expected_source_hash'] = '0' * 64
                write_json(root / 'identities.json', {'example': {facility['id']: link}})
                with self.assertRaisesRegex(ValueError, 'identity'):
                    migrate(root, Path(td) / 'new')
