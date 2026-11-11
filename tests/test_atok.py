"""Artificial words only; byte-level ATOK text generation, not product import."""
import copy
import unittest
from njd.atok import check_atok, row_problem
from njd.exporters import render
from njd.adapters.gunma import parse
from test_core import HTML, dataset


def words(reading, surface):
    html=HTML.replace('試驗神社',surface).replace('ｼｹﾝｼﾞﾝｼﾞｬ',reading)
    return parse(html,'2026-11-08','a'*64)


class AtokTest(unittest.TestCase):
    def test_direct_generation_has_header_crlf_and_deduplicates_facilities(self):
        data=dataset();before=copy.deepcopy(data)
        out=render(data,'atok')
        expected='!!ATOK_TANGO_TEXT_HEADER_1\r\nしけんじんじゃ\t試驗神社\t固有地名\r\n'
        self.assertEqual(out.content,expected.encode('shift_jis'))
        self.assertEqual(out.rows,1)
        self.assertEqual(out.deduplicated,1)
        self.assertEqual(len(out.exclusions),1)
        self.assertEqual(out.summary()['actual_ime_import'],'not_tested')
        self.assertEqual(data,before)
        self.assertEqual(check_atok(out.content),[])

    def test_unrepresentable_variant_is_excluded_without_replacement(self):
        for surface in ['𠮷神社','髙神社','神社①','神社〜','神社¥']:
            with self.subTest(surface=surface):
                data=words('しけんじんじゃ',surface)
                out=render(data,'atok')
                self.assertEqual(out.rows,0)
                self.assertEqual(len(out.exclusions),3)
                self.assertTrue(any('Shift JIS' in e['reason'] for e in out.exclusions))
                self.assertEqual(data['entries'][0]['surface'],surface)

    def test_documented_length_bounds_are_not_silently_truncated(self):
        self.assertEqual(check_atok(b'!!ATOK_TANGO_TEXT_HEADER_1\r\n'),[])
        self.assertIsNone(row_problem(('あ'*32,'社'*100,'固有地名')))
        self.assertIn('32',row_problem(('あ'*33,'神社','固有地名')))
        self.assertIn('100',row_problem(('あ','社'*101,'固有地名')))
        out=render(words('あ'*33,'神社'),'atok')
        self.assertEqual(out.rows,0)
        self.assertTrue(any('32' in x['reason'] for x in out.exclusions))

    def test_fields_cannot_inject_rows_or_invalid_readings(self):
        for row in [('あ','神\t社','固有地名'),('あ','神\n社','固有地名'),
                    ('あ','神\x00社','固有地名'),('ア','神社','固有地名'),
                    ('ーあ','神社','固有地名'),('あ','神社','名詞'),
                    ('あ','神社\u2028社','固有地名')]:
            with self.subTest(row=row):self.assertTrue(row_problem(row))

    def test_checker_rejects_encoding_header_columns_pos_duplicates_and_endings(self):
        header='!!ATOK_TANGO_TEXT_HEADER_1\r\n'
        line='かな\t神社\t固有地名\r\n'
        bad=[b'\xff',line.encode('shift_jis'),(header+line).encode('utf-8'),
             (header+line).replace('\r\n','\n').encode('shift_jis'),
             (header+line).replace('固有地名','名詞').encode('shift_jis'),
             (header+line+line).encode('shift_jis'),
             (header+line).rstrip('\r\n').encode('shift_jis'),
             (header+'かな\t神社\t固有地名\tメモ\r\n').encode('shift_jis'),
             (header+'かな\t神\x00社\t固有地名\r\n').encode('shift_jis')]
        for raw in bad:
            with self.subTest(raw=raw):self.assertTrue(check_atok(raw))
