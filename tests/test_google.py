"""Released-Google profile and the confirmed shared TSV subset."""
import unittest
from njd.exporters import render
from test_atok import words


class GoogleTest(unittest.TestCase):
    def test_google_and_mozc_preserve_the_confirmed_three_column_subset(self):
        data=words('しけんじんじゃ','𠮷神社')
        output=render(data,'google')
        self.assertEqual(output.content,'しけんじんじゃ\t𠮷神社\t固有名詞\n'.encode('utf-8'))
        self.assertEqual(output.content,render(data,'mozc').content)
        self.assertEqual(output.rows,1)
        self.assertEqual(output.deduplicated,1)
        self.assertEqual(len(output.exclusions),1)
        self.assertEqual(output.summary()['actual_ime_import'],'not_tested')

    def test_rejects_over_300_utf8_bytes_without_losing_the_canonical_word(self):
        for count,rows in [(75,1),(76,0)]:
            with self.subTest(count=count):
                data=words('あ','𠮷'*count)
                out=render(data,'google')
                self.assertEqual(out.rows,rows)
                self.assertEqual(data['entries'][0]['surface'],'𠮷'*count)
                if count==76:self.assertTrue(any('300' in e['reason'] for e in out.exclusions))
