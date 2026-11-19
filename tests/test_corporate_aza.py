import copy
import unittest

from njd.corrections import apply_corrections, correction_problems
from njd.corporate import BASE, FIELDS
from test_corporate import META, row, target


def example():
    t = target()
    f, e = t['facility'], t['entry']
    f['address'] = '鳥取市大覚寺裏谷76-2'
    f['source_hash'] = e['source_hash'] = 'e' * 64
    fields = dict(zip(FIELDS, row(streetNumber='大覚寺小字裏谷７６番地の２')))
    address = '鳥取県鳥取市大覚寺小字裏谷７６番地の２'
    ref = dict(META, title='国税庁法人番号公表サイト', source_kind='government_corporate_register',
               name_raw=fields['name'], reading_raw=fields['furigana'], address_raw=address,
               excerpt=f"{fields['name']} / {fields['furigana']} / {address}",
               corporate_number=fields['corporateNumber'], source_fields=fields, csv_row=1)
    ref['address_identity_proof'] = dict(
        kind='registered_abr_town_spelling', expected_source_hash=e['source_hash'],
        agency_address_raw=f['address'], registry_page_hash=ref['page_hash'],
        registry_csv_row=ref['csv_row'], town_master=dict(
            url='https://data.address-br.digital.go.jp/mt_town/mt_town_all.csv.zip',
            license_url='https://www.digital.go.jp/policies/base_registry_address_tos',
            member='mt_town_all.csv', checked_at=ref['checked_at'], page_hash='b' * 64,
            row=dict(csv_row=2, lg_code='312011', machiaza_id='0061002', machiaza_type='3',
                     pref='鳥取県', county='', city='鳥取市', ward='', oaza_cho='大覚寺',
                     chome='', koaza='裏谷', status_flg='1', efct_date='1947-01-01', ablt_date='')))
    proposal = dict(status='verified', facility_id=f['id'], expected_source_hash=e['source_hash'],
                    original=dict(name_raw=f['name_raw'], reading_raw='', address=f['address'],
                                  listing_url=f['listing_url']),
                    changes={'reading': 'まえだじんじゃ'}, references=[ref],
                    reason='同じ町字と全地番', identity_match='同名同一地番')
    return proposal, (f, e, t['source'])


class CorporateAzaTest(unittest.TestCase):
    def test_literal_kana_and_same_abr_town_and_full_parcel(self):
        proposal, target = example()
        self.assertEqual(correction_problems(proposal, *target), [])

    def test_inconsistent_address_witness_cannot_be_bypassed(self):
        proposal, target = example()
        changes = (
            ('ref', 'url', BASE + '/download/other.html'),
            ('ref', 'csv_row', 3),
            ('fields', 'cityCode', '202'),
            ('proof', 'agency_address_raw', '鳥取市大覚寺裏谷76-3'),
            ('row', 'lg_code', '312020'),
            ('row', 'koaza', '字谷'),
            ('row', 'ablt_date', '2025-01-01'),
        )
        for group, key, value in changes:
            with self.subTest(group=group, key=key):
                bad = copy.deepcopy(proposal)
                ref = bad['references'][0]
                proof = ref['address_identity_proof']
                groups = dict(ref=ref, fields=ref['source_fields'], proof=proof,
                              row=proof['town_master']['row'])
                groups[group][key] = value
                without_proof = {k: v for k, v in ref.items() if k != 'address_identity_proof'}
                without_proof.update(address_raw=target[0]['address'], excerpt='前田神社 マエダジンジャ 鳥取市大覚寺裏谷76-2')
                bad['references'].append(without_proof)
                self.assertTrue(correction_problems(bad, *target))

    def test_another_branch_is_never_the_same_address(self):
        proposal, target = example()
        ref = proposal['references'][0]
        ref['source_fields']['streetNumber'] = ref['source_fields']['streetNumber'].replace('２', '３')
        ref['address_raw'] = ref['address_raw'].replace('２', '３')
        ref['excerpt'] = ref['excerpt'].replace('２', '３')
        self.assertTrue(correction_problems(proposal, *target))

    def test_both_addresses_print_the_same_koaza(self):
        proposal, target = example()
        f, _, _ = target
        ref = proposal['references'][0]
        proof = ref['address_identity_proof']
        f['address'] = '鳥取市大覚寺小字裏谷76-2'
        proposal['original']['address'] = f['address']
        proof['agency_address_raw'] = f['address']
        proof['shared_koaza_raw'] = '小字裏谷'
        proof['town_master']['row'].update(oaza_cho='字大覚寺', koaza='', machiaza_type='1')
        ref['source_fields']['streetNumber'] = '字' + ref['source_fields']['streetNumber']
        ref['address_raw'] = ref['address_raw'].replace('大覚寺', '字大覚寺')
        ref['excerpt'] = ref['excerpt'].replace('大覚寺', '字大覚寺')
        self.assertEqual(correction_problems(proposal, *target), [])
        proof['shared_koaza_raw'] = '小字裏'
        self.assertTrue(correction_problems(proposal, *target))

    def test_an_excluded_entry_stays_excluded_after_reapplication(self):
        proposal, (facility, entry, source) = example()
        entry['status'] = 'excluded'
        entry['reason'] = 'prior exclusion'
        data = dict(facilities=[facility], entries=[entry], collection=source)
        corrections = dict(schema_version=1, entries={entry['id']: proposal})
        first = apply_corrections(data, corrections)
        second = apply_corrections(first, corrections)
        self.assertEqual(second['entries'][0]['status'], 'excluded')
        self.assertEqual(second['entries'][0]['reason'], 'prior exclusion')
