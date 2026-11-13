"""Synthetic evidence, not real shrine identity or pronunciation proof."""
import copy
import unittest
from njd.records import build_dataset
from njd.reviews import apply_reviews,review_problems
from njd.validation import eligible,blocking_problems

REASON='Hyogo map and profile official names differ or are missing'
# Public, independently inspected archive window metadata; shrine fields below are synthetic.
DAILY_FIXTURE=[{'date': '20261102',
  'file_id': '28508',
  'rows': 2346,
  'page_hash': 'fed1d994034e65a53765c77e4f7106a3949c51f9cd88600ae9aa1e507e968485',
  'url': 'https://www.houjin-bangou.nta.go.jp/download/sabun/index.html'},
 {'date': '20261104',
  'file_id': '28511',
  'rows': 2156,
  'page_hash': '3c65e01545ac0e137166cf06c6d01bd88aaaf85527d1d065374dbbee4e62976d',
  'url': 'https://www.houjin-bangou.nta.go.jp/download/sabun/index.html'},
 {'date': '20261105',
  'file_id': '28514',
  'rows': 2183,
  'page_hash': '38ca2001e1e0912410cb8dfbf8b7f77d2b8a98d0901294721173e6dce0879f74',
  'url': 'https://www.houjin-bangou.nta.go.jp/download/sabun/index.html'},
 {'date': '20261106',
  'file_id': '28517',
  'rows': 2617,
  'page_hash': '7472580e4a837671b200a986da17567a0f7917692b3f0cb62f13f5b1010238c9',
  'url': 'https://www.houjin-bangou.nta.go.jp/download/sabun/index.html'},
 {'date': '20261109',
  'file_id': '28520',
  'rows': 2362,
  'page_hash': 'f2661f24d97564cf7b14a58389dfa1fa3f819a62c29f86b347a146b56a70765b',
  'url': 'https://www.houjin-bangou.nta.go.jp/download/sabun/index.html'},
 {'date': '20261110',
  'file_id': '28523',
  'rows': 2642,
  'page_hash': '38034ac0c65af5af98a5c01025c134e854c986d583886074d8d81afb79fbfb64',
  'url': 'https://www.houjin-bangou.nta.go.jp/download/sabun/index.html'},
 {'date': '20261111',
  'file_id': '28526',
  'rows': 2692,
  'page_hash': 'eb1976bceee98ace70fe15f074f861ca9f7d1e3ea2956477ee8e8f03df1dbddd',
  'url': 'https://www.houjin-bangou.nta.go.jp/download/sabun/index.html'},
 {'date': '20261112',
  'file_id': '28529',
  'rows': 2180,
  'page_hash': '896ee14905fdfcd8098dd4bdb87fdc9bd02655facaf056c3d5358b984a60c1b9',
  'url': 'https://www.houjin-bangou.nta.go.jp/download/sabun/index.html'}]


def fixture(locality='架空町字架空',registered_locality=None):
    when='2026-11-13T01:00:00+00:00';code='6300001';url='https://www.hyogo-jinjacho.com/data/'+code+'.html'
    address='架空市'+locality+'1-1';raw='〒000-0000\n'+address;name='架空八幡神社';kana='カクウハチマンジンジャ'
    data=build_dataset('hyogo','28','兵庫県','人工神社庁',[dict(name=name,reading_raw=kana,address=address,
        address_raw=raw,url=url,page_hash='a'*64,fetched_at=when,locator='header.hero fields',evidence='人工資料',
        source_id=code,review_reason=REASON)],metadata=dict(authority_status='confirmed'))
    f=data['facilities'][0];e=data['entries'][0];e.update(reading='',reading_display_raw=kana,printed_code_raw=code+'/兼務')
    m=dict(url='https://www.hyogo-jinjacho.com/data/xml.php?ne_lat=36&sw_lat=34&ne_lng=136&sw_lng=134',
        page_hash='b'*64,fetched_at=when,locator='Locations/Locate[1]',code_raw=code,name_raw='架空八幡宮',
        address_raw=address,protocol_url='https://www.hyogo-jinjacho.com/js/formsearch.js',
        href_derivation='data/ + actual Locate code + .html')
    f['xml_occurrences']=[m];f['map_address_raw']=address
    common=dict(title='人工資料',checked_at=when,fetched_at=when,source_kind='agency')
    refs=[dict(common,evidence_role='agency_profile',url=url,page_hash='a'*64,locator=f['source_locator'],
        name_raw=name,reading_raw=kana,reading_scope='full_name',address_raw=raw,printed_code_raw=e['printed_code_raw'],
        excerpt=name+' / '+kana+' / '+e['printed_code_raw']+' / '+raw),
        dict(common,**{k:v for k,v in m.items() if k!='fetched_at'},evidence_role='agency_map',excerpt='架空八幡宮 / '+code+' / '+address)]
    fields=dict(corporateNumber='1234567890123',name=name,prefectureCode='28',prefectureName='兵庫県',
        cityName='架空市',streetNumber=(registered_locality or locality)+'１番地の１',kind='399',latest='1',process='01',
        closeDate='',hihyoji='0',nameImageId='',addressImageId='',furigana='')
    addr=fields['prefectureName']+fields['cityName']+fields['streetNumber']
    refs.append(dict(title='人工登録',checked_at=when,fetched_at=when,evidence_role='registered_profile_identity',
        source_kind='government_corporate_register',url='https://www.houjin-bangou.nta.go.jp/download/zenken/index.html',
        page_hash='0fc15a6ca6db74e8b109c8ebda38ec154057ac1f7f2ff26c2c6609eb9ae1f6cd',locator='synthetic CSV row 2',name_raw=name,address_raw=addr,excerpt=name+' / '+addr,
        source_fields=fields,corporate_number=fields['corporateNumber'],csv_row=2,snapshot='20261030',
        file_id='28443',member='28_hyogo_all_20261030.csv',
        registry_state_proof=dict(as_of='20261112',monthly_prefecture_rows=206383,daily_rows=19178,
            daily_resources=[dict(x,fetched_at=when) for x in DAILY_FIXTURE],target_corporate_or_full_parcel_events=0,
            active_shrine_corporation_count_at_full_address=1,
            active_corporate_numbers_at_full_address=[fields['corporateNumber']])))
    v=dict(confirmation='source_review',review_kind='hyogo_profile_name_selection',case_id='synthetic-profile',
        reason='人工資料の実code・全地番・独立登記に基づき詳細表示を選択',recorded_at=when,
        facility_id=f['id'],expected_source_hash=e['source_hash'],original=dict(name_raw=name,reading_raw=kana,address=address,listing_url=url),
        profile_selection_proof=dict(kind='hyogo_typed_profile_registered_name_selection',facility_id=f['id'],entry_id=e['id'],
            expected_source_hash=e['source_hash'],native_code=code,profile_name_raw=name,map_name_raw=m['name_raw'],
            selection='profile_name_and_profile_kana'),references=refs,
        outputs=[dict(surface=name,reading='かくうはちまんじんじゃ',reading_url=url,basis='agency_selected')])
    refs[1]['protocol_reference']=dict(url='https://www.hyogo-jinjacho.com/js/formsearch.js',
        page_hash='e124e51e28043bc10f5a9dec59c71e9c30c0c57851dda691e567f8c7376537f9',
        fetched_at=when,checked_at=when,locator='MarkerSet LocateCode href expression',profile_path_template='data/{code}.html')
    return data,dict(schema_version=1,entries={e['id']:v}),v


class HyogoProfileReviewTest(unittest.TestCase):
    def test_selection_keeps_raw_map_profile_and_hash_and_revalidates_offline(self):
        d,doc,v=fixture();before=copy.deepcopy(d);f=d['facilities'][0];e=d['entries'][0]
        self.assertEqual(review_problems(v,f,e,d['collection']),[])
        out=apply_reviews(d,doc);self.assertEqual(len(eligible(out)),1);self.assertFalse(blocking_problems(out))
        for k in f:
            if k not in ['status','reason']:self.assertEqual(out['facilities'][0][k],f[k])
        for k in ['id','surface','reading_raw','source_hash','reading_url']:self.assertEqual(out['entries'][0][k],e[k])
        self.assertEqual(out['entries'][0]['reading'],'かくうはちまんじんじゃ');self.assertEqual(d,before)
        self.assertEqual(len(eligible(apply_reviews(out,doc))),1)
        out['entries'][0]['human_review']['references'][2]['source_fields']['latest']='0'
        self.assertTrue(blocking_problems(out))

    def test_explicit_registered_kana_can_only_confirm_the_same_whole_reading(self):
        d,doc,v=fixture();r=v['references'][2];kana=d['entries'][0]['reading_raw']
        r['source_fields']['furigana']=kana;r.update(reading_raw=kana,reading_scope='full_name')
        r['excerpt']+=' / '+kana
        self.assertEqual(len(eligible(apply_reviews(d,doc))),1)

    def test_missing_mutated_or_malformed_evidence_stays_pending(self):
        changes=[lambda v:v.pop('profile_selection_proof'),lambda v:v.update(profile_selection_proof=[]),
            lambda v:v['profile_selection_proof'].update(entry_id='other'),
            lambda v:v['profile_selection_proof'].update(native_code='6300002'),
            lambda v:v['profile_selection_proof'].update(selection='map_name_and_profile_kana'),
            lambda v:v['references'].pop(),lambda v:v.update(references={}),
            lambda v:v['references'][0].update(evidence_role=[]),
            lambda v:v['references'][0].update(evidence_role='agency_map'),
            lambda v:v['references'][0].update(page_hash='f'*64),
            lambda v:v['references'][0].update(url='https://['),
            lambda v:v['references'][0].update(printed_code_raw='6300002/兼務'),
            lambda v:v['references'][0].update(reading_raw='ベツジンジャ'),
            lambda v:v['references'][0].update(address_raw='架空市別町1-1'),
            lambda v:v['references'][1].update(code_raw='6300002'),
            lambda v:v['references'][1].update(name_raw='別名神社'),
            lambda v:v['references'][1].update(address_raw='架空市別町1-1'),
            lambda v:v['references'][1].update(excerpt=None),
            lambda v:v['references'][2].update(source_fields=None),
            lambda v:v['references'][2].update(csv_row=True),
            lambda v:v['references'][2].update(snapshot='2026103'),
            lambda v:v['references'][2]['source_fields'].update(name='架空八幡宮'),
            lambda v:v['references'][2]['source_fields'].update(latest='0'),
            lambda v:v['references'][2]['source_fields'].update(process='99'),
            lambda v:v['references'][2]['source_fields'].update(closeDate='2026-10-31'),
            lambda v:v['references'][2]['source_fields'].update(hihyoji='1'),
            lambda v:v['references'][2]['source_fields'].update(nameImageId='001'),
            lambda v:v['references'][2]['source_fields'].update(addressImageId='001'),
            lambda v:v['references'][2]['source_fields'].update(furigana='ベツジンジャ'),
            lambda v:v['references'][2]['source_fields'].update(streetNumber=None),
            lambda v:v['references'][2]['registry_state_proof'].update(active_shrine_corporation_count_at_full_address=2),
            lambda v:v['references'][2]['registry_state_proof'].update(active_corporate_numbers_at_full_address=['other']),
            lambda v:v['references'][2]['registry_state_proof'].update(as_of='20261001'),
            lambda v:v['outputs'][0].update(surface='架空八幡宮'),
            lambda v:v['outputs'][0].update(surface=[]),lambda v:v['outputs'][0].update(reading={}),
            lambda v:v['outputs'][0].update(reading='かくうはちまんぐう'),lambda v:v.update(split=True)]
        for i,change in enumerate(changes):
            with self.subTest(case=i):
                d,doc,v=fixture();change(v);self.assertEqual(eligible(apply_reviews(d,doc)),[])

    def test_invalid_profile_review_does_not_enter_component_split_processing(self):
        for value in [[],{},True]:
            with self.subTest(prefix=value):
                d,doc,v=fixture();v.update(split=True,excluded_name_prefix=value)
                self.assertEqual(eligible(apply_reviews(d,doc)),[])

    def test_non_numeric_locality_glyphs_are_never_nfkc_folded(self):
        for original,registered in [('架空町字塚','架空町字塚'),('架空町ｶ','架空町カ'),('架空町Ａ','架空町A')]:
            with self.subTest(original=original):
                d,doc,v=fixture(original,registered)
                self.assertEqual(eligible(apply_reviews(d,doc)),[])

    def test_registry_daily_window_and_protocol_provenance_are_required_offline(self):
        mutations=[lambda v:v['references'][2]['registry_state_proof'].pop('daily_resources'),
            lambda v:v['references'][2]['registry_state_proof'].update(as_of='20990101'),
            lambda v:v['references'][2]['registry_state_proof'].update(target_corporate_or_full_parcel_events=1),
            lambda v:v['references'][2]['registry_state_proof'].update(daily_rows=1),
            lambda v:v['references'][2]['registry_state_proof']['daily_resources'].pop(),
            lambda v:v['references'][2]['registry_state_proof']['daily_resources'][0].update(url='https://other.example.invalid/'),
            lambda v:v['references'][2]['registry_state_proof']['daily_resources'][0].update(page_hash='f'*64),
            lambda v:v['references'][2]['registry_state_proof']['daily_resources'][0].update(date='20261103'),
            lambda v:v['references'][2]['registry_state_proof']['daily_resources'][0].update(fetched_at='bad'),
            lambda v:v['references'][2]['registry_state_proof']['daily_resources'][0].update(rows=1),
            lambda v:v['references'][1].pop('protocol_reference'),
            lambda v:v['references'][1]['protocol_reference'].update(page_hash='f'*64),
            lambda v:v['references'][1]['protocol_reference'].update(checked_at='2099-01-01T00:00:00+00:00'),
            lambda v:v['references'][0].update(fetched_at='2099-01-01T00:00:00+00:00'),
            lambda v:v['references'][1].update(checked_at='2099-01-01T00:00:00+00:00')]
        for i,mutate in enumerate(mutations):
            with self.subTest(case=i):
                d,doc,v=fixture();mutate(v)
                self.assertEqual(eligible(apply_reviews(d,doc)),[])
                d,doc,v=fixture();out=apply_reviews(d,doc)
                mutate(out['entries'][0]['human_review'])
                self.assertTrue(blocking_problems(out))
                self.assertEqual(eligible(apply_reviews(out,dict(schema_version=1,entries={out['entries'][0]['id']:out['entries'][0]['human_review']}))),[])

    def test_full_parcel_and_literal_aza_must_match(self):
        for street in ['架空町字架空１番地の１０','架空町字架空１番地','架空町１番地の１','架空町字別１番地の１']:
            with self.subTest(street=street):
                d,doc,v=fixture();r=v['references'][2];r['source_fields']['streetNumber']=street
                r['address_raw']='兵庫県架空市'+street;r['excerpt']='架空八幡神社 / '+r['address_raw']
                self.assertEqual(eligible(apply_reviews(d,doc)),[])

    def test_other_identity_conditions_and_original_changes_remain_pending(self):
        for case in ['reason','review_reason','excluded','identity','facility_identity','external_glyph','multi_xml','map_address','stale','authority','source','prefecture']:
            with self.subTest(case=case):
                d,doc,v=fixture();f=d['facilities'][0];e=d['entries'][0]
                if case=='reason':e['reason']='another condition'
                elif case=='review_reason':f['review_reason']='address conflict'
                elif case=='excluded':e.update(status='excluded',reason='excluded')
                elif case=='identity':e['identity_review_required']=True
                elif case=='facility_identity':f['identity_review_required']=True
                elif case=='external_glyph':f['name_rendering_status']='external_glyph'
                elif case=='multi_xml':f['xml_occurrences'].append(copy.deepcopy(f['xml_occurrences'][0]))
                elif case=='map_address':f['map_address_raw']='別町1-1'
                elif case=='stale':f['address']='架空市別町1-1'
                elif case=='authority':d['collection']['authority_status']='unconfirmed'
                elif case=='source':f['source_key']='other'
                elif case=='prefecture':f['prefecture_code']='27'
                self.assertEqual(eligible(apply_reviews(d,doc)),[])
