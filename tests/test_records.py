import unittest
from njd.records import build_dataset,municipality_from_address
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

    def test_locality_city_character_does_not_extend_municipality(self):
        for address,prefecture,want in [
            ('福知山市市寺123-4','京都府','福知山市'),
            ('京都府京都市左京区静市市原町123-4','京都府','京都市左京区'),
            ('滋賀県東近江市市子殿町123-4','滋賀県','東近江市'),
            ('兵庫県丹波市市島町架空123-4','兵庫県','丹波市'),
            ('架空市市場123-4','架空県','架空市'),
        ]:
            with self.subTest(address=address):
                self.assertEqual(municipality_from_address(address,prefecture),want)

    def test_literal_double_city_names_keep_both_characters(self):
        for city,prefecture in [('四日市市','三重県'),('廿日市市','広島県'),
                                ('野々市市','石川県'),('今市市','栃木県'),('八日市市','滋賀県')]:
            with self.subTest(city=city):
                self.assertEqual(municipality_from_address(prefecture+city+'市場町123-4',prefecture),city)

    def test_city_boundary_repair_keeps_source_address_hash_and_identity(self):
        address='京都府福知山市市寺123-4'
        d=build_dataset('fixture','26','京都府','架空県神社庁',[row(address=address)])
        self.assertEqual(d['facilities'][0]['municipality'],'福知山市')
        self.assertEqual(d['facilities'][0]['address'],address)
        self.assertEqual(d['entries'][0]['reading_raw'],'カクウジンジャ')
        # Changing a derived municipality never participates in source identity.
        other=build_dataset('fixture','26','京都府','架空県神社庁',[row(address=address,municipality='明示市')])
        for key in ['id','address','source_hash']:
            self.assertEqual(d['facilities'][0][key],other['facilities'][0][key])
        self.assertEqual(other['facilities'][0]['municipality'],'明示市')

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

    def test_unconfirmed_source_authority_never_becomes_eligible(self):
        d=build_dataset('example','11','埼玉県','架空県神社庁',[row()],metadata={'authority_status':'pending','authority_reason':'current official linkage not established'})
        self.assertEqual(d['facilities'][0]['status'],'pending')
        self.assertEqual(d['entries'][0]['status'],'pending')
        self.assertEqual(eligible(d),[])

    def test_explicit_secondary_address_source_and_review_reason_preserved(self):
        d=build([row(address='架空市乙町1',address_source={'url':'https://agency.example.invalid/detail/1','page_hash':'b'*64,'fetched_at':'2026-11-08T00:00:00+00:00','name_raw':'架空神社','address_raw':'架空市乙町1'},review_reason='source name conflict requires review')])
        self.assertIn('address_source',d['facilities'][0])
        self.assertEqual(d['entries'][0]['status'],'pending')
    def test_external_glyph_name_cannot_be_exported_as_html(self):
        d=build([row(name='架空<svg></svg>神社',name_rendering_status='external_glyph')])
        self.assertEqual(d['entries'][0]['status'],'pending')
        self.assertEqual(eligible(d),[])

    def test_native_facility_with_unpublished_name_is_retained_for_review(self):
        d=build([row(name='')])
        self.assertEqual(eligible(d),[])
        self.assertTrue(all(p.get('severity')=='review' for p in validate(d)))
