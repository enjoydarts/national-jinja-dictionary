import copy
import unittest
from test_records import build, row
from test_reviews import decision
from njd.reviews import apply_reviews
from njd.validation import eligible, blocking_problems


class LinkedProfileReviewTests(unittest.TestCase):
    def case(self):
        data=build([row(name='総社神社',reading_raw='そうしゃじんじゃ',address='架空市')])
        f=data['facilities'][0];e=data['entries'][0]
        data['collection']['source_key']='ibaraki';f['source_key']='ibaraki'
        f.update(status='pending',reason='regional agency name differs from linked detail name',
            review_reason='regional agency name differs from linked detail name',
            native_source_id='https://agency.example.invalid/shrines/42')
        profile=dict(url=f['native_source_id'],link_url=f['native_source_id'],name_raw='總社神社',
            address_raw='架空市甲町42',page_hash='b'*64,locator='table shrine name/location',
            fetched_at='2026-11-08T01:00:00+00:00',applied=False)
        f['address_source']=copy.deepcopy(profile)
        ref=dict(url=profile['url'],source_kind='agency',title='保存済みのリンク先詳細',
            name_raw=profile['name_raw'],address_raw=profile['address_raw'],
            excerpt=profile['name_raw']+' / '+profile['address_raw'],page_hash=profile['page_hash'],
            checked_at=profile['fetched_at'])
        review=decision(data,[dict(surface='總社神社',reading='そうしゃじんじゃ',
            reading_url=f['listing_url'],basis='agency_selected')],
            review_kind='linked_agency_profile_surface_selection',
            profile_selection=dict(profile=copy.deepcopy(profile),listing_url=f['listing_url'],listing_page_hash=f['page_hash']),
            references=[ref],accepted_identity_differences=[dict(url=ref['url'],agency_name=f['name_raw'],
                agency_address=f['address'],reference_name=ref['name_raw'],reference_address=ref['address_raw'])])
        return data,review

    def test_explicit_linked_detail_surface_keeps_original_reading_and_source(self):
        data,review=self.case();before=copy.deepcopy(data)
        result=apply_reviews(data,review)
        self.assertEqual(blocking_problems(result),[])
        self.assertEqual(len(eligible(result)),1)
        e=eligible(result)[0]
        self.assertEqual((e['surface'],e['reading']),('總社神社','そうしゃじんじゃ'))
        self.assertEqual(e['name_raw'],'総社神社')
        self.assertEqual(result['facilities'][0]['address'],'架空市')
        self.assertEqual(data,before)

    def test_binding_or_independent_hold_cannot_be_overridden(self):
        for change in ('link','hash','city','surface','reading','approval','identity','reason','reference'):
            with self.subTest(change=change):
                data,review=self.case();item=next(iter(review['entries'].values()));f=data['facilities'][0]
                if change=='link': f['native_source_id']='https://agency.example.invalid/shrines/other'
                elif change=='hash': item['profile_selection']['profile']['page_hash']='c'*64
                elif change=='city':
                    f['address_source']['address_raw']='別市甲町42'
                    item['profile_selection']['profile']=copy.deepcopy(f['address_source'])
                elif change=='surface': item['outputs'][0]['surface']='別神社'
                elif change=='reading': item['outputs'][0]['reading']='べつじんじゃ'
                elif change=='approval': item['confirmation']='source_review'
                elif change=='identity': data['entries'][0]['identity_review_required']=True
                elif change=='reason': f.update(reason='multiple address lines',review_reason='multiple address lines')
                elif change=='reference': item['references'][0]['page_hash']='c'*64
                self.assertEqual(eligible(apply_reviews(data,review)),[])
