"""Artificial inspection packets: these tests establish no real facility facts."""
import copy
import unittest
from njd.records import build_dataset
from njd.corrections import correction_problems,apply_corrections
from njd.validation import eligible,blocking_problems
from njd.hyogo_registry_window import DAILY_FILES


def fixture():
    name='架盞神社';csvname='架＿神社';when='2026-11-13T06:00:00+00:00';code='9999'
    index='https://www.shiga-jinjacho.jp/ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-search.html?mode:search=1&view:term=100&view:page=1'
    href='ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-detail.html?mode:view=1&view:oid='+code
    url='https://www.shiga-jinjacho.jp/'+href;raw='長浜市架空町';full='滋賀県長浜市架空町123-4';quote='人工一覧 '+name+' '+raw
    d=build_dataset('shiga','25','滋賀県','人工神社庁',[dict(name=name,reading_raw='',address=raw,url=index,page_hash='a'*64,
        fetched_at=when,locator='a.news_title[1] + postal address span',evidence=quote,source_id=code)],metadata=dict(authority_status='confirmed'))
    f=d['facilities'][0];e=d['entries'][0]
    ip=dict(index_url=index,index_page_hash='a'*64,index_locator=f['source_locator'],index_checked_at=when,index_excerpt=quote,
        source_id=code,name_raw=name,address_raw=raw,href_raw=href,base_href='https://www.shiga-jinjacho.jp/',url=url)
    native=dict(url=url,title='人工神社庁詳細',source_kind='agency',name_raw=name,name_display_raw=name+' （カ）',reading_raw='カ',
        reading_scope='partial_or_absent',agency_code=code,address_raw=full,page_hash='b'*64,locator='div.j_title; 鎮座地',
        fetched_at=when,checked_at=when,excerpt=name+' （カ） / '+full,alias_display_raw='')
    f['agency_detail_reading_research']=dict(index_proof=copy.deepcopy(ip),reference=copy.deepcopy(native),status='inspected')
    agency=copy.deepcopy(native);agency.update(page_hash='c'*64,identity_only=True,index_proof=dict(ip,index_page_hash='e'*64))
    fields=dict(corporateNumber='1234567890123',name=csvname,furigana='カジンジャ',prefectureCode='25',prefectureName='滋賀県',cityName='長浜市',
        streetNumber='架空町１２３番地の４',postCode='0000000',kind='399',latest='1',process='01',closeDate='',hihyoji='0',nameImageId='00000001',addressImageId='')
    addr='滋賀県長浜市架空町１２３番地の４';archive='87869a2c6b84617c97c9aa95138a34ef17899540cee159a81ac3529b3ea3d510'
    im=dict(image_id='00000001',url='https://www.houjin-bangou.nta.go.jp/image?imageid=00000001',corporate_number=fields['corporateNumber'],
        archive_page_hash=archive,snapshot='20261030',csv_row=2,source_name_raw=csvname,source_address_raw=addr,page_hash='d'*64,
        fetched_at=when,checked_at=when,method='visual_inspection_of_official_image',note='人工目視全文='+name+' / CSV='+csvname,
        placeholder_field_name_raw=csvname,placeholder_character='＿',placeholder_character_index_zero_based=1,transcribed_full_name_raw=name)
    proof=dict(rule='literal_registered_name_placeholder_with_individual_image_review',target_entry_id=e['id'],expected_source_hash=e['source_hash'],
        image_field='nameImageId',image_id='00000001',image_page_hash='d'*64,placeholder_character='＿',placeholder_indices_zero_based=[1],
        registered_name_raw=csvname,transcribed_character='盞',transcribed_full_name_raw=name)
    monthly=dict(url='https://www.houjin-bangou.nta.go.jp/download/zenken/index.html',page_hash=archive,fetched_at=when,file_id='28432',snapshot='20261030',data_rows=44347)
    daily=[dict(date=x['date'],file_id=x['file_id'],url=x['url'],page_hash=x['page_hash'],data_rows=x['rows'],fetched_at=when) for x in DAILY_FILES]
    reg=dict(url=monthly['url'],title='人工登録CSV',source_kind='government_corporate_register',source_fields=fields,name_raw=csvname,
        reading_raw=fields['furigana'],reading_scope='full_name',address_raw=addr,corporate_number=fields['corporateNumber'],page_hash=archive,
        fetched_at=when,checked_at=when,locator='synthetic CSV row2',csv_row=2,snapshot='20261030',file_id='28432',zip_member='25_shiga_all_20261030.csv',
        excerpt=csvname+' / カジンジャ / '+addr,image_reviews=dict(nameImageId=im),registered_name_image_identity=proof,
        registry_state_proof=dict(as_of='20261112',monthly_base=[monthly],daily_deltas=daily,daily_rows=19178,target_corporate_or_full_parcel_events=0,
            active_religious_corporations_at_native_full_address=1,active_corporate_numbers_at_native_full_address=[fields['corporateNumber']]))
    c=dict(correction_kind='registered_name_image_full_reading',case_id='synthetic-name-image',status='verified',recorded_at=when,
        facility_id=f['id'],expected_source_hash=e['source_hash'],original=dict(name_raw=name,reading_raw='',address=raw,listing_url=index),
        changes=dict(reading='かじんじゃ'),reason='人工個別画像の全文名と全地番/実IDを照合。同じCSV行の全文かなを採用',
        identity_match=dict(agency_native_id=code,actual_detail_id=code,agency_name_raw=name,original_address_raw=raw,native_full_address_raw=full,
            registered_name_raw=csvname,registered_image_name_raw=name,registered_full_address_raw=addr),references=[agency,reg])
    return d,dict(schema_version=1,entries={e['id']:c}),c


class RegisteredNameImageTest(unittest.TestCase):
    def test_individual_proxy_image_full_kana_keeps_every_original_field_and_reapplies(self):
        d,doc,c=fixture();before=copy.deepcopy(d);f=d['facilities'][0];e=d['entries'][0]
        self.assertEqual(correction_problems(c,f,e,d['collection']),[])
        out=apply_corrections(d,doc);got=out['entries'][0]
        self.assertEqual((got['reading'],got['reading_url'],got['reading_source_kind']),('かじんじゃ','https://www.houjin-bangou.nta.go.jp/download/zenken/index.html','reference'))
        self.assertEqual(len(eligible(out)),1);self.assertFalse(blocking_problems(out));self.assertEqual(d,before)
        self.assertEqual(out['facilities'],before['facilities'])
        for k in ['id','name_raw','surface','reading_raw','source_hash','page_hash']:self.assertEqual(got[k],e[k])
        self.assertEqual(got['correction']['references'][1]['name_raw'],'架＿神社')
        self.assertEqual(apply_corrections(out,doc),out)

    def test_different_proxy_position_image_corporation_or_row_cannot_supply_reading(self):
        changes=[lambda c:c.pop('correction_kind'),lambda c:c['changes'].update(surface='架盞神社'),
            lambda c:c['references'][1]['registered_name_image_identity'].update(placeholder_indices_zero_based=[True]),
            lambda c:c['references'][1]['registered_name_image_identity'].update(transcribed_character='益'),
            lambda c:c['references'][1]['registered_name_image_identity'].update(transcribed_full_name_raw='架盞神宮'),
            lambda c:c['references'][1]['registered_name_image_identity'].update(image_page_hash='f'*64),
            lambda c:c['references'][1]['image_reviews']['nameImageId'].update(image_id='00000002'),
            lambda c:c['references'][1]['image_reviews']['nameImageId'].update(corporate_number='1234567890124'),
            lambda c:c['references'][1]['image_reviews']['nameImageId'].update(csv_row=3),
            lambda c:c['references'][1]['source_fields'].update(addressImageId='00000002'),
            lambda c:c['references'][1]['source_fields'].update(furigana='カジンシャ'),
            lambda c:c['references'][1]['registry_state_proof'].update(target_corporate_or_full_parcel_events=1),
            lambda c:c['references'][1]['registry_state_proof']['daily_deltas'].pop(),
            lambda c:c['references'][0]['index_proof'].update(source_id='9998'),
            lambda c:c['references'][0]['index_proof'].update(href_raw='unobserved.html'),
            lambda c:c['references'][0].update(fetched_at='2099-01-01T00:00:00+00:00'),
            lambda c:c['references'][1].update(fetched_at='2020-01-01T00:00:00+00:00')]
        for i,change in enumerate(changes):
            with self.subTest(i=i):
                d,doc,c=fixture();change(c);self.assertEqual(eligible(apply_corrections(d,doc)),[])

    def test_whole_parcel_is_compared_after_all_registered_quotations_are_consistent(self):
        for street in ['架空町１２３番地','架空町１２３番地の４０','架空別町１２３番地の４']:
            with self.subTest(street=street):
                d,doc,c=fixture();r=c['references'][1];r['source_fields']['streetNumber']=street;addr='滋賀県長浜市'+street
                r['address_raw']=addr;r['excerpt']='架＿神社 / カジンジャ / '+addr
                r['image_reviews']['nameImageId']['source_address_raw']=addr;c['identity_match']['registered_full_address_raw']=addr
                self.assertTrue(correction_problems(c,d['facilities'][0],d['entries'][0],d['collection']))
                self.assertEqual(eligible(apply_corrections(d,doc)),[])

    def test_offline_revalidation_and_invalid_reapplication_hold_the_output(self):
        d,doc,c=fixture();out=apply_corrections(d,doc);self.assertEqual(len(eligible(out)),1)
        out['entries'][0]['correction']['references'][1]['image_reviews']['nameImageId']['transcribed_full_name_raw']='架益神社'
        self.assertTrue(blocking_problems(out));self.assertEqual(eligible(out),[])
        c['references'][1]['image_reviews']['nameImageId']['transcribed_full_name_raw']='架益神社'
        self.assertEqual(eligible(apply_corrections(out,doc)),[])

    def test_other_identity_conditions_and_prior_exclusion_are_not_overridden(self):
        for case in ['entry_identity','facility_identity','excluded','review_reason','glyph','authority','stale','different_source','partial_added_sounds']:
            with self.subTest(case=case):
                d,doc,c=fixture();f=d['facilities'][0];e=d['entries'][0]
                if case=='entry_identity':e['identity_review_required']=True
                elif case=='facility_identity':f['identity_review_required']=True
                elif case=='excluded':e.update(status='excluded',reason='prior exclusion')
                elif case=='review_reason':f['review_reason']='another condition'
                elif case=='glyph':f['name_rendering_status']='external_glyph'
                elif case=='authority':d['collection']['authority_status']='unconfirmed'
                elif case=='stale':f['source_hash']='f'*64
                elif case=='different_source':f['source_key']='other'
                elif case=='partial_added_sounds':c['references'][0]['reading_raw']='カベツ'
                self.assertEqual(eligible(apply_corrections(d,doc)),[])

    def test_csv_remains_the_declared_reading_source_when_agency_kana_also_agrees(self):
        d,doc,c=fixture();f=d['facilities'][0];a=c['references'][0]
        for ref in [a,f['agency_detail_reading_research']['reference']]:
            ref.update(reading_raw='カジンジャ',name_display_raw='架盞神社 （カジンジャ）',excerpt='架盞神社 （カジンジャ） / '+ref['address_raw'])
        out=apply_corrections(d,doc)
        self.assertEqual(out['entries'][0]['reading_url'],'https://www.houjin-bangou.nta.go.jp/download/zenken/index.html')
        self.assertEqual(len(eligible(out)),1)

    def test_locality_text_is_literal_even_when_numeric_unit_normalization_could_fold_it(self):
        import hashlib
        for original,registered in [('一番町','1番町'),('架空塚','架空塚'),('架空ｶ','架空カ')]:
            with self.subTest(original=original,registered=registered):
                d,doc,c=fixture();f=d['facilities'][0];e=d['entries'][0];raw='長浜市'+original;full='滋賀県'+raw+'123-4'
                f['address']=raw;c['original']['address']=raw;digest=hashlib.sha256(('架盞神社\0\0'+raw).encode()).hexdigest()
                f['source_hash']=e['source_hash']=c['expected_source_hash']=c['references'][1]['registered_name_image_identity']['expected_source_hash']=digest
                old=f['agency_detail_reading_research'];old['index_proof'].update(address_raw=raw,index_excerpt='架盞神社 '+raw)
                old['reference']['address_raw']=full;a=c['references'][0];a.update(address_raw=full,excerpt='架盞神社 （カ） / '+full)
                a['index_proof'].update(address_raw=raw,index_excerpt='架盞神社 '+raw)
                reg=c['references'][1];street=registered+'１２３番地の４';addr='滋賀県長浜市'+street
                reg['source_fields']['streetNumber']=street;reg.update(address_raw=addr,excerpt='架＿神社 / カジンジャ / '+addr)
                reg['image_reviews']['nameImageId']['source_address_raw']=addr
                c['identity_match'].update(original_address_raw=raw,native_full_address_raw=full,registered_full_address_raw=addr)
                self.assertEqual(eligible(apply_corrections(d,doc)),[])

    def test_malformed_reason_and_raw_reference_fields_hold_without_exceptions(self):
        for field in ['reason','address']:
            for value in [None,True,[],{}]:
                with self.subTest(field=field,value=value):
                    d,doc,c=fixture()
                    if field=='reason':c['reason']=value
                    else:c['references'][1]['address_raw']=value
                    self.assertEqual(eligible(apply_corrections(d,doc)),[])

    def test_rebound_index_snapshot_on_another_origin_is_not_an_agency_binding(self):
        d,doc,c=fixture();f=d['facilities'][0];e=d['entries'][0]
        url=f['listing_url'].replace('www.shiga-jinjacho.jp','example.invalid')
        f['listing_url']=e['listing_url']=c['original']['listing_url']=url
        f['agency_detail_reading_research']['index_proof']['index_url']=url;c['references'][0]['index_proof']['index_url']=url
        self.assertTrue(correction_problems(c,f,e,d['collection']))
        self.assertEqual(eligible(apply_corrections(d,doc)),[])
