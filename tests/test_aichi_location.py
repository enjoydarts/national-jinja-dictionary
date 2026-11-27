"""The Oguchi API row and its independent parcel witnesses."""

import copy
import unittest

from njd.aichi_location import aichi_location_entry_problems, aichi_location_problems
from njd.locations import apply_locations, raw_address
from njd.validation import blocking_problems, eligible


def fixture():
    api = 'https://aichi-jinjacho.or.jp/index.php/search/shrine'
    facility_id = 'eda99f26-cbf0-5817-89c2-8f217bf74bbf'
    entry_id = 'd6e5cbf8-11c9-5906-9cdf-506a279d0d7a'
    source_hash = 'd11bc38ba5087519627c0abf47fe4900100903cb4d11746127fe40622c6ae0c0'
    original_dt = '2026-11-08T15:00:27.789308+00:00'
    recheck_dt = '2026-11-27T01:08:25.144414+00:00'
    visit_dt = '2026-11-27T01:07:17.793410+00:00'
    registry_dt = '2026-11-27T01:07:17.705962+00:00'
    municipality = '丹羽郡大口町'
    selected = {
        'id': '297f0651-b055-4a25-a48d-1cb2ff73e202',
        'name': '天神社', 'kana': 'てんじんしゃ', 'pref': '愛知県',
        'city': municipality, 'addr': '', 'house_num': '2丁目305番地',
    }
    other = selected | {
        'id': '96a1005c-5242-4978-93d9-aeadbcb6a1ce',
        'kana': 'てんじんじゃ', 'addr': '秋田', 'house_num': '3',
    }
    original = {
        'name_raw': '天神社', 'address': '', 'municipality': municipality,
        'listing_url': api, 'official_site_url': None, 'native_source_id': selected['id'],
    }
    facility = original | {
        'id': facility_id, 'source_key': 'aichi', 'prefecture_code': '23',
        'prefecture': '愛知県', 'listed_name': '天神社', 'source_hash': source_hash,
        'agency': '愛知県神社庁',
        'address_raw': '愛知県丹羽郡大口町2丁目305番地',
        'page_hash': '6ea80a81488dd2d5fa6fa6121dbd8c00441bca332edf4dd86bda9bfaf8c3119c',
        'fetched_at': original_dt,
        'source_locator': 'POST JSON all 69 official area choices, limit=-1 $.list[1] id=' + selected['id'],
        'status': 'pending', 'reason': 'missing name, address or municipality',
    }
    entry = {
        'id': entry_id, 'facility_id': facility_id, 'source_hash': source_hash,
        'page_hash': facility['page_hash'], 'name_raw': '天神社', 'surface': '天神社',
        'listing_url': api, 'reading_url': api, 'reading_source_kind': 'agency',
        'reading': 'てんじんしゃ', 'reading_raw': 'てんじんしゃ',
        'fetched_at': original_dt, 'checked_at': original_dt,
        'evidence': '愛知県神社庁の大口町一覧に天神社と全文かなを記載。',
        'semantic_type': 'proper_noun',
        'status': 'pending', 'reason': 'missing name, address or municipality',
    }
    supplement = {
        'supplement_kind': 'aichi_documented_street', 'status': 'verified',
        'facility_id': facility_id, 'entry_id': entry_id, 'expected_source_hash': source_hash,
        'original': original, 'changes': {'address': '丹羽郡大口町替地2-305'},
        'reason': '現地記事と法人個票の替地2丁目305番地を照合した。',
        'recorded_at': '2026-11-27T01:10:00+00:00',
        'agency_recheck': {
            'url': api, 'request_method': 'POST', 'checked_at': recheck_dt,
            'page_hash': '2ce3ac22a94dc8313d0095bb8a58a3cc28184162c9a8639e3e0b1869908569d0',
            'locator': '$.list、同名2行', 'request_body': {'addr': '大口町', 'limit': -1},
            'retrieved_rows': 20, 'corresponding_name_rows': [selected, other],
        },
        'reference': {
            'url': 'https://owari-nagoya55.hatenablog.com/entry/2025/10/31/000000',
            'page_hash': 'b44adb1f042d13ca1cc5f2431c32adc192bc58d2da0aa1d044c19b088615ffea',
            'name_raw': '天神社', 'address_raw': '丹羽郡大口町替地2-305',
            'source_kind': 'independent_visit_article', 'location_role': 'shrine',
            'locator': '主記事の表題と末尾の所在地', 'fetched_at': visit_dt,
            'excerpt': '丹羽郡大口町替地『天神社』 ／ 所在地　/　丹羽郡大口町替地2-305',
        },
        'registry_reference': {
            'url': 'https://www.houjin-bangou.nta.go.jp/henkorireki-johoto.html?selHouzinNo=3180005009256',
            'page_hash': 'f1d7d64aa9905c8989dc629de98c224a38a4e0c2e076406e07cb93779ea7571d',
            'source_kind': 'government_corporate_profile', 'location_role': 'principal_office',
            'name_raw': '天神社', 'corporate_number': '3180005009256',
            'address_raw': '愛知県丹羽郡大口町替地２丁目３０５番地',
            'locator': '「最新情報」の法人番号・名称・主たる事務所所在地', 'checked_at': registry_dt,
            'excerpt': '最新情報 ／ 法人番号 3180005009256 ／ 天神社 ／ 愛知県丹羽郡大口町替地２丁目３０５番地',
        },
    }
    return supplement, facility, entry


class AichiLocationTest(unittest.TestCase):
    def test_accepts_exact_tenjinsha_witnesses_without_mutating_inputs(self):
        proof, facility, entry = fixture()
        before = copy.deepcopy((proof, facility))
        self.assertEqual(aichi_location_problems(proof, facility), [])
        self.assertEqual(aichi_location_entry_problems(facility, [entry]), [])
        self.assertEqual((proof, facility), before)

    def test_location_stays_bound_to_its_original_snapshot(self):
        mutations = (
            ('entry ID', lambda p, f: p.update(entry_id='another')),
            ('acquired source hash', lambda p, f: f.update(source_hash='a' * 64)),
            ('raw partial address', lambda p, f: f.update(address_raw='愛知県丹羽郡大口町2丁目306番地')),
            ('original municipality', lambda p, f: p['original'].update(municipality='')),
            ('existing address', lambda p, f: f.update(address='丹羽郡大口町秋田3')),
            ('municipality change', lambda p, f: p['changes'].update(municipality='丹羽郡大口町')),
            ('reliable row acquisition', lambda p, f: f.update(page_hash='unknown')),
        )
        for label, mutate in mutations:
            with self.subTest(label=label):
                proof, facility, _ = fixture()
                mutate(proof, facility)
                self.assertTrue(aichi_location_problems(proof, facility))

    def test_api_requires_both_distinct_same_name_rows_from_the_seen_query(self):
        proof, facility, _ = fixture()
        proof['agency_recheck']['corresponding_name_rows'].reverse()
        self.assertEqual(aichi_location_problems(proof, facility), [])
        for label in ('no other row', 'duplicate target', 'changed other address', 'different query', 'row count'):
            with self.subTest(label=label):
                proof, facility, _ = fixture()
                api = proof['agency_recheck']
                rows = api['corresponding_name_rows']
                if label == 'no other row':
                    rows.pop()
                elif label == 'duplicate target':
                    rows[1] = copy.deepcopy(rows[0])
                elif label == 'changed other address':
                    rows[1].update(addr='替地', house_num='2丁目305番地')
                elif label == 'different query':
                    api['request_body'].update(addr='愛知県')
                else:
                    api['retrieved_rows'] = 2
                self.assertTrue(aichi_location_problems(proof, facility))

    def test_witnesses_must_identify_the_complete_same_parcel(self):
        for addr in ('丹羽郡大口町秋田2-305', '丹羽郡大口町替地2-305-1', '丹羽郡大口町替地2-3050'):
            with self.subTest(address=addr):
                proof, facility, _ = fixture()
                proof['reference'].update(address_raw=addr, excerpt=f'天神社 ／ 所在地　/　{addr}')
                proof['changes']['address'] = addr
                self.assertTrue(aichi_location_problems(proof, facility))
        for field, value in (
            ('name_raw', '別社'), ('address_raw', '愛知県丹羽郡大口町替地２丁目３０６番地'),
            ('location_role', 'shrine'), ('corporate_number', '3180005009257'),
        ):
            with self.subTest(field=field):
                proof, facility, _ = fixture()
                proof['registry_reference'][field] = value
                self.assertTrue(aichi_location_problems(proof, facility))

    def test_reapplied_location_preserves_the_acquired_empty_address(self):
        proof, facility, _ = fixture()
        facility.update(proof['changes'], status='verified', reason='',
                        location_supplement=copy.deepcopy(proof) | {'applied': True})
        self.assertEqual(aichi_location_problems(proof, facility), [])
        facility['location_supplement']['original']['address'] = '丹羽郡大口町秋田3'
        self.assertTrue(aichi_location_problems(proof, facility))

    def test_applied_location_retains_municipality_and_makes_the_agency_reading_eligible(self):
        proof, facility, entry = fixture()
        source = {'schema_version': 1, 'collection': {}, 'facilities': [facility], 'entries': [entry]}
        proposals = {'schema_version': 1, 'facilities': {facility['id']: proof}}
        located = apply_locations(source, proposals)
        selected = located['facilities'][0]
        self.assertEqual(selected['municipality'], '丹羽郡大口町')
        self.assertEqual(selected['address'], '丹羽郡大口町替地2-305')
        self.assertEqual(selected['address_raw'], '愛知県丹羽郡大口町2丁目305番地')
        self.assertEqual(raw_address(selected), '')
        self.assertEqual(blocking_problems(located), [])
        self.assertEqual([(row['id'], row['reading']) for row in eligible(located)],
                         [(entry['id'], 'てんじんしゃ')])
        self.assertEqual(apply_locations(located, proposals), located)

    def test_other_readings_do_not_become_eligible_from_this_location(self):
        _, facility, entry = fixture()
        self.assertTrue(aichi_location_entry_problems(facility, []))
        self.assertTrue(aichi_location_entry_problems(facility, [entry, entry | {'id': 'another'}]))
        self.assertTrue(aichi_location_entry_problems(facility, [entry | {
            'reading_raw': 'てんじんじゃ', 'reading': 'てんじんじゃ',
        }]))

    def test_malformed_witnesses_and_dates_fail_closed(self):
        for field in ('reference', 'registry_reference', 'agency_recheck'):
            for bad in (None, [], 1, 'bad'):
                with self.subTest(field=field, value=bad):
                    proof, facility, _ = fixture()
                    proof[field] = bad
                    self.assertTrue(aichi_location_problems(proof, facility))
        proof, facility, _ = fixture()
        proof['reference']['fetched_at'] = '2026-11-27T01:07:17.793410'
        self.assertTrue(aichi_location_problems(proof, facility))
