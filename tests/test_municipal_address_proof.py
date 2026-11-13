"""Synthetic shrine/parcel fixtures; government examples prove prefixes only."""
import copy
import unittest
from test_records import row
from test_corrections import correction
from njd.records import build_dataset
from njd.corrections import apply_corrections
from njd.validation import eligible

EXAMPLES=[
 ('佐賀郡諸富町','佐賀市諸富町',1,'2005-10-01','大字諸富津'),
 ('佐賀郡大和町','佐賀市大和町',1,'2005-10-01','大字尼寺'),
 ('佐賀郡富士町','佐賀市富士町',1,'2005-10-01','大字古湯'),
 ('神埼郡三瀬村','佐賀市三瀬村',1,'2005-10-01','大字三瀬'),
 ('佐賀郡川副町','佐賀市川副町',2,'2007-10-01','大字鹿江'),
 ('佐賀郡東与賀町','佐賀市東与賀町',2,'2007-10-01','大字下古賀'),
 ('佐賀郡久保田町','佐賀市久保田町',2,'2007-10-01','大字新田'),
 ('小城郡小城町','小城市小城町',1,'2005-03-01','大字畑田'),
 ('神埼郡千代田町','神埼市千代田町',2,'2006-03-20','大字直鳥'),
]


def fixture(rule=EXAMPLES[4],suffix='大字架空123-4'):
 old,new,page,date,example=rule
 old_example=old+example+'○○番地'
 new_example=new+example.removeprefix('大字')+'○○番地' if old in ('神埼郡三瀬村','小城郡小城町','神埼郡千代田町') else new+example+'○○番地'
 d=build_dataset('saga_fixture','41','佐賀県','架空県神社庁',
     [row(name='架空神社',reading_raw='',address=old+suffix)])
 c=correction(d,{'reading':'かくうじんじゃ'});f=d['facilities'][0];e=d['entries'][0]
 ref=c['entries'][e['id']]['references'][0]
 ref.update(page_hash='b'*64,address_raw='佐賀県'+new+suffix,
            excerpt='架空神社（かくうじんじゃ） 佐賀県'+new+suffix)
 ref['address_identity_proof']=dict(kind='documented_municipality_prefix_change',
     facility_id=f['id'],entry_id=e['id'],expected_source_hash=e['source_hash'],
     listing_address_raw=f['address'],reference_address_raw=ref['address_raw'],
     reference_url=ref['url'],reference_page_hash=ref['page_hash'],
     change_reference=dict(url='https://www.pref.saga.lg.jp/kiji00329259/3_29259_6_chouazamei.pdf',
         page_hash='19ef4a4d2ff1ece43a6e2bb8ef9822b1766f77367cf9528c5cfc47dcac100308',
         source_publisher='佐賀県',pdf_page=page,effective_date=date,
         former_example_raw=old_example,current_example_raw=new_example,
         locator=f'{page}ページ 合併後住所表示例',
         fetched_at='2026-11-13T00:00:00+09:00',checked_at='2026-11-13T00:01:00+09:00'))
 return d,c,ref


class MunicipalAddressProofTest(unittest.TestCase):
    def test_evidenced_prefix_change_allows_reading_and_preserves_acquired_address(self):
        d,c,ref=fixture();before=copy.deepcopy(d);out=apply_corrections(d,c)
        self.assertEqual(len(eligible(out)),1)
        self.assertEqual(out['entries'][0]['reading'],'かくうじんじゃ')
        self.assertEqual(out['facilities'][0]['address'],'佐賀郡川副町大字架空123-4')
        self.assertEqual(out['entries'][0]['reading_raw'],'')
        self.assertEqual(out['facilities'][0]['id'],before['facilities'][0]['id'])
        self.assertEqual(d,before)

    def test_documented_prefixes_accept_only_the_matching_page_example(self):
        for rule in EXAMPLES:
            with self.subTest(prefix=rule[0]):
                d,c,ref=fixture(rule);self.assertEqual(len(eligible(apply_corrections(d,c))),1)

    def test_ogi_chiyoda_preserve_original_and_reject_wrong_evidence_or_parcel(self):
        for rule in EXAMPLES[-2:]:
            with self.subTest(prefix=rule[0]):
                d,c,ref=fixture(rule);before=copy.deepcopy(d)
                out=apply_corrections(d,c)
                self.assertEqual(len(eligible(out)),1)
                self.assertEqual(out['facilities'],before['facilities'])
                self.assertEqual(out['entries'][0]['reading_raw'],'')
                self.assertEqual(out['entries'][0]['reading'],'かくうじんじゃ')
            for mutation in ['missing','page','date','example','parcel','locality','glyph']:
                with self.subTest(prefix=rule[0],mutation=mutation):
                    d,c,ref=fixture(rule)
                    proof=ref['address_identity_proof'];change=proof['change_reference']
                    if mutation=='missing':ref.pop('address_identity_proof')
                    elif mutation=='page':change['pdf_page']=3-rule[2]
                    elif mutation=='date':change['effective_date']='2005-10-01'
                    elif mutation=='example':change['current_example_raw']='小城市小城町池上○○番地'
                    else:
                        suffix={'parcel':'大字架空123-40','locality':'大字別所123-4','glyph':'大字架空字別所123-4'}[mutation]
                        ref['address_raw']='佐賀県'+rule[1]+suffix
                        proof['reference_address_raw']=ref['address_raw']
                        ref['excerpt']='架空神社（かくうじんじゃ） '+ref['address_raw']
                    self.assertEqual(eligible(apply_corrections(d,c)),[])

    def test_ogi_prefix_does_not_authorize_old_locality_glyph_changes(self):
        d,c,ref=fixture(EXAMPLES[-2],suffix='大字晴氣123-4')
        ref['address_raw']='佐賀県小城市小城町晴気123-4'
        ref['excerpt']='架空神社（かくうじんじゃ） '+ref['address_raw']
        ref['address_identity_proof']['reference_address_raw']=ref['address_raw']
        self.assertEqual(eligible(apply_corrections(d,c)),[])

    def test_missing_or_unbound_evidence_leaves_entry_pending(self):
        mutations=[
            lambda r:r.pop('address_identity_proof'),
            lambda r:r.update(address_identity_proof=None),
            lambda r:r.update(address_identity_proof=[]),
            lambda r:r['address_identity_proof'].update(kind='assumed_merger'),
            lambda r:r['address_identity_proof'].update(facility_id='other'),
            lambda r:r['address_identity_proof'].update(entry_id='other'),
            lambda r:r['address_identity_proof'].update(expected_source_hash='d'*64),
            lambda r:r['address_identity_proof'].update(listing_address_raw='別住所123-4'),
            lambda r:r['address_identity_proof'].update(reference_address_raw='別住所123-4'),
            lambda r:r['address_identity_proof'].update(reference_url='https://other.invalid/'),
            lambda r:r['address_identity_proof'].update(reference_page_hash='c'*64),
            lambda r:r['address_identity_proof'].pop('change_reference'),
            lambda r:r['address_identity_proof'].update(change_reference=[]),
            lambda r:r['address_identity_proof']['change_reference'].update(url='https://example.invalid/same.pdf'),
            lambda r:r['address_identity_proof']['change_reference'].update(page_hash='d'*64),
            lambda r:r['address_identity_proof']['change_reference'].update(source_publisher='民間資料'),
            lambda r:r['address_identity_proof']['change_reference'].update(pdf_page=1),
            lambda r:r['address_identity_proof']['change_reference'].update(effective_date='2005-10-01'),
            lambda r:r['address_identity_proof']['change_reference'].update(former_example_raw='佐賀郡川副町大字架空123-4'),
            lambda r:r['address_identity_proof']['change_reference'].update(current_example_raw='佐賀市川副町大字架空123-4'),
            lambda r:r['address_identity_proof']['change_reference'].update(locator=''),
            lambda r:r['address_identity_proof']['change_reference'].update(fetched_at='2026-11-13'),
            lambda r:r['address_identity_proof']['change_reference'].update(checked_at='invalid'),
        ]
        for i,mutate in enumerate(mutations):
            with self.subTest(case=i):
                d,c,ref=fixture();mutate(ref)
                self.assertEqual(eligible(apply_corrections(d,c)),[])

    def test_mapping_cannot_hide_different_parcel_or_locality(self):
        for current in ['佐賀県佐賀市川副町大字架空123-40','佐賀県佐賀市川副町大字架空123',
                        '佐賀県佐賀市川副町大字別所123-4','佐賀県佐賀市川副町大字架空字別所123-4',
                        '佐賀県佐賀市川副町大字架空123-4-1']:
            with self.subTest(address=current):
                d,c,ref=fixture();ref['address_raw']=current
                ref['excerpt']='架空神社（かくうじんじゃ） '+current
                ref['address_identity_proof']['reference_address_raw']=current
                self.assertEqual(eligible(apply_corrections(d,c)),[])

    def test_locality_without_original_parcel_cannot_identify_new_parcel(self):
        d,c,ref=fixture(suffix='大字架空');ref['address_raw']+='123-4'
        ref['excerpt']='架空神社（かくうじんじゃ） '+ref['address_raw']
        ref['address_identity_proof']['reference_address_raw']=ref['address_raw']
        self.assertEqual(eligible(apply_corrections(d,c)),[])

    def test_numbers_only_in_chome_or_district_names_do_not_prove_a_parcel(self):
        for suffix in ['大字架空１丁目','第1区','大字架空1番町']:
            with self.subTest(suffix=suffix):
                d,c,ref=fixture(suffix=suffix)
                self.assertEqual(eligible(apply_corrections(d,c)),[])

    def test_chome_followed_by_a_complete_house_number_keeps_all_units(self):
        d,c,ref=fixture(suffix='大字架空１丁目２番３号')
        self.assertEqual(len(eligible(apply_corrections(d,c))),1)
        self.assertEqual(apply_corrections(d,c)['facilities'][0]['address'],
                         '佐賀郡川副町大字架空１丁目２番３号')

    def test_other_prefecture_or_unknown_former_prefix_remains_pending(self):
        for code,prefix in [('40','佐賀郡川副町'),('41','佐賀郡架空町')]:
            with self.subTest(code=code,prefix=prefix):
                d,c,ref=fixture();f=d['facilities'][0];f['prefecture_code']=code
                if prefix!='佐賀郡川副町':
                    f['address']=prefix+'大字架空123-4'
                    ref['address_identity_proof']['listing_address_raw']=f['address']
                    c['entries'][d['entries'][0]['id']]['original']['address']=f['address']
                self.assertEqual(eligible(apply_corrections(d,c)),[])

    def test_reading_proof_does_not_authorize_a_name_change(self):
        d,c,ref=fixture();v=c['entries'][d['entries'][0]['id']]
        v['changes']['surface']='別名神社';ref['name_raw']='別名神社'
        ref['excerpt']='別名神社（かくうじんじゃ） '+ref['address_raw']
        self.assertEqual(eligible(apply_corrections(d,c)),[])
