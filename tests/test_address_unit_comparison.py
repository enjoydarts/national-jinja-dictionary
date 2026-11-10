"""Address numeral comparison never rewrites names, readings or stored addresses."""
import unittest
from test_records import build,row
from njd.corrections import _reference_matches


class AddressUnitComparisonTests(unittest.TestCase):
    def matches(self,agency,reference):
        d=build([row(name='架空神社',address=agency,reading_raw='')])
        return _reference_matches(dict(name_raw='架空神社',address_raw='埼玉県'+reference),d['facilities'][0],d['entries'][0],{})

    def test_explicit_units_agree_in_both_directions(self):
        for a,b in [('架空市北12条東1丁目1番10号','架空市北十二条東一丁目一番十号'),
                    ('架空市甲町二丁目18番6号','架空市甲町2丁目18番6号'),
                    ('架空市甲町第一号1670番地','架空市甲町第1号1670番地')]:
            with self.subTest(a=a,b=b):
                self.assertTrue(self.matches(a,b));self.assertTrue(self.matches(b,a))

    def test_other_parcels_names_and_nonstandard_numerals_never_match(self):
        for a,b in [('架空市北12条東1丁目1番10号','架空市北十二条東一丁目一番11号'),
                    ('架空市一ノ宮1','架空市1ノ宮1'),
                    ('架空市甲町2丁目1','架空市甲町百二丁目1'),
                    ('架空市甲町23丁目1','架空市甲町二三丁目1'),
                    ('架空市甲町10丁目1','架空市甲町零十丁目1'),
                    ('架空市甲町10丁目1','架空市甲町十〇丁目1'),
                    ('架空市甲町12丁目1','架空市甲町1二丁目1'),
                    ('架空市甲町110丁目1','架空市甲町1十丁目1'),
                    ('架空市甲町1丁目1','架空市甲町壱丁目1')]:
            with self.subTest(a=a,b=b):self.assertFalse(self.matches(a,b))

    def test_existing_locality_with_numeric_word_keeps_its_original_scope(self):
        for town in ['五番領','八条町','小一条町','五条','後三条町']:
            with self.subTest(town=town):
                self.assertTrue(self.matches('架空市'+town,'架空市'+town+'17'))
        self.assertFalse(self.matches('架空市甲町一番地','架空市甲町一番地1'))
