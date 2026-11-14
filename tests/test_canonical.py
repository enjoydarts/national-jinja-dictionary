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
            before = _effective(root)
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
