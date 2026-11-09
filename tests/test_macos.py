"""Synthetic records for the versioned Apple additional-dictionary profile."""
import copy
import csv
import io
import unittest
from test_records import build,row
from njd.exporters import render
from njd.macos import check_macos,encode_row

class MacOSExportTest(unittest.TestCase):
    def test_direct_export_deduplicates_without_losing_facilities(self):
        d=build([row(),row(source_id='2',address='架空市乙町2'),row(source_id='3',reading_raw='')]);before=copy.deepcopy(d)
        out=render(d,'macos')
        self.assertEqual(out.rows,1);self.assertEqual(out.deduplicated,1)
        self.assertEqual(out.content,'"かくうじんじゃ","架空神社","その他の固有名詞"\n'.encode())
        self.assertEqual(check_macos(out.content),[]);self.assertEqual(len(out.exclusions),1)
        self.assertEqual(d,before)
    def test_quotes_preserve_comma_space_double_quote_and_variant_characters(self):
        name='𠮷神社, "試驗 社"';out=render(build([row(name=name)]),'macos')
        self.assertFalse(out.content.startswith(b'\xef\xbb\xbf'))
        self.assertEqual(list(csv.reader(io.StringIO(out.content.decode()))),[['かくうじんじゃ',name,'その他の固有名詞']])
        self.assertEqual(check_macos(out.content),[])
    def test_reading_32_limit_and_conservative_utf16_surface_limit(self):
        for changes in [dict(reading_raw='あ'*33),dict(name='社'*65),dict(name='𠮷'*33)]:
            with self.subTest(changes=changes):
                d=build([row(**changes)]);out=render(d,'macos')
                self.assertEqual(out.rows,0);self.assertEqual(len(d['entries']),1)
                self.assertTrue(out.exclusions);self.assertIn('UTF-16',out.exclusions[0]['reason'])
        d=build([row(name='社'*64,reading_raw='あ'*32)])
        self.assertEqual(render(d,'macos').rows,1)
    def test_escaped_line_length_is_checked_without_truncating(self):
        d=build([row(name='"'*64,reading_raw='あ'*32)])
        out=render(d,'macos');self.assertEqual(out.rows,0)
        self.assertIn('127',out.exclusions[0]['reason']);self.assertEqual(d['entries'][0]['surface'],'"'*64)
    def test_checker_rejects_bad_encoding_columns_pos_duplicates_and_controls(self):
        good=encode_row(('かな','名','その他の固有名詞')).encode()
        for content in [b'\xff',b'\xef\xbb\xbf'+good,good.replace(b'\n',b'\r\n'),good+good,
                        b'"one","two"\n','"かな","名","固有名詞"\n'.encode(),
                        '"かな","名\n社","その他の固有名詞"\n'.encode(),
                        '"仮名","名","その他の固有名詞"\n'.encode()]:
            with self.subTest(content=content):self.assertTrue(check_macos(content))
    def test_same_input_produces_identical_file(self):
        d=build([row(name='試驗神社'),row(source_id='2',name='別架空神社')])
        self.assertEqual(render(d,'macos').content,render(d,'macos').content)
