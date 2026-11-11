"""Unicode output contract, independent of actual ATOK dictionary installation."""
import copy
import unittest
from njd.atok import check_atok, row_problem
from njd.exporters import render
from test_atok import words


class AtokUnicodeTest(unittest.TestCase):
    def test_preserves_non_bmp_and_variant_characters_with_big_endian_bom(self):
        data=words('しけんじんじゃ','𠮷神社');before=copy.deepcopy(data)
        out=render(data,'atok_unicode')
        # Literal byte prefix is independent of the encoder being tested.
        self.assertEqual(out.content[:6],b'\xfe\xff\x00!\x00!')
        self.assertEqual(out.content[2:].decode('utf-16-be'),
            '!!ATOK_TANGO_TEXT_HEADER_1\r\nしけんじんじゃ\t𠮷神社\t固有地名\r\n')
        self.assertEqual(out.content[-4:],b'\x00\r\x00\n')
        self.assertEqual(out.rows,1)
        self.assertEqual(out.deduplicated,1)
        self.assertEqual(out.summary()['actual_ime_import'],'not_tested')
        self.assertEqual(check_atok(out.content,unicode=True),[])
        self.assertEqual(render(data,'atok').rows,0)
        self.assertEqual(data,before)

    def test_counts_supplementary_characters_as_two_units_without_truncation(self):
        self.assertIsNone(row_problem(('あ'*32,'𠮷'*50,'固有地名'),unicode=True))
        self.assertIn('100',row_problem(('あ','𠮷'*51,'固有地名'),unicode=True))
        out=render(words('あ','𠮷'*51),'atok_unicode')
        self.assertEqual(out.rows,0)
        self.assertTrue(any('100' in e['reason'] for e in out.exclusions))
        self.assertEqual(check_atok(out.content,unicode=True),[])

    def test_does_not_relax_reading_or_control_character_checks(self):
        for row in [('ア','𠮷神社','固有地名'),('あ','神\t社','固有地名'),
                    ('あ','神\x00社','固有地名'),('あ','神\u2028社','固有地名')]:
            with self.subTest(row=row):self.assertTrue(row_problem(row,unicode=True))

    def test_rejects_other_byte_profiles_malformed_utf16_and_injected_rows(self):
        text='!!ATOK_TANGO_TEXT_HEADER_1\r\nあ\t神社\t固有地名\r\n'
        for raw in [text.encode('utf-16-be'),b'\xff\xfe'+text.encode('utf-16-le'),
                    b'\xfe\xff'+text.encode('utf-16-be')+b'\x00',
                    b'\xfe\xff'+text.replace('\r\n','\n').encode('utf-16-be'),
                    b'\xfe\xff'+text.replace('神社','神\x00社').encode('utf-16-be'),
                    text.encode('shift_jis')]:
            with self.subTest(raw=raw):self.assertTrue(check_atok(raw,unicode=True))
