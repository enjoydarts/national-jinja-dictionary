import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from test_records import build,row
from njd.nationwide import save_collection
from njd.release import create_release

class ReleaseTest(unittest.TestCase):
    def test_release_builds_from_versioned_data_without_network(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td); data=base/'data';out=base/'dist'
            save_collection(data,'example',build([row()]))
            with patch('njd.http.request',side_effect=AssertionError('release must stay offline')):
                result=create_release(data,out,'v0.2.0','a'*40)
            with zipfile.ZipFile(result['archive']) as z:
                self.assertIn('national/mozc.txt',z.namelist())
                self.assertEqual(len(z.read('national/mozc.txt').splitlines()),1)
                source=json.loads(z.read('SOURCE.json'))
                self.assertEqual(source['source_commit'],'a'*40)
                self.assertIn('sources/example.json',source['data_files'])
                report=json.loads(z.read('report.json'))
                self.assertEqual(report['format_outputs']['atok']['status'],'blocked')
                self.assertEqual(json.loads(z.read('national/json.json'))['entries'][0]['reading'],'かくうじんじゃ')
    def test_release_is_byte_reproducible_and_uses_updated_canonical(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td);data=base/'data';out=base/'dist'
            save_collection(data,'example',build([row()]))
            first=Path(create_release(data,out,'v0.2.0','a'*40)['archive']).read_bytes()
            again=Path(create_release(data,out,'v0.2.0','a'*40)['archive']).read_bytes()
            self.assertEqual(first,again)
            save_collection(data,'example',build([row(),row(source_id='2',name='別架空神社',reading_raw='ベツカクウジンジャ')]))
            path=create_release(data,out,'v0.2.0','b'*40)['archive']
            with zipfile.ZipFile(path) as z:self.assertEqual(len(z.read('national/mozc.txt').splitlines()),2)
    def test_invalid_canonical_blocks_release(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td);data=base/'data';save_collection(data,'example',build([row()]))
            p=data/'sources/example.json';d=json.loads(p.read_text());d['entries'][0]['reading']='うそ';p.write_text(json.dumps(d))
            with self.assertRaises(ValueError):create_release(data,base/'dist','v0.2.0','a'*40)
    def test_version_cannot_escape_release_directory(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError):create_release(Path(td),Path(td)/'out','../bad','a'*40)

    def test_tag_verification_rejects_same_named_branch_with_other_commit(self):
        import subprocess
        from njd.release import require_matching_tag
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            def git(*args):
                return subprocess.run(['git','-c','user.name=Fixture','-c','user.email=fixture@example.invalid','-c','commit.gpgsign=false',*args],cwd=root,check=True,capture_output=True,text=True).stdout.strip()
            git('init','-b','main');git('commit','--allow-empty','-m','A');git('tag','v0.2.0')
            git('commit','--allow-empty','-m','B');git('branch','v0.2.0')
            with self.assertRaises(ValueError):require_matching_tag(root,'v0.2.0')
            git('checkout','--detach','refs/tags/v0.2.0')
            self.assertEqual(require_matching_tag(root,'v0.2.0'),git('rev-parse','HEAD'))

    def test_release_includes_actionable_review_lists_and_input_evidence(self):
        from njd.storage import write_json
        with tempfile.TemporaryDirectory() as td:
            base=Path(td);data=base/'data'
            save_collection(data,'example',build([row(reading_raw='')]))
            catalog={'schema_version':1,'prefectures':[]}
            corrections={'schema_version':1,'entries':{}}
            write_json(data/'source_catalog.json',catalog);write_json(data/'corrections.json',corrections)
            result=create_release(data,base/'out','v0.2.0','a'*40)
            with zipfile.ZipFile(result['archive']) as z:
                pending=json.loads(z.read('pending.json'))
                self.assertEqual(pending[0]['facility']['address'],'架空市乙町1')
                self.assertEqual(pending[0]['entry']['reading_raw'],'')
                self.assertTrue(pending[0]['entry']['listing_url'])
                self.assertEqual(json.loads(z.read('source_catalog.json')),catalog)
                self.assertEqual(json.loads(z.read('corrections.json')),corrections)
                self.assertIn('source_catalog.json',json.loads(z.read('SOURCE.json'))['data_files'])
