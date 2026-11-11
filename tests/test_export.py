import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from test_core import dataset
from njd.exporters import render, check_mozc, FORMATS
from njd.report import report, samples

class ExportTest(unittest.TestCase):
    def test_mozc_deduplicates_lines_keeps_facilities(self):
        d=dataset(); output=render(d,'mozc')
        self.assertEqual(output.rows,1)
        self.assertEqual(output.content,'しけんじんじゃ\t試驗神社\t固有名詞\n'.encode())
        self.assertEqual(len(d['facilities']),3)
        self.assertEqual(check_mozc(output.content),[])
    def test_bad_source_excluded_with_reason(self):
        d=dataset(); d['entries'][0]['reading_url']=''
        out=render(d,'mozc'); self.assertEqual(out.rows,1)
        self.assertTrue(out.exclusions)
    def test_length_bytes_not_character_count(self):
        d=dataset(); e=d['entries'][0]; e['reading']=e['reading_raw']='あ'*101
        e['source_hash']=hashlib.sha256('\0'.join((e['name_raw'],e['reading_raw'],d['facilities'][0]['address'])).encode()).hexdigest()
        d['facilities'][0]['source_hash']=e['source_hash']
        out=render(d,'mozc')
        self.assertEqual(out.rows,1)
        self.assertTrue(any('300' in x['reason'] for x in out.exclusions))
    def test_blocked_formats_never_emit_speculative_files(self):
        from unittest.mock import patch
        with patch.dict(FORMATS,{'unconfirmed':dict(status='blocked',reason='missing product evidence')}):
            out=render(dataset(),'unconfirmed')
            self.assertIsNone(out.content)
            self.assertEqual(out.status,'blocked')
            self.assertTrue(out.reason)
    def test_management_json_csv_keep_pending_and_sources(self):
        d=dataset(); j=render(d,'json'); c=render(d,'csv')
        self.assertEqual(json.loads(j.content)['facilities'],d['facilities'])
        self.assertIn('pending',c.content.decode())
        self.assertIn('reading_url',c.content.decode())
    def test_deterministic_and_input_not_mutated(self):
        d=dataset(); before=copy.deepcopy(d)
        for name in FORMATS:
            self.assertEqual(render(d,name).content,render(d,name).content)
        self.assertEqual(d,before)
    def test_format_checker(self):
        for content in [b'bad',b'\xff', 'かな\t名\t名詞\n'.encode(), 'かな\t名\t固有名詞\nかな\t名\t固有名詞\n'.encode()]:
            self.assertTrue(check_mozc(content))
    def test_prefecture_report_distinguishes_counts(self):
        r=report(dataset(),{'mozc':render(dataset(),'mozc')})
        self.assertEqual(r['totals']['facilities'],3)
        self.assertEqual(r['totals']['verified_facilities'],2)
        self.assertEqual(r['totals']['dictionary_rows'],1)
        self.assertEqual(r['totals']['output_rows']['mozc'],1)
        self.assertEqual(len(r['prefectures']),47)
        self.assertEqual(r['prefectures'][0]['collection_status'],'not_collected')
    def test_samples_use_real_entries_only(self):
        d=dataset(); s=samples(d,maximum=5)
        self.assertTrue(s['entries'])
        self.assertTrue({e['id'] for e in s['entries']} <= {e['id'] for e in d['entries']})
        self.assertEqual(len({e['surface'] for e in s['entries']}),1)

    def test_prefecture_scope_does_not_repeat_unrelated_source_metadata(self):
        from njd.report import subset
        d=dataset();d['collection']['sources']={'gunma':{'prefecture_code':'10','source_rows_observed':3},'other':{'prefecture_code':'11','source_rows_observed':999}}
        s=subset(d,'10')
        self.assertEqual(set(s['collection']['sources']),{'gunma'})
        self.assertEqual(s['collection']['source_rows_observed'],3)
        self.assertEqual(len(d['collection']['sources']),2)
