"""Synthetic evidence: never used as real shrine identity or pronunciation."""
import copy
import unittest
from njd.records import build_dataset
from njd.reviews import apply_reviews,review_problems
from njd.validation import eligible,blocking_problems


def fixture(address='茨城県架空市架空町\n123-4'):
    index='https://agency.example.invalid/area/'
    detail=index+'jinja/1.html'
    when='2026-11-13T01:00:00+00:00'
    data=build_dataset('fixture','08','茨城県','架空神社庁',[dict(name='架空神社',
        reading_raw='カクウジンジャ',address=address,url=index,page_hash='a'*64,
        fetched_at=when,locator='table row 1',evidence='架空神社 カクウジンジャ 架空市',source_id=detail,
        address_source=dict(url=detail,link_url=detail,name_raw='架空神社',address_raw=address,
            page_hash='b'*64,fetched_at=when,locator='typed address cell'))])
    f=data['facilities'][0];e=data['entries'][0]
    common=dict(title='人工資料',checked_at=when,fetched_at=when,name_raw='架空神社')
    refs=[dict(common,evidence_role='agency_index',source_kind='agency',url=index,page_hash='a'*64,
        locator='table row 1',reading_raw='カクウジンジャ',reading_scope='full_name',
        address_raw='架空市',native_href_raw=detail,excerpt='架空神社 / カクウジンジャ / 架空市 / '+detail),
        dict(common,evidence_role='agency_address',source_kind='agency',url=detail,page_hash='b'*64,
        locator='typed address cell',address_raw=address,excerpt='架空神社 / '+address)]
    fields=dict(name='架空神社',corporateNumber='1234567890123',prefectureCode='08',
        prefectureName='茨城県',cityName='架空市',streetNumber='架空町１２３番地４',kind='399',
        latest='1',process='01',closeDate='',hihyoji='0',nameImageId='',addressImageId='',furigana='')
    regaddress='茨城県架空市架空町１２３番地４'
    refs.append(dict(common,evidence_role='registered_address_identity',source_kind='government_corporate_register',
        url='https://www.houjin-bangou.nta.go.jp/download/zenken/index.html',page_hash='c'*64,
        locator='synthetic CSV row 2',csv_row=2,snapshot='20261030',corporate_number=fields['corporateNumber'],
        source_fields=fields,address_raw=regaddress,excerpt='架空神社 / '+regaddress,
        registry_state_proof=dict(as_of='20261111',active_matching_full_address_count=1,
            active_matching_corporate_numbers=[fields['corporateNumber']])))
    review=dict(confirmation='source_review',review_kind='single_address_linebreak',case_id='fixture-layout',
        recorded_at=when,reason='人工の単一住所セルと明示全文かなを個別審査',facility_id=f['id'],
        expected_source_hash=e['source_hash'],original=dict(name_raw=f['name_raw'],reading_raw=e['reading_raw'],
            address=address,listing_url=index),references=refs,
        address_presentation_proof=dict(kind='agency_two_line_locality_parcel',facility_id=f['id'],entry_id=e['id'],
            expected_source_hash=e['source_hash'],joined_address_raw=''.join(address.splitlines())),
        outputs=[dict(surface='架空神社',reading='かくうじんじゃ',reading_url=index,basis='agency_selected')])
    return data,dict(schema_version=1,entries={e['id']:review}),review


class AddressLayoutReviewTest(unittest.TestCase):
    def test_bound_layout_review_keeps_all_original_fields_and_selects_agency_kana(self):
        for separator in ['\n','\r\n']:
            with self.subTest(separator=repr(separator)):
                data,doc,review=fixture('茨城県架空市架空町'+separator+'123-4');before=copy.deepcopy(data)
                self.assertEqual(review_problems(review,data['facilities'][0],data['entries'][0],data['collection']),[])
                out=apply_reviews(data,doc);self.assertEqual(len(eligible(out)),1);self.assertFalse(blocking_problems(out))
                self.assertEqual(out['facilities'][0]['address'],before['facilities'][0]['address'])
                self.assertEqual(out['facilities'][0]['address_source'],before['facilities'][0]['address_source'])
                for key in ['id','surface','reading','reading_raw','source_hash','reading_url']:
                    self.assertEqual(out['entries'][0][key],before['entries'][0][key])
                self.assertEqual(data,before)
                again=apply_reviews(out,doc);self.assertEqual(len(eligible(again)),1)

    def test_missing_or_changed_bound_material_stays_pending(self):
        mutations=[
            lambda v:v.pop('address_presentation_proof'),
            lambda v:v['address_presentation_proof'].update(facility_id='other'),
            lambda v:v['address_presentation_proof'].update(entry_id='other'),
            lambda v:v['address_presentation_proof'].update(expected_source_hash='d'*64),
            lambda v:v['address_presentation_proof'].update(joined_address_raw='茨城県架空市別町123-4'),
            lambda v:v['references'].pop(0),
            lambda v:v['references'][0].update(page_hash='d'*64),
            lambda v:v['references'][0].update(native_href_raw='https://agency.example.invalid/other/'),
            lambda v:v['references'][0].update(reading_raw='ベツジンジャ'),
            lambda v:v['references'][1].update(url='https://other.example.invalid/'),
            lambda v:v['references'][1].update(page_hash='d'*64),
            lambda v:v['references'][1].update(address_raw='茨城県架空市別町123-4'),
            lambda v:v['references'][2]['source_fields'].update(latest='0'),
            lambda v:v['references'][2]['source_fields'].update(process='99'),
            lambda v:v['references'][2]['source_fields'].update(closeDate='2026-11-01'),
            lambda v:v['references'][2]['source_fields'].update(hihyoji='1'),
            lambda v:v['references'][2]['source_fields'].update(nameImageId='00000001'),
            lambda v:v['references'][2]['registry_state_proof'].update(active_matching_full_address_count=2),
            lambda v:v['references'][2]['registry_state_proof'].update(active_matching_corporate_numbers=['other']),
            lambda v:v['references'][2].update(corporate_number='9999999999999'),
        ]
        for i,mutate in enumerate(mutations):
            with self.subTest(case=i):
                data,doc,v=fixture();mutate(v);self.assertEqual(eligible(apply_reviews(data,doc)),[])

    def test_real_multiple_locations_notes_and_split_parcel_remain_pending(self):
        for address in ['茨城県架空市架空町123\n茨城県別市別町456',
                        '茨城県架空市架空町\n123-4 ※移転後住所',
                        '茨城県架空市架空町1\n23-4',
                        '茨城県架空市架空町\n123-4\n567-8']:
            with self.subTest(address=address):
                data,doc,v=fixture(address);self.assertEqual(eligible(apply_reviews(data,doc)),[])

    def test_malformed_evidence_is_rejected_without_crashing(self):
        mutations=[lambda v:v.update(address_presentation_proof=[]),
            lambda v:v.update(references={}),
            lambda v:v['references'][0].update(evidence_role={}),
            lambda v:v['references'][0].update(excerpt=None),
            lambda v:v['references'][2].update(source_fields=None),
            lambda v:v['references'][2]['source_fields'].update(cityName=None),
            lambda v:v['references'][2]['source_fields'].update(process=None),
            lambda v:v['references'][2].update(csv_row=True)]
        for i,mutate in enumerate(mutations):
            with self.subTest(case=i):
                data,doc,v=fixture();mutate(v)
                try:out=apply_reviews(data,doc)
                except Exception as exc:self.fail('malformed evidence crashed: '+type(exc).__name__)
                self.assertEqual(eligible(out),[])

    def test_different_registry_parcel_or_aza_cannot_clear_layout_hold(self):
        for locality in ['架空町１２３番地４０','架空町１２３番地','架空町字別所１２３番地４']:
            with self.subTest(locality=locality):
                data,doc,v=fixture();ref=v['references'][2];ref['source_fields']['streetNumber']=locality
                ref['address_raw']='茨城県架空市'+locality;ref['excerpt']='架空神社 / '+ref['address_raw']
                self.assertEqual(eligible(apply_reviews(data,doc)),[])

    def test_layout_review_cannot_change_name_reading_or_override_another_condition(self):
        for case in ['surface','reading','reason','identity','excluded','stale']:
            with self.subTest(case=case):
                data,doc,v=fixture()
                if case=='surface':v['outputs'][0]['surface']='別名神社'
                elif case=='reading':v['outputs'][0]['reading']='べつじんじゃ'
                elif case=='reason':data['facilities'][0]['reason']='unresolved name conflict'
                elif case=='identity':data['entries'][0]['identity_review_required']=True
                elif case=='excluded':data['entries'][0].update(status='excluded',reason='excluded by source review')
                elif case=='stale':data['facilities'][0]['address']='茨城県架空市別町\n123-4'
                self.assertEqual(eligible(apply_reviews(data,doc)),[])
