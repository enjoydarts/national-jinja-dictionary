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


ISAHAYA_CASES = (
    ('諫早市高来町船津名', '諫早市高来町船津', '北高来郡高来町', '船津名', '859-0105', '1423431',
     '7268addacd3cdc04caa3427c20cb54866f98c63b792cc931bfb63a926d6db8a5'),
    ('諫早市森山町大字森山本村名', '諫早市森山町本村', '北高来郡森山町', '森山本村名', '854-0203', '1423411',
     '2a134ed6fb6dee34b1afc2831e3a5b93ee61ed28e52a372251debbecb8088834'),
)


def isahaya_fixture(case, parcel='123番地4'):
    acquired, current, former_city, former_town, postcode, city_code, digest = case
    dataset = build_dataset('nagasaki', '42', '長崎県', '長崎県神社庁',
                            [row(name='架空神社', reading_raw='', address=acquired+parcel)])
    facility, entry = dataset['facilities'][0], dataset['entries'][0]
    proposal = correction(dataset, {'reading':'かくうじんじゃ'})
    reference = proposal['entries'][entry['id']]['references'][0]
    reference.update(page_hash='b'*64, reading_scope='full_name', address_raw='長崎県'+current+parcel,
                     excerpt='架空神社（かくうじんじゃ） 長崎県'+current+parcel)
    reference['address_identity_proof'] = dict(
        kind='documented_isahaya_locality_change', facility_id=facility['id'], entry_id=entry['id'],
        expected_source_hash=entry['source_hash'], listing_address_raw=facility['address'],
        reference_address_raw=reference['address_raw'], reference_url=reference['url'],
        reference_page_hash=reference['page_hash'], change_reference=dict(
            url='https://www.post.japanpost.jp/cgi-zip/zipcode.php?addr=&city='+city_code+'&cmp=1&mode=list&pref=42',
            page_hash=digest, source_publisher='日本郵便株式会社', effective_date='2005-03-01',
            former_municipality_raw=former_city, former_locality_raw=former_town,
            current_locality_raw=current, postal_code_raw=postcode, locator='住所等の変更情報',
            checked_at='2026-11-25T07:45:25+00:00'))
    return dataset, proposal, reference


class IsahayaLocalityProofTest(unittest.TestCase):
    def test_documented_localities_match_full_parcel_and_preserve_the_acquired_record(self):
        for case in ISAHAYA_CASES:
            with self.subTest(locality=case[0]):
                dataset, proposal, _ = isahaya_fixture(case)
                before = copy.deepcopy(dataset)
                updated = apply_corrections(dataset, proposal)
                self.assertEqual(len(eligible(updated)), 1)
                self.assertEqual(updated['entries'][0]['reading'], 'かくうじんじゃ')
                self.assertEqual(updated['facilities'], before['facilities'])
                self.assertEqual(updated['entries'][0]['reading_raw'], '')
                self.assertEqual(dataset, before)

    def test_different_street_or_parcel_cannot_use_the_documented_match(self):
        case = ISAHAYA_CASES[0]
        for address in ('諫早市高来町船津123番地40', '諫早市高来町船津123番地', '諫早市高来町小船津123番地4'):
            with self.subTest(address=address):
                dataset, proposal, reference = isahaya_fixture(case)
                reference['address_raw'] = address
                reference['excerpt'] = '架空神社（かくうじんじゃ） '+address
                reference['address_identity_proof']['reference_address_raw'] = address
                self.assertEqual(eligible(apply_corrections(dataset, proposal)), [])

    def test_an_unbound_or_different_postal_row_leaves_the_reading_pending(self):
        case = ISAHAYA_CASES[1]
        mutations = (
            lambda ref: ref.pop('address_identity_proof'),
            lambda ref: ref.update(reading_scope='partial'),
            lambda ref: ref['address_identity_proof'].update(expected_source_hash='d'*64),
            lambda ref: ref['address_identity_proof']['change_reference'].update(effective_date='2005-04-01'),
            lambda ref: ref['address_identity_proof']['change_reference'].update(postal_code_raw='854-0204'),
            lambda ref: ref['address_identity_proof']['change_reference'].update(page_hash='c'*64),
            lambda ref: ref['address_identity_proof']['change_reference'].update(checked_at='2026-11-25'),
        )
        for mutate in mutations:
            dataset, proposal, reference = isahaya_fixture(case)
            mutate(reference)
            self.assertEqual(eligible(apply_corrections(dataset, proposal)), [])

    def test_the_proof_cannot_clear_an_exclusion_or_match_a_place_without_a_parcel(self):
        dataset, proposal, _ = isahaya_fixture(ISAHAYA_CASES[0])
        dataset['entries'][0]['status'] = 'excluded'
        updated = apply_corrections(dataset, proposal)
        self.assertEqual(updated['entries'][0]['status'], 'excluded')
        self.assertEqual(eligible(updated), [])

        dataset, proposal, reference = isahaya_fixture(ISAHAYA_CASES[0], parcel='')
        reference['address_raw'] += '123番地'
        reference['excerpt'] += '123番地'
        reference['address_identity_proof']['reference_address_raw'] = reference['address_raw']
        self.assertEqual(eligible(apply_corrections(dataset, proposal)), [])
