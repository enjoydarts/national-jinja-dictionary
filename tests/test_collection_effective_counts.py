"""Recollection counts must describe the same evidence/judgments as generation."""
from pathlib import Path
import tempfile
import unittest

from test_records import build,row
from test_corrections import correction
from test_location_pipeline import fixture
from njd.__main__ import _effective
from njd.nationwide import run_collections,save_collection
from njd.report import _counts
from njd.storage import load_dataset,write_json


class CollectionEffectiveCountsTests(unittest.TestCase):
    def run_source(self,root,raw):
        spec={'example':dict(code='11',collect=lambda client,limit=None:raw)}
        return run_collections(root,spec,['example'],cache_dir=root.parent/'cache')['11']

    def assert_same_counts(self,state,root):
        expected=_counts(_effective(root, legacy=True))
        for key in ('facilities','facility_records','source_alias_records','verified_facilities','dictionary_rows'):
            self.assertEqual(state[key],expected[key],key)
        self.assertEqual(state['pending_entries'],expected['entry_status_counts'].get('pending',0))

    def test_missing_reading_supplement_and_manifest_metadata_survive_recollection(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/'data';raw=build([row(reading_raw='')])
            write_json(root/'corrections.json',correction(raw,dict(reading='かくうじんじゃ')))
            write_json(root/'manifest.json',dict(counts_basis='evidence and judgments',custom_metadata='keep',prefectures={'12':dict(reason='unrelated source failure',status='failed')}))
            before=(root/'corrections.json').read_bytes();state=self.run_source(root,raw)
            self.assertEqual(state['verified_facilities'],1)
            self.assert_same_counts(state,root)
            self.assertEqual((root/'corrections.json').read_bytes(),before)
            manifest=load_dataset(root/'manifest.json')
            self.assertEqual(manifest['counts_basis'],'evidence and judgments')
            self.assertEqual(manifest['custom_metadata'],'keep')
            self.assertEqual(manifest['prefectures']['12']['reason'],'unrelated source failure')

    def test_user_exclusion_is_included_in_counts_without_editing_source(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/'data';raw=build([row()]);e=raw['entries'][0]
            write_json(root/'decisions.json',{e['id']:dict(expected_source_hash=e['source_hash'],status='excluded',reason='synthetic explicit exclusion')})
            state=self.run_source(root,raw)
            self.assertEqual(state['verified_facilities'],0)
            self.assert_same_counts(state,root)
            self.assertEqual(load_dataset(root/'sources/example.json')['entries'][0]['status'],'verified')

    def test_stale_decision_cannot_keep_new_source_reading_in_verified_count(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/'data';raw=build([row()]);e=raw['entries'][0]
            write_json(root/'decisions.json',{e['id']:dict(expected_source_hash='b'*64,status='verified',reason='outdated source judgment')})
            state=self.run_source(root,raw)
            self.assertEqual(state['verified_facilities'],0)
            self.assert_same_counts(state,root)

    def test_location_then_reading_and_failed_source_preserve_effective_counts(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/'data';raw,locations,readings=fixture(root)
            write_json(root/'corrections.json',readings)
            state=self.run_source(root,raw)
            self.assertEqual(state['verified_facilities'],1)
            self.assert_same_counts(state,root)
            def fail(client,limit=None):raise ValueError('synthetic source failure')
            states=run_collections(root,{'example':dict(code='11',collect=fail)},['example'],cache_dir=root.parent/'cache')
            self.assertEqual(states['11']['status'],'failed_using_previous')
            self.assert_same_counts(states['11'],root)

    def test_invalid_overlay_cannot_replace_previous_source_before_counting_fails(self):
        for existing in (False,True):
            with self.subTest(existing=existing),tempfile.TemporaryDirectory() as td:
                root=Path(td)/'data';old=build([row()])
                if existing:save_collection(root,'example',old)
                path=root/'sources/example.json';before=path.read_bytes() if existing else None
                write_json(root/'corrections.json',dict(schema_version=999,entries={}))
                incoming=build([row(),row(source_id='2',address='架空市乙町2')])
                state=self.run_source(root,incoming)
                self.assertEqual(state['status'],'failed_using_previous' if existing else 'failed')
                self.assertEqual(path.read_bytes() if path.exists() else None,before)
