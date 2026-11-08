import unittest
from njd.records import build_dataset
from njd.validation import validate, eligible


def row(**changes):
    r=dict(name='架空神社',reading_raw='カクウジンジャ',address='架空市乙町1',
        url='https://agency.example.invalid/shrines/1',page_hash='a'*64,
        fetched_at='2026-11-08T00:00:00+00:00',locator='table row 1',
        evidence='same source row: name, kana and address',source_id='1')
    r.update(changes);return r

def build(rows): return build_dataset('example','11','埼玉県','架空県神社庁',rows)

class RecordTest(unittest.TestCase):
    def test_shared_records_have_valid_sources(self):
        d=build([row()]); self.assertEqual(validate(d),[])
        self.assertEqual(d['entries'][0]['reading'],'かくうじんじゃ')
        self.assertEqual(d['collection']['source_key'],'example')
    def test_native_id_survives_renaming_but_hash_changes(self):
        a=build([row()]);b=build([row(name='改称神社',address='架空市甲町2')])
        self.assertEqual(a['facilities'][0]['id'],b['facilities'][0]['id'])
        self.assertNotEqual(a['entries'][0]['source_hash'],b['entries'][0]['source_hash'])
    def test_same_name_different_facilities_not_merged(self):
        d=build([row(source_id='1'),row(source_id='2',address='架空市乙町2')])
        self.assertEqual(len(d['facilities']),2)
    def test_duplicate_source_occurrences_keep_provenance(self):
        d=build([row(),row(url='https://agency.example.invalid/area')])
        self.assertEqual(len(d['facilities']),1)
        self.assertEqual(len(d['facilities'][0]['listing_occurrences']),2)
    def test_conflicting_native_id_readings_quarantined(self):
        d=build([row(),row(reading_raw='ベツヨミ')])
        self.assertEqual(len(d['facilities']),1)
        self.assertEqual(eligible(d),[])
        self.assertEqual(len(d['facilities'][0]['source_conflicts']),1)
    def test_missing_reading_retained_but_not_eligible(self):
        d=build([row(reading_raw='')]);self.assertEqual(validate(d),[])
        self.assertEqual(d['facilities'][0]['status'],'verified')
        self.assertEqual(d['entries'][0]['status'],'pending')
    def test_municipality_derived_from_explicit_address(self):
        d=build([row(address='埼玉県さいたま市大宮区高鼻町1')])
        self.assertEqual(d['facilities'][0]['municipality'],'さいたま市大宮区')

    def test_missing_address_is_explicit_review_record_not_exportable(self):
        d=build([row(address='')])
        self.assertEqual(eligible(d),[])
        self.assertTrue(validate(d))
        self.assertTrue(all(p.get('severity')=='review' for p in validate(d)))

    def test_source_name_with_control_characters_is_preserved_for_review(self):
        d=build([row(name='架空\n神社')])
        self.assertEqual(d['facilities'][0]['name_raw'],'架空\n神社')
        self.assertEqual(d['entries'][0]['status'],'pending')
        self.assertEqual(eligible(d),[])
        self.assertTrue(all(p.get('severity')=='review' for p in validate(d)))
