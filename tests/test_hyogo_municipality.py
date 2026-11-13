"""Artificial fixtures: supplements never rewrite acquired address or reading."""
import copy
import hashlib
import unittest
from test_hyogo_profile_review import fixture as profile_fixture
from njd.locations import apply_locations,location_problems
from njd.validation import eligible,blocking_problems


def fixture():
    d,_,v=profile_fixture();f=d['facilities'][0];e=d['entries'][0]
    address='神崎郡神河架空123-4';raw='〒000-0000\n'+address
    digest=hashlib.sha256(('架空八幡神社\0カクウハチマンジンジャ\0'+address).encode()).hexdigest()
    f.update(address=address,address_raw=raw,municipality='',source_hash=digest,reason='missing name, address or municipality',map_address_raw=address)
    f.pop('review_reason');e.update(source_hash=digest,reading='かくうはちまんじんじゃ',reason=f['reason'])
    m=f['xml_occurrences'][0];m.update(name_raw=f['name_raw'],address_raw=address)
    profile,mapped,reg=copy.deepcopy(v['references']);profile.update(address_raw=raw,excerpt=f['name_raw']+' / カクウハチマンジンジャ / 6300001/兼務 / '+raw)
    mapped.update(name_raw=f['name_raw'],address_raw=address,excerpt=f['name_raw']+' / 6300001 / '+address)
    fields=reg['source_fields'];fields.update(cityName='神崎郡神河町',streetNumber='架空１２３番地の４',postCode='0000000')
    reg.update(address_raw='兵庫県神崎郡神河町架空１２３番地の４',excerpt=f['name_raw']+' / 兵庫県神崎郡神河町架空１２３番地の４ / 0000000')
    town=dict(url='https://www.town.kamikawa.hyogo.jp/0000000707.html',page_hash='c'*64,
        title='人工の行政名根拠',source_kind='government_municipality',publisher='神河町',municipality_raw='神崎郡神河町',
        locator='footer address',excerpt='神河町役場 兵庫県神崎郡神河町寺前64番地',fetched_at=profile['fetched_at'],checked_at=profile['checked_at'])
    s=dict(supplement_kind='hyogo_registered_municipality',status='verified',facility_id=f['id'],expected_source_hash=digest,
        original={k:f.get(k) for k in ('name_raw','address','municipality','listing_url','official_site_url','native_source_id')},
        reason='人工資料の全所在地と実行政名を照合し派生市町村だけを補完',recorded_at=profile['checked_at'],
        changes=dict(municipality='神崎郡神河町'),reference=profile,map_reference=mapped,registry_reference=reg,municipality_reference=town)
    return d,dict(schema_version=1,facilities={f['id']:s}),s


class HyogoMunicipalityTest(unittest.TestCase):
    def test_supplement_changes_only_derived_municipality_and_revalidates(self):
        # Missing dispatch leaves the facility pending; rewriting address violates raw retention.
        d,doc,s=fixture();before=copy.deepcopy(d);f=d['facilities'][0]
        self.assertEqual(location_problems(s,f,d['collection']),[])
        out=apply_locations(d,doc);got=out['facilities'][0]
        self.assertEqual((got['municipality'],got['address']),('神崎郡神河町','神崎郡神河架空123-4'))
        self.assertEqual(len(eligible(out)),1);self.assertFalse(blocking_problems(out))
        for k in ['name_raw','address','address_raw','source_hash','id','xml_occurrences','map_address_raw']:
            self.assertEqual(got[k],f[k])
        for k in ['id','reading_raw','reading','source_hash','reading_source_kind']:
            self.assertEqual(out['entries'][0][k],d['entries'][0][k])
        self.assertEqual(d,before);self.assertEqual(apply_locations(out,doc),out)

    def test_unverified_full_parcel_postcode_identity_or_window_stays_pending(self):
        # Omitting any of these guards would adopt a different parcel/corporation or stale evidence.
        changes=[lambda s:s['changes'].update(address='神崎郡神河町架空123-4'),
            lambda s:s['changes'].update(municipality='神崎郡別町'),lambda s:s.update(expected_source_hash='f'*64),
            lambda s:s['reference'].update(reading_raw='カクウハチマングウ'),
            lambda s:s['reference'].update(printed_code_raw='6300002/兼務'),
            lambda s:s['reference'].update(page_hash='f'*64),lambda s:s['map_reference'].update(code_raw='6300002'),
            lambda s:s['map_reference'].update(address_raw='神崎郡神河架空123-40'),
            lambda s:s['registry_reference']['source_fields'].update(streetNumber='架空１２３番地'),
            lambda s:s['registry_reference']['source_fields'].update(postCode='0000001'),
            lambda s:s['registry_reference']['source_fields'].update(name='架空八幡宮'),
            lambda s:s['registry_reference']['source_fields'].update(nameImageId='00001'),
            lambda s:s['registry_reference']['source_fields'].update(furigana='ベツジンジャ'),
            lambda s:s['registry_reference']['registry_state_proof'].update(target_corporate_or_full_parcel_events=1),
            lambda s:s['registry_reference']['registry_state_proof'].update(active_shrine_corporation_count_at_full_address=2),
            lambda s:s['registry_reference']['registry_state_proof']['daily_resources'].pop(),
            lambda s:s['municipality_reference'].update(url='https://example.invalid/'),
            lambda s:s['municipality_reference'].update(excerpt='神河町'),
            lambda s:s['municipality_reference'].update(fetched_at='2099-01-01T00:00:00+00:00'),
            lambda s:s.update(recorded_at='2020-01-01T00:00:00+00:00')]
        for i,change in enumerate(changes):
            with self.subTest(i=i):
                d,doc,s=fixture();change(s);out=apply_locations(d,doc)
                self.assertEqual(eligible(out),[]);self.assertEqual(out['facilities'][0]['municipality'],'')

    def test_failed_reapplication_restores_original_municipality_and_blocks_validation(self):
        d,doc,s=fixture();out=apply_locations(d,doc)
        self.assertEqual(len(eligible(out)),1)
        out['facilities'][0]['location_supplement']['registry_reference']['source_fields']['postCode']='0000001'
        self.assertTrue(blocking_problems(out))
        doc['facilities'][d['facilities'][0]['id']]=copy.deepcopy(out['facilities'][0]['location_supplement'])
        rejected=apply_locations(out,doc)
        self.assertEqual(rejected['facilities'][0]['municipality'],'')
        self.assertEqual(rejected['facilities'][0]['address'],'神崎郡神河架空123-4')
        self.assertEqual(eligible(rejected),[])

    def test_existing_town_name_other_conditions_and_old_supplement_kind_are_protected(self):
        for case in ['has_town','glyph','identity','reason','excluded','map_name','source','old_kind','authority']:
            with self.subTest(case=case):
                d,doc,s=fixture();f=d['facilities'][0];e=d['entries'][0]
                if case=='has_town':f.update(address='神崎郡神河町架空123-4',municipality='神崎郡神河町')
                elif case=='glyph':f['name_rendering_status']='external_glyph'
                elif case=='identity':f['identity_review_required']=True
                elif case=='reason':f['reason']='different condition'
                elif case=='excluded':e.update(status='excluded',reason='excluded')
                elif case=='map_name':f['xml_occurrences'][0]['name_raw']='架空八幡宮'
                elif case=='source':f['source_key']='other'
                elif case=='old_kind':s.pop('supplement_kind')
                elif case=='authority':d['collection']['authority_status']='unconfirmed'
                out=apply_locations(d,doc);self.assertEqual(eligible(out),[])
                if case=='excluded':self.assertEqual(out['entries'][0]['status'],'excluded')

    def test_non_numeric_locality_glyphs_are_literal_and_no_full_address_nfkc_is_allowed(self):
        for original,registered in [('架空塚','架空塚'),('架空ｶ','架空カ'),('架空Ａ','架空A')]:
            with self.subTest(original=original):
                d,doc,s=fixture();f=d['facilities'][0];e=d['entries'][0]
                addr='神崎郡神河'+original+'123-4';raw='〒000-0000\n'+addr
                digest=hashlib.sha256(('架空八幡神社\0カクウハチマンジンジャ\0'+addr).encode()).hexdigest()
                f.update(address=addr,address_raw=raw,map_address_raw=addr,source_hash=digest)
                f['xml_occurrences'][0]['address_raw']=addr;e['source_hash']=digest
                s['original']['address']=addr;s['expected_source_hash']=digest
                s['reference'].update(address_raw=raw,excerpt='架空八幡神社 / カクウハチマンジンジャ / 6300001/兼務 / '+raw)
                s['map_reference'].update(address_raw=addr,excerpt='架空八幡神社 / 6300001 / '+addr)
                reg=s['registry_reference'];reg['source_fields']['streetNumber']=registered+'１２３番地の４'
                reg['address_raw']='兵庫県神崎郡神河町'+registered+'１２３番地の４';reg['excerpt']='架空八幡神社 / '+reg['address_raw']+' / 0000000'
                self.assertEqual(eligible(apply_locations(d,doc)),[])

    def test_malformed_nested_provenance_is_rejected_without_exceptions(self):
        for field in ['reference','map_reference','registry_reference','municipality_reference','changes','original']:
            for value in [None,[],True,0,'']:
                with self.subTest(field=field,value=value):
                    d,doc,s=fixture();s[field]=value
                    self.assertEqual(eligible(apply_locations(d,doc)),[])
