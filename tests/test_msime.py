"""Artificial-word tests; file generation is distinct from Windows import."""
import copy
import unittest
from njd.exporters import render
from njd.msime import check_msime, row_problem
from test_atok import words


class MsimeTest(unittest.TestCase):
    def test_native_header_unicode_bytes_and_dedup_preserve_variants(self):
        data=words('しけんじんじゃ','𠮷神社');before=copy.deepcopy(data)
        out=render(data,'msime')
        self.assertEqual(out.content[:6],b'\xff\xfe!\x00M\x00')
        self.assertEqual(out.content[2:].decode('utf-16-le'),
            '!Microsoft IME Dictionary Tool\r\n!Version:\r\n!Format:WORDLIST\r\nしけんじんじゃ\t𠮷神社\t固有名詞\r\n')
        self.assertEqual(out.rows,1);self.assertEqual(out.deduplicated,1)
        self.assertEqual(len(out.exclusions),1)
        self.assertEqual(out.summary()['actual_ime_import'],'not_tested')
        self.assertEqual(check_msime(out.content),[])
        self.assertEqual(data,before)

    def test_60_unit_bounds_do_not_count_supplementary_as_single_characters(self):
        self.assertIsNone(row_problem(('あ'*60,'𠮷'*30,'固有名詞')))
        self.assertIn('60',row_problem(('あ'*61,'神社','固有名詞')))
        self.assertIn('60',row_problem(('あ','𠮷'*31,'固有名詞')))
        out=render(words('あ','𠮷'*31),'msime')
        self.assertEqual(out.rows,0)
        self.assertTrue(any('60' in e['reason'] for e in out.exclusions))
        self.assertEqual(check_msime(out.content),[])

    def test_control_characters_invalid_reading_and_wrong_pos_are_rejected(self):
        for row in [('ア','神社','固有名詞'),('あ','神\t社','固有名詞'),
                    ('あ','神\x00社','固有名詞'),('あ','神\u2028社','固有名詞'),
                    ('あ','神社','地名'),('あ','神社','固有名詞','コメント')]:
            with self.subTest(row=row):self.assertTrue(row_problem(row))

    def test_checker_rejects_other_encodings_headers_injection_and_duplicate_rows(self):
        text='!Microsoft IME Dictionary Tool\r\n!Version:\r\n!Format:WORDLIST\r\nあ\t神社\t固有名詞\r\n'
        changes=[text.replace('WORDLIST','PROOFLIST'),text.replace('!Version:\r\n',''),
                 text.replace('!Version:','!Version:1'),text.replace('\r\n','\n'),
                 text.replace('神社','神\x00社'),text+'あ\t神社\t固有名詞\r\n',
                 text.replace('固有名詞','名詞'),text.replace('固有名詞\r\n','固有名詞\tメモ\r\n')]
        for raw in [text.encode('utf-8'),text.encode('utf-16-le'),b'\xfe\xff'+text.encode('utf-16-be'),
                    b'\xff\xfe'+text.encode('utf-16-le')+b'\x00']+[b'\xff\xfe'+s.encode('utf-16-le') for s in changes]:
            with self.subTest(raw=raw):self.assertTrue(check_msime(raw))
