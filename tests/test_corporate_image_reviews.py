"""Synthetic image-review metadata; no real images or shrine facts in fixtures."""
import copy
import unittest
from test_corporate import row,target,META
from njd import corporate as c
from njd.corrections import correction_problems


def fields(**changes):return dict(zip(c.FIELDS,row(**changes)))
def reviews(r):
    address=r['prefectureName']+r['cityName']+r['streetNumber']
    return {field:dict(image_id=r[field],url=c.BASE+'/image?imageid='+r[field],page_hash='b'*64,
        fetched_at='2026-11-10T00:00:00+00:00',checked_at='2026-11-10T01:00:00+00:00',
        corporate_number=r['corporateNumber'],archive_page_hash=META['page_hash'],snapshot=META['snapshot'],csv_row=1,
        source_name_raw=r['name'],source_address_raw=address,method='visual_inspection_of_official_image',
        note='Synthetic test: image/Unicode name and full parcel correspondence, original glyph evidence retained; no reading inferred.')
        for field in ['nameImageId','addressImageId'] if r[field]}

class CorporateImageReviewTests(unittest.TestCase):
    def test_image_ids_still_block_automatic_unreviewed_proposal(self):
        with self.assertRaises(ValueError):c._proposal(target(),fields(nameImageId='00000001'),'31_tottori_all_20261030.csv',1,META)
    def test_reviewed_name_and_address_images_allow_literal_full_csv_reading(self):
        r=fields(nameImageId='00000001',addressImageId='00000002')
        proposal=c._proposal(target(),r,'31_tottori_all_20261030.csv',1,META,image_reviews=reviews(r))
        ref=proposal['references'][0]
        self.assertEqual(proposal['changes'],dict(reading='まえだじんじゃ'))
        self.assertEqual(ref['source_fields'],r);self.assertEqual(ref['image_reviews'],reviews(r))
        self.assertFalse(correction_problems(proposal,target()['facility'],target()['entry'],target()['source']))
    def test_registry_image_claim_requires_exact_review_packet(self):
        p=c._proposal(target(),fields(),'31_tottori_all_20261030.csv',1,META)
        p['references'][0]['source_fields']['nameImageId']='00000001'
        self.assertTrue(correction_problems(p,target()['facility'],target()['entry'],target()['source']))
    def test_wrong_image_row_archive_or_target_is_rejected(self):
        r=fields(nameImageId='00000001')
        for key,value in [('url',c.BASE+'/image?imageid=00000002'),('corporate_number','9876543210123'),('archive_page_hash','c'*64),('snapshot','20260930'),('csv_row',2),('source_name_raw','別神社'),('source_address_raw','鳥取県鳥取市別町1'),('method','inferred'),('page_hash',''),('checked_at','')]:
            packet=reviews(r);packet['nameImageId'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):c._proposal(target(),r,'31_tottori_all_20261030.csv',1,META,image_reviews=packet)
    def test_image_inspection_does_not_supply_missing_or_repair_large_kana(self):
        for raw in ['', 'マエダジンジヤ','マエダ']:
            r=fields(nameImageId='00000001',furigana=raw)
            with self.assertRaises(ValueError):c._proposal(target(),r,'31_tottori_all_20261030.csv',1,META,image_reviews=reviews(r))

class CorporateImageBindingTests(unittest.TestCase):
    def valid(self):
        r=fields(nameImageId='00000001');return c._proposal(target(),r,'31_tottori_all_20261030.csv',1,META,image_reviews=reviews(r))
    def test_image_evidence_cannot_detach_reading_or_archive_from_raw_csv(self):
        for mutate in [lambda ref:ref.update(reading_raw='マエタジンジャ'),lambda ref:ref.update(page_hash=''),lambda ref:ref.update(snapshot='')]:
            p=self.valid();ref=p['references'][0];mutate(ref)
            if not ref.get('page_hash'):ref['image_reviews']['nameImageId']['archive_page_hash']=''
            if not ref.get('snapshot'):ref['image_reviews']['nameImageId']['snapshot']=''
            self.assertTrue(correction_problems(p,target()['facility'],target()['entry'],target()['source']))
    def test_malformed_csv_field_types_are_structured_review_errors(self):
        p=self.valid();ref=p['references'][0];ref['source_fields']['prefectureName']=None
        self.assertTrue(correction_problems(p,target()['facility'],target()['entry'],target()['source']))

class CorporateImageLiteralReadingTests(unittest.TestCase):
    def test_a_consistent_corrected_reading_must_still_equal_original_csv_kana(self):
        r=fields(nameImageId='00000001');p=c._proposal(target(),r,'31_tottori_all_20261030.csv',1,META,image_reviews=reviews(r))
        ref=p['references'][0];ref['reading_raw']='マエタジンジャ';ref['excerpt']=ref['excerpt'].replace('マエダジンジャ','マエタジンジャ');p['changes']['reading']='まえたじんじゃ'
        self.assertTrue(correction_problems(p,target()['facility'],target()['entry'],target()['source']))

class CorporateImageAuthorityTests(unittest.TestCase):
    def test_image_backed_archive_requires_official_source_and_valid_corporate_number(self):
        r=fields(nameImageId='00000001');meta=dict(META,url='https://other.example/archive')
        with self.assertRaises(ValueError):c._proposal(target(),r,'31_tottori_all_20261030.csv',1,meta,image_reviews=reviews(r))
        r=fields(nameImageId='00000001',corporateNumber='invalid')
        with self.assertRaises(ValueError):c._proposal(target(),r,'31_tottori_all_20261030.csv',1,META,image_reviews=reviews(r))

    def daily(self):
        meta=dict(META,url=c.BASE+'/download/sabun/index.html',snapshot='20261118',checked_at='2026-11-19T00:00:00+00:00')
        r=fields(nameImageId='00000001',updateDate='2026-11-18')
        packet=reviews(r)
        packet['nameImageId']['snapshot']=meta['snapshot']
        return meta,r,packet

    def test_daily_image_review_binds_the_official_difference_version(self):
        meta,r,packet=self.daily()
        proposal=c._proposal(target(),r,'diff_20261118.csv',1,meta,image_reviews=packet)
        ref=proposal['references'][0]
        self.assertEqual(ref['title'],'国税庁法人番号公表サイト 差分データ')
        self.assertEqual(ref['source_fields'],r)
        self.assertEqual(proposal['changes'],{'reading':'まえだじんじゃ'})

    def test_publication_date_uses_japan_standard_time(self):
        meta,r,packet=self.daily()
        meta['checked_at']='2026-11-17T15:30:00+00:00'
        proposal=c._proposal(target(),r,'diff_20261118.csv',1,meta,image_reviews=packet)
        self.assertEqual(proposal['changes'],{'reading':'まえだじんじゃ'})

    def test_daily_image_review_rejects_mismatched_archive_or_csv_date(self):
        meta,r,packet=self.daily()
        cases=[
            (meta,r,'diff_20261117.csv'),
            (meta,dict(r,updateDate='2026-11-17'),'diff_20261118.csv'),
            (dict(meta,checked_at='2026-11-17T14:59:00+00:00'),r,'diff_20261118.csv'),
            (dict(meta,file_id='not-an-id'),r,'diff_20261118.csv'),
            (dict(meta,url=c.BASE+'/download/zenken/index.html'),r,'diff_20261118.csv'),
            (dict(meta,url='https://other.example/download/sabun/index.html'),r,'diff_20261118.csv'),
        ]
        for archive,row,member in cases:
            with self.subTest(archive=archive,member=member),self.assertRaises(ValueError):
                c._proposal(target(),row,member,1,archive,image_reviews=packet)

class CorporateImageActiveIdentityTests(unittest.TestCase):
    def test_images_do_not_make_historical_closed_or_hidden_corporations_eligible(self):
        for change in [dict(latest='0'),dict(process='99'),dict(closeDate='2026-10-01'),dict(hihyoji='1')]:
            r=fields(nameImageId='00000001',**change)
            with self.subTest(change=change),self.assertRaises(ValueError):c._proposal(target(),r,'31_tottori_all_20261030.csv',1,META,image_reviews=reviews(r))
