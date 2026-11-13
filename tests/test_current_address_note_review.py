"""Synthetic evidence; no fixture is a real shrine or adoption proof."""
import copy
import unittest
from njd.records import build_dataset
from njd.reviews import apply_reviews,review_problems
from njd.validation import eligible,blocking_problems

NOTE='※東日本大震災復興事業区画整理に伴い、令和3年11月27日に当住所へ表記変更となりました。'


def fixture(separator='\r\n',note=NOTE):
    when='2026-11-13T01:00:00+00:00';url='https://agency.example.invalid/jinja-search/list.php?page=3'
    href='detail.php?code=123&page=3';detail='https://agency.example.invalid/jinja-search/'+href
    first='宮城県架空市架空町3-4-1';address=first+separator+note
    d=build_dataset('fixture','04','宮城県','人工神社庁',[dict(name='架空神社',reading_raw='あつたじんじゃ',
        address=address,evidence='人工の名称・読み・鎮座地',url=url,page_hash='a'*64,fetched_at=when,locator='.simple-list-item[7]',source_id='123')])
    f=d['facilities'][0];e=d['entries'][0];common=dict(title='人工資料',source_kind='agency',
        checked_at=when,fetched_at=when,name_raw=f['name_raw'],reading_raw=e['reading_raw'],reading_scope='full_name')
    refs=[dict(common,evidence_role='agency_index',url=url,page_hash='a'*64,locator=f['source_locator'],
        address_raw=address,native_href_raw=href,excerpt='架空神社 / あつたじんじゃ / '+address),
        dict(common,evidence_role='agency_detail',url=detail,page_hash='b'*64,locator='h3 + p (鎮座地)',
        address_first_line_raw=first,current_address_note_raw=note,excerpt='架空神社 / あつたじんじゃ / '+address)]
    fields=dict(corporateNumber='1234567890123',name='架空神社',prefectureCode='04',prefectureName='宮城県',
        cityName='架空市',streetNumber='架空町３丁目４番地１',kind='399',latest='1',process='12',
        closeDate='',hihyoji='0',nameImageId='',addressImageId='',furigana='アツタジンジャ')
    regaddr='宮城県架空市架空町３丁目４番地１'
    refs.append(dict(common,evidence_role='registered_address_identity',source_kind='government_corporate_register',
        url='https://www.houjin-bangou.nta.go.jp/download/zenken/index.html',page_hash='c'*64,locator='CSV row 2',
        source_fields=fields,corporate_number=fields['corporateNumber'],csv_row=2,snapshot='20261030',
        address_raw=regaddr,reading_raw=fields['furigana'],excerpt='架空神社 / アツタジンジャ / '+regaddr,
        registry_state_proof=dict(as_of='20261112',active_matching_full_address_count=1,
            active_matching_corporate_numbers=[fields['corporateNumber']])))
    v=dict(confirmation='source_review',review_kind='single_address_current_note',case_id='synthetic-note',
        recorded_at=when,reason='人工資料の現在住所注記を審査',facility_id=f['id'],expected_source_hash=e['source_hash'],
        original=dict(name_raw=f['name_raw'],reading_raw=e['reading_raw'],address=address,listing_url=url),references=refs,
        address_presentation_proof=dict(kind='agency_current_address_notation_note',facility_id=f['id'],entry_id=e['id'],
            expected_source_hash=e['source_hash'],address_first_line_raw=first,current_address_note_raw=note,
            detail_url=detail,detail_page_hash='b'*64,detail_locator='h3 + p (鎮座地)'),
        outputs=[dict(surface=f['name_raw'],reading=e['reading'],reading_url=url,basis='agency_selected')])
    return d,dict(schema_version=1,entries={e['id']:v}),v


class CurrentAddressNoteReviewTest(unittest.TestCase):
    def test_explicit_current_note_selects_unchanged_reading_without_altering_raw_fields(self):
        for sep in ['\n','\r\n']:
            with self.subTest(separator=repr(sep)):
                d,doc,v=fixture(sep);before=copy.deepcopy(d)
                self.assertEqual(review_problems(v,d['facilities'][0],d['entries'][0],d['collection']),[])
                out=apply_reviews(d,doc);self.assertEqual(len(eligible(out)),1);self.assertFalse(blocking_problems(out))
                for k in ['id','name_raw','address','source_hash','native_source_id','listing_url']:
                    self.assertEqual(out['facilities'][0][k],before['facilities'][0][k])
                for k in ['id','surface','reading','reading_raw','source_hash','reading_url']:
                    self.assertEqual(out['entries'][0][k],before['entries'][0][k])
                self.assertEqual(d,before);self.assertEqual(len(eligible(apply_reviews(out,doc))),1)

    def test_other_addresses_and_notes_remain_pending_even_with_matching_references(self):
        for note in ['宮城県別市別町3-4-1','※旧住所です。',NOTE+' 宮城県別市1番地',NOTE+'\n別住所',NOTE.replace('当住所へ','旧住所から')]:
            with self.subTest(note=note):
                d,doc,v=fixture(note=note);self.assertEqual(eligible(apply_reviews(d,doc)),[])

    def test_missing_changed_and_malformed_bound_evidence_stays_pending(self):
        changes=[lambda v:v.pop('address_presentation_proof'),lambda v:v.update(address_presentation_proof=[]),
            lambda v:v['address_presentation_proof'].update(entry_id='other'),
            lambda v:v['address_presentation_proof'].update(expected_source_hash='f'*64),
            lambda v:v['address_presentation_proof'].update(address_first_line_raw='宮城県架空市別町3-4-1'),
            lambda v:v['references'].pop(),lambda v:v.update(references={}),
            lambda v:v['references'][0].update(evidence_role={}),
            lambda v:v['references'][0].update(evidence_role='agency_detail'),
            lambda v:v['references'][0].update(page_hash='f'*64),
            lambda v:v['references'][0].update(native_href_raw='detail.php?code=999'),
            lambda v:v['references'][0].update(address_raw='宮城県架空市架空町3-4-1'),
            lambda v:v['references'][1].update(url='https://other.example.invalid/detail.php?code=123'),
            lambda v:v['references'][1].update(page_hash='f'*64),
            lambda v:v['references'][1].update(locator='other'),
            lambda v:v['references'][1].update(reading_raw='べつじんじゃ'),
            lambda v:v['references'][1].update(excerpt=None),
            lambda v:v['references'][1].update(current_address_note_raw='※旧住所'),
            lambda v:v['references'][2].update(csv_row=True),
            lambda v:v['references'][2].update(snapshot='2026103'),
            lambda v:v['references'][2]['registry_state_proof'].update(as_of='2026111'),
            lambda v:v['references'][2].update(source_fields=None),
            lambda v:v['references'][2]['source_fields'].update(latest='0'),
            lambda v:v['references'][2]['source_fields'].update(process='99'),
            lambda v:v['references'][2]['source_fields'].update(closeDate='2026-11-01'),
            lambda v:v['references'][2]['source_fields'].update(hihyoji='1'),
            lambda v:v['references'][2]['source_fields'].update(nameImageId='001'),
            lambda v:v['references'][2]['source_fields'].update(addressImageId='001'),
            lambda v:v['references'][2]['source_fields'].update(furigana='ベツジンジャ'),
            lambda v:v['references'][2]['source_fields'].update(cityName=None),
            lambda v:v['references'][2]['registry_state_proof'].update(active_matching_full_address_count=2),
            lambda v:v['references'][2]['registry_state_proof'].update(as_of='20261001'),
            lambda v:v['outputs'][0].update(reading='べつじんじゃ'),
            lambda v:v['outputs'][0].update(surface='別名神社'),lambda v:v.update(split=True)]
        for i,change in enumerate(changes):
            with self.subTest(case=i):
                d,doc,v=fixture();change(v);self.assertEqual(eligible(apply_reviews(d,doc)),[])

    def test_whole_parcel_and_locality_must_match(self):
        for street in ['架空町３丁目４番地１０','架空町３丁目４番地','架空町字別所３丁目４番地１','別町３丁目４番地１']:
            with self.subTest(street=street):
                d,doc,v=fixture();r=v['references'][2];r['source_fields']['streetNumber']=street
                r['address_raw']='宮城県架空市'+street;r['excerpt']='架空神社 / アツタジンジャ / '+r['address_raw']
                self.assertEqual(eligible(apply_reviews(d,doc)),[])

    def test_other_conditions_and_changed_raw_material_cannot_be_overridden(self):
        for case in ['reason','excluded','identity','stale','unconfirmed','conflict']:
            with self.subTest(case=case):
                d,doc,v=fixture();f=d['facilities'][0];e=d['entries'][0]
                if case=='reason':f['reason']='another condition'
                elif case=='excluded':e.update(status='excluded',reason='excluded')
                elif case=='identity':e['identity_review_required']=True
                elif case=='stale':f['address']=f['address'].replace('3-4-1','3-4-10')
                elif case=='unconfirmed':d['collection']['authority_status']='unconfirmed'
                elif case=='conflict':f['source_conflicts']=[dict(name_raw='別名神社',address='別住所')]
                self.assertEqual(eligible(apply_reviews(d,doc)),[])
