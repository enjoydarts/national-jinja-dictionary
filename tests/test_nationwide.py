import tempfile
import unittest
from pathlib import Path
from test_records import build,row
from njd.nationwide import save_collection, merge_collections, run_collections
from njd.storage import load_dataset

class NationwideTest(unittest.TestCase):
    def test_merging_preserves_other_prefectures_and_source_records(self):
        from njd.records import build_dataset
        with tempfile.TemporaryDirectory() as td:
            work=Path(td)
            a=build([row()])
            b=build_dataset('other','12','千葉県','別の神社庁',[row(source_id='2')])
            save_collection(work,'example',a);save_collection(work,'other',b)
            d=merge_collections(work)
            self.assertEqual(len(d['facilities']),2)
            self.assertEqual(len(d['collection']['sources']),2)
            self.assertEqual(len(d['collection']['prefecture_states']),47)
            self.assertEqual({f['prefecture_code'] for f in d['facilities']},{'11','12'})
            save_collection(work,'example',a)
            self.assertEqual(len(merge_collections(work)['facilities']),2)
    def test_failed_source_keeps_previous_collection_and_continues(self):
        with tempfile.TemporaryDirectory() as td:
            work=Path(td);save_collection(work,'example',build([row()]))
            def fail(client,limit=None): raise ValueError('source changed')
            registry={'example':dict(code='11',prefecture='埼玉県',agency='架空',collect=fail)}
            state=run_collections(work,registry,['example'],offline=True)
            self.assertEqual(state['11']['status'],'failed_using_previous')
            self.assertEqual(len(merge_collections(work)['facilities']),1)
    def test_merge_is_deterministic(self):
        with tempfile.TemporaryDirectory() as td:
            work=Path(td);save_collection(work,'example',build([row()]))
            from njd.storage import json_bytes
            before=json_bytes(merge_collections(work))
            self.assertEqual(before,json_bytes(merge_collections(work)))
    def test_unsafe_keys_and_cross_source_identity_are_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError): save_collection(Path(td),'../unsafe',build([row()]))
            with self.assertRaises(ValueError): save_collection(Path(td),'different',build([row()]))

    def test_private_exception_details_never_enter_public_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td);work=base/'data';cache=base/'private-cache'
            secret_path='/Users/private-person/private-vault/cache/request.lock'
            def fail(client,limit=None):raise PermissionError(13,'Permission denied',secret_path)
            registry={'example':dict(code='11',prefecture='埼玉県',agency='架空',collect=fail)}
            state=run_collections(work,registry,['example'],cache_dir=cache)
            self.assertNotIn(secret_path,(work/'manifest.json').read_text())
            self.assertIn('local_io_error',state['11']['reason'])
            self.assertIn(secret_path,(cache/'diagnostics/example.json').read_text())

    def test_local_work_paths_cannot_be_saved_as_canonical_metadata(self):
        with tempfile.TemporaryDirectory() as td:
            d=build([row()]);d['collection']['operator_note']="Permission error: '/Users/private-person/cache/file'"
            with self.assertRaises(ValueError):save_collection(Path(td),'example',d)
            self.assertFalse((Path(td)/'sources/example.json').exists())
