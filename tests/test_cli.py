import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from test_core import dataset, HTML
from njd.__main__ import main
from njd.audit import audit_gunma
from njd.storage import write_json

class CliTest(unittest.TestCase):
    def run_cli(self,*args):
        with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()): return main(list(args))
    def test_reject_repository_workspace(self):
        with self.assertRaises(ValueError): self.run_cli('--workspace',str(Path(__file__).resolve().parents[1]),'report')
    def test_build_all_reports_blocked_and_only_requested_files(self):
        with tempfile.TemporaryDirectory() as td:
            write_json(Path(td)/'common.json',dataset())
            self.assertEqual(self.run_cli('--workspace',td,'build','--formats','all'),2)
            out=Path(td)/'generated'
            self.assertTrue((out/'national/mozc.txt').exists())
            self.assertTrue((out/'prefectures/10/mozc.txt').exists())
            self.assertTrue((out/'national/atok.txt').exists())
            self.assertFalse((out/'national/google.txt').exists())
            r=json.loads((out/'report.json').read_text())
            self.assertEqual(r['format_outputs']['atok']['status'],'generated')
            self.assertEqual(r['format_outputs']['google']['status'],'blocked')
            # Reusing an output location must not leave stale files looking current.
            self.assertEqual(self.run_cli('--workspace',td,'build','--formats','json'),0)
            self.assertFalse((out/'national/mozc.txt').exists())
            self.assertTrue((out/'national/json.json').exists())
    def test_samples_only_does_not_generate_full_dictionaries_and_reports_exclusions(self):
        with tempfile.TemporaryDirectory() as td:
            write_json(Path(td)/'common.json',dataset())
            self.assertEqual(self.run_cli('--workspace',td,'build','--samples-only','--formats','all'),2)
            out=Path(td)/'generated'
            self.assertFalse((out/'national').exists())
            self.assertFalse((out/'prefectures').exists())
            self.assertTrue((out/'samples/national/atok.txt').exists())
            self.assertFalse((out/'samples/national/google.txt').exists())
            self.assertFalse((out/'pending.json').exists())
            r=json.loads((out/'samples/national/report.json').read_text())
            self.assertEqual(r['output_scope'],'import_sample_only')
            self.assertEqual(r['format_outputs']['atok']['rows'],1)
            self.assertEqual(r['format_outputs']['google']['status'],'blocked')
            self.assertEqual(r['format_outputs']['atok']['actual_ime_import'],'not_tested')

    def test_samples_only_retains_per_format_unrepresentable_word_reasons(self):
        from njd.adapters.gunma import parse
        with tempfile.TemporaryDirectory() as td:
            d=parse(HTML.replace('試驗神社','𠮷神社'),'2026-11-08','a'*64)
            write_json(Path(td)/'common.json',d)
            self.assertEqual(self.run_cli('--workspace',td,'build','--samples-only','--formats','atok,mozc','--prefecture','10'),0)
            out=Path(td)/'generated'
            r=json.loads((out/'samples/prefectures/10/report.json').read_text())
            self.assertEqual(r['format_outputs']['atok']['rows'],0)
            self.assertEqual(r['format_outputs']['mozc']['rows'],1)
            self.assertTrue(any('Shift JIS' in e['reason'] for e in r['format_outputs']['atok']['exclusions']))
    def test_build_bytes_reproducible(self):
        with tempfile.TemporaryDirectory() as td:
            write_json(Path(td)/'common.json',dataset())
            args=('--workspace',td,'build','--formats','mozc,json,csv')
            self.assertEqual(self.run_cli(*args),0)
            before={p.relative_to(Path(td)/'generated'):p.read_bytes() for p in (Path(td)/'generated').rglob('*') if p.is_file()}
            self.assertEqual(self.run_cli(*args),0)
            after={p.relative_to(Path(td)/'generated'):p.read_bytes() for p in (Path(td)/'generated').rglob('*') if p.is_file()}
            self.assertEqual(before,after)
    def test_source_audit_checks_actual_rows(self):
        d=dataset()
        self.assertEqual(audit_gunma(d,HTML,'a'*64)['mismatches'],[])
        d['entries'][0]['reading_raw']='ﾍﾞﾂﾖﾐ'
        self.assertTrue(audit_gunma(d,HTML,'a'*64)['mismatches'])

    def test_audit_uses_repository_source_file_without_common_json(self):
        from unittest.mock import patch
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as td:
            base=Path(td);data=base/'data';out=base/'out'
            write_json(data/'sources/gunma.json',dataset())
            with patch('njd.__main__.Client') as client:
                client.return_value.fetch.return_value=SimpleNamespace(text=HTML,sha256='a'*64)
                self.assertEqual(self.run_cli('--data-dir',str(data),'--output-dir',str(out),'audit','--source','gunma'),0)
                self.assertTrue(client.call_args.kwargs['offline'])
            self.assertTrue((out/'source-audit.json').exists())
