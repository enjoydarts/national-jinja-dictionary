"""Only two wholly printed readings of one typed formal name may be derived."""
import copy
import hashlib
import unittest
from njd.records import build_dataset
from njd.reviews import apply_reviews,review_problems
from njd.validation import eligible,blocking_problems


def fixture(city_change=False):
    name='架空神社';raw='カクウジンジャ（カキジンジャ）';code='6300001';when='2026-11-13T05:00:00+00:00'
    address='丹波篠山市架空123-4' if city_change else '架空市架空町123-4';display='〒000-0000\n'+address
    url='https://www.hyogo-jinjacho.com/data/'+code+'.html'
    d=build_dataset('hyogo','28','兵庫県','人工神社庁',[dict(name=name,reading_raw=raw,address=address,address_raw=display,url=url,page_hash='a'*64,
        fetched_at=when,locator='header.hero h1; div.kana; div.code strong; dl dt[所在地] + dd',evidence='人工資料',source_id=code)],metadata=dict(authority_status='confirmed'))
    f=d['facilities'][0];e=d['entries'][0];e.update(reading_display_raw=raw,printed_code_raw=code+'/兼務',reason='missing or nonliteral full agency reading')
    mapped='篠山市架空123-4' if city_change else address
    m=dict(url='https://www.hyogo-jinjacho.com/data/xml.php?ne_lat=36&sw_lat=34&ne_lng=136&sw_lng=134',page_hash='b'*64,
        fetched_at=when,locator='Locations/Locate[1]',code_raw=code,name_raw=name,address_raw=mapped,
        protocol_url='https://www.hyogo-jinjacho.com/js/formsearch.js',href_derivation='data/ + actual Locate code + .html')
    f.update(xml_occurrences=[m],map_address_raw=mapped)
    ref=dict(source_kind='agency',source_publisher='人工神社庁',url=url,title='人工資料',page_hash='a'*64,fetched_at=when,checked_at=when,
        locator=f['source_locator'],name_raw=name,reading_raw=raw,address_raw=address,display_address_raw=display,printed_code_raw=code+'/兼務',
        excerpt=name+' / '+raw+' / '+code+'/兼務 / '+display,field_counts=dict(formal_names=1,kana_fields=1,addresses=1,printed_codes=1))
    intervals=[dict(start=0,end=7,raw='カクウジンジャ',reading='かくうじんじゃ'),dict(start=8,end=14,raw='カキジンジャ',reading='かきじんじゃ')]
    proof=dict(kind='agency_same_name_parenthesized_full_readings',entry_id=e['id'],facility_id=f['id'],expected_source_hash=e['source_hash'],
        native_source_id=code,formal_name_raw=name,whole_reading_raw=raw,whole_reading_field='header.hero div.kana',
        profile_url=url,profile_page_hash='a'*64,profile_address=address,profile_address_raw=display,profile_printed_code_raw=code+'/兼務',
        reading_intervals=intervals,delimiters=[dict(start=7,end=8,raw='（'),dict(start=14,end=15,raw='）')],xml_reference=copy.deepcopy(m))
    if city_change:
        from njd.adapters.hyogo import _city_name_comparison,CITY_NAME_CHANGE
        comparison=_city_name_comparison(mapped,address);comparison['profile_address_raw']=display;f['address_comparisons']=[comparison]
        proof['existing_city_name_change']=copy.deepcopy(f['address_comparisons'])
        proof['city_name_change_recheck']=dict(url=CITY_NAME_CHANGE['ordinance_reference']['url'],page_hash='c'*64,fetched_at=when,checked_at=when,
            locator='本則・附則',excerpt='篠山市の名称を丹波篠山市に変更する。 この条例は、平成31年5月1日から施行する。')
    review=dict(case_id='synthetic-same-name-variants',confirmation='source_review',review_kind='same_name_parenthesized_full_readings',facility_id=f['id'],
        expected_source_hash=e['source_hash'],original=dict(name_raw=name,reading_raw=raw,address=address,listing_url=url),recorded_at=when,
        reason='人工資料の同一正式名に明示された2全文かなをそのまま採用',proof=proof,references=[ref],
        outputs=[dict(surface=name,reading=i['reading'],reading_url=url,basis='agency_full_reading_variant',source_reading_raw=i['raw'],source_interval={k:i[k] for k in ['start','end']}) for i in intervals])
    return d,dict(schema_version=1,entries={e['id']:review}),review


class ReadingVariantsTest(unittest.TestCase):
    def test_two_same_name_readings_keep_parent_raw_identity_and_are_idempotent(self):
        # Missing special dispatch either rejects this evidence or overwrites the primary twice.
        for changed in [False,True]:
            with self.subTest(city_change=changed):
                d,doc,v=fixture(changed);before=copy.deepcopy(d);f=d['facilities'][0];e=d['entries'][0]
                self.assertEqual(review_problems(v,f,e,d['collection']),[])
                out=apply_reviews(d,doc);got=eligible(out)
                self.assertFalse(blocking_problems(out));self.assertEqual(len(got),2)
                self.assertEqual({(x['surface'],x['reading']) for x in got},{('架空神社','かくうじんじゃ'),('架空神社','かきじんじゃ')})
                self.assertEqual(len(out['facilities']),1);self.assertEqual(len(out['entries']),3)
                self.assertEqual({x['parent_entry_id'] for x in got},{e['id']});self.assertEqual(len({x['id'] for x in got}),2)
                self.assertNotIn(e['id'],{x['id'] for x in got});self.assertEqual(out['entries'][0]['status'],'excluded')
                for k,value in e.items():
                    if k not in ['status','reason']:self.assertEqual(out['entries'][0][k],value)
                self.assertEqual(out['facilities'],before['facilities']);self.assertEqual(d,before)
                self.assertEqual(apply_reviews(out,doc),out)

    def test_source_intervals_code_and_full_address_cannot_be_changed_independently(self):
        changes=[lambda v:v.update(split=True),lambda v:v['outputs'][0].update(surface='別神社'),
            lambda v:v['outputs'][0].update(reading='かくうじんぐう'),lambda v:v['outputs'][1].update(reading='かくうじんじゃ'),
            lambda v:v['outputs'][0]['source_interval'].update(start=True),lambda v:v['outputs'][0]['source_interval'].update(end=6),
            lambda v:v['proof']['reading_intervals'][0].update(raw='カクウ'),lambda v:v['proof']['delimiters'][0].update(raw='('),
            lambda v:v['proof'].update(native_source_id='6300002'),lambda v:v['proof'].update(entry_id='other'),
            lambda v:v['proof']['xml_reference'].update(address_raw='架空市架空町123-40'),
            lambda v:v['references'][0].update(display_address_raw='〒000-0000\n架空市架空町123-40'),
            lambda v:v['references'][0].update(page_hash='f'*64),lambda v:v['references'][0]['field_counts'].update(kana_fields=2),
            lambda v:v['references'][0].update(fetched_at='2099-01-01T00:00:00+00:00'),lambda v:v.update(accepted_identity_differences=[{}])]
        for i,change in enumerate(changes):
            with self.subTest(i=i):
                d,doc,v=fixture();change(v);self.assertEqual(eligible(apply_reviews(d,doc)),[])

    def test_invalid_proof_reapplication_removes_own_derived_outputs(self):
        d,doc,v=fixture();out=apply_reviews(d,doc);self.assertEqual(len(eligible(out)),2)
        v['proof']['reading_intervals'][1]['start']=7
        again=apply_reviews(out,doc);self.assertEqual(eligible(again),[])
        self.assertEqual(again['entries'][0]['reading_raw'],'カクウジンジャ（カキジンジャ）')

    def test_child_parent_id_reading_and_embedded_evidence_revalidate_offline(self):
        for case in ['parent','id','reading','proof']:
            with self.subTest(case=case):
                d,doc,v=fixture();out=apply_reviews(d,doc);self.assertEqual(len(eligible(out)),2);child=out['entries'][1]
                if case=='parent':child['parent_entry_id']='other'
                elif case=='id':child['id']='other'
                elif case=='reading':child['reading']='かくうじんぐう'
                elif case=='proof':child['human_review']['references'][0]['field_counts']['formal_names']=2
                self.assertTrue(blocking_problems(out))

    def test_other_identity_conditions_exclusions_and_city_difference_are_protected(self):
        for case in ['facility_identity','entry_identity','glyph','address','review_reason','excluded','authority','reading_reason','city_proof','city_parcel']:
            with self.subTest(case=case):
                d,doc,v=fixture(case.startswith('city'));f=d['facilities'][0];e=d['entries'][0]
                if case=='facility_identity':f['identity_review_required']=True
                elif case=='entry_identity':e['identity_review_required']=True
                elif case=='glyph':f['name_rendering_status']='external_glyph'
                elif case=='address':f['address']='架空市架空町123-40'
                elif case=='review_reason':f['review_reason']='another issue'
                elif case=='excluded':e.update(status='excluded',reason='previous exclusion')
                elif case=='authority':d['collection']['authority_status']='unconfirmed'
                elif case=='reading_reason':e['reason']='other condition'
                elif case=='city_proof':v['proof']['city_name_change_recheck']['excerpt']='篠山市'
                elif case=='city_parcel':v['proof']['existing_city_name_change'][0]['unchanged_suffix_raw']='架空123-40'
                self.assertEqual(eligible(apply_reviews(d,doc)),[])

    def test_observation_counts_and_source_intervals_are_real_integers(self):
        for case in ['count','interval','delimiter']:
            with self.subTest(case=case):
                d,doc,v=fixture()
                if case=='count':v['references'][0]['field_counts']['formal_names']=True
                elif case=='interval':v['proof']['reading_intervals'][0]['start']=False
                elif case=='delimiter':v['proof']['delimiters'][0]['start']=7.0
                self.assertEqual(eligible(apply_reviews(d,doc)),[])

    def test_rebound_partial_duplicate_and_nonliteral_punctuation_are_rejected(self):
        # Rebind every hash/quotation/interval so the semantic guard alone must reject it.
        cases=[('カクウ','かくう','カキジンジャ','かきじんじゃ','（','）'),
            ('カクウジンジャ','かくうじんじゃ','カクウジンジャ','かくうじんじゃ','（','）'),
            ('カクウジンジャ','かくうじんじゃ','カキジンジャ','かきじんじゃ','(',')')]
        for first,r1,second,r2,left,right in cases:
            with self.subTest(first=first,second=second,left=left):
                d,doc,v=fixture();f=d['facilities'][0];e=d['entries'][0];raw=first+left+second+right
                digest=hashlib.sha256(('架空神社\0'+raw+'\0'+f['address']).encode()).hexdigest()
                f['source_hash']=e['source_hash']=v['expected_source_hash']=v['proof']['expected_source_hash']=digest
                e.update(reading_raw=raw,reading_display_raw=raw);v['original']['reading_raw']=v['proof']['whole_reading_raw']=raw
                v['references'][0].update(reading_raw=raw,excerpt='架空神社 / '+raw+' / 6300001/兼務 / '+f['address_raw'])
                intervals=[dict(start=0,end=len(first),raw=first,reading=r1),dict(start=len(first)+1,end=len(first)+1+len(second),raw=second,reading=r2)]
                v['proof']['reading_intervals']=intervals;v['proof']['delimiters']=[dict(start=len(first),end=len(first)+1,raw=left),dict(start=len(raw)-1,end=len(raw),raw=right)]
                for o,i in zip(v['outputs'],intervals):o.update(reading=i['reading'],source_reading_raw=i['raw'],source_interval={k:i[k] for k in ['start','end']})
                self.assertTrue(review_problems(v,f,e,d['collection']))
                self.assertEqual(eligible(apply_reviews(d,doc)),[])

    def test_same_source_map_observation_with_a_different_whole_parcel_is_rejected(self):
        d,doc,v=fixture();f=d['facilities'][0];mapped='架空市架空町123-40'
        f['xml_occurrences'][0]['address_raw']=f['map_address_raw']=v['proof']['xml_reference']['address_raw']=mapped
        self.assertEqual(eligible(apply_reviews(d,doc)),[])

    def test_malformed_existing_child_parent_is_reported_without_crashing_reapply(self):
        for parent in [[],{},False]:
            with self.subTest(parent=parent):
                d,doc,v=fixture();out=apply_reviews(d,doc)
                out['entries'][1]['parent_entry_id']=parent
                again=apply_reviews(out,doc)
                self.assertTrue(blocking_problems(again))

    def test_parent_and_both_siblings_must_exist_as_one_approved_group(self):
        for case in ['missing_parent','missing_sibling','parent_status','parent_review']:
            with self.subTest(case=case):
                d,doc,v=fixture();out=apply_reviews(d,doc)
                if case=='missing_parent':out['entries'].pop(0)
                elif case=='missing_sibling':out['entries'].pop()
                elif case=='parent_status':out['entries'][0].update(status='pending',reason='different issue')
                elif case=='parent_review':out['entries'][0]['human_review']['case_id']='different review'
                self.assertTrue(blocking_problems(out));self.assertEqual(eligible(out),[])
