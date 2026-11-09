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
            self.assertFalse((out/'national/atok.txt').exists())
            r=json.loads((out/'report.json').read_text())
            self.assertEqual(r['format_outputs']['atok']['status'],'blocked')
            # Reusing an output location must not leave stale files looking current.
            self.assertEqual(self.run_cli('--workspace',td,'build','--formats','json'),0)
            self.assertFalse((out/'national/mozc.txt').exists())
            self.assertTrue((out/'national/json.json').exists())
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
