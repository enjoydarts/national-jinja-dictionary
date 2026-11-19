"""Regression tests for the municipality-only exception for the inspected row."""
import copy
import hashlib
import unittest

from njd.locations import apply_locations, location_problems
from njd.validation import blocking_problems, eligible


def fixture():
    name, kana, code = '東外城田神社', 'ひがしときだじんじゃ', '4208002'
    town, address = '度会郡玉城町', '三重県度会郡玉城蚊野2218-2'
    full_address = '度会郡玉城町蚊野2218-2'
    profile = ('https://kyoka.mie-jinjacho.or.jp/shrine/'
               '%e6%9d%b1%e5%a4%96%e5%9f%8e%e7%94%b0%e7%a5%9e%e7%a4%be/')
    fid, eid = '854451cc-c896-5a37-bfd7-9360567bebec', '623ef6a4-bf2c-5f25-84f0-094a945b6606'
    digest = hashlib.sha256('\0'.join((name, kana, address)).encode()).hexdigest()
    acquired, observed, recorded = ('2026-11-09T06:11:55.801644+00:00',
                                   '2026-11-19T12:13:24.724203+00:00',
                                   '2026-11-19T13:00:00+00:00')
    acquired_hash = 'f8236e7e84a02fef101e23ae23d6b80922ccdd78973caaf7b0ad2014098bfdb3'
    locator = 'div.shrine_detail h2; span.furigana; table.table_03 th=神社コード/鎮座地'
    original = dict(name_raw=name, address=address, municipality='', listing_url=profile,
                    native_source_id=code, official_site_url=None)
    raw = dict(source_hash=digest, page_hash=acquired_hash, listing_url=profile, name_raw=name,
               status='pending', reason='missing name, address or municipality', fetched_at=acquired,
               checked_at=acquired)
    facility = dict(raw, **{k: v for k, v in original.items() if k not in raw}, id=fid,
                    address_raw=address, source_locator=locator, source_key='mie', prefecture='三重県',
                    prefecture_code='24', listed_name=name, agency='三重県神社庁')
    entry = dict(raw, id=eid, facility_id=fid, reading=kana, reading_raw=kana, source_reading_raw=kana,
                 surface=name, reading_url=profile, reading_source_kind='agency', semantic_type='proper_noun',
                 evidence=f'{name} / {kana} / {code} / {address}')
    data = dict(schema_version=1, facilities=[facility], entries=[entry],
                collection=dict(source_key='mie', authority_status='confirmed'))
    register_url = 'https://www.houjin-bangou.nta.go.jp/download/zenken/index.html'
    daily_url = 'https://www.houjin-bangou.nta.go.jp/download/sabun/index.html'
    dates = (2, 4, 5, 6, 9, 10, 11, 12, 13, 16, 17, 18, 19)
    counts = (2346, 2156, 2183, 2617, 2362, 2642, 2692, 2180, 2548, 2372, 2183, 2483, 2035)
    daily = [dict(snapshot=f'202611{day:02}', file_id=str(28508 + 3 * i), rows=count,
                  member=f'diff_202611{day:02}.csv', url=daily_url, response_url=daily_url,
                  page_hash='a' * 64, checked_at=observed)
             for i, (day, count) in enumerate(zip(dates, counts))]
    national = dict(as_of='20261119', daily_rows=sum(counts), daily=daily,
                    related_daily_events=0, checked_at='2026-11-19T12:20:54.718894+00:00',
                    monthly=dict(snapshot='20261030', file_id='28429', member='24_mie_all_20261030.csv',
                                 prefecture_code='24', checked_at=observed, rows=57194,
                                 page_hash='8afbf798651c6d2057b0cde1a30004e342857b10ae73b9425dd72a3a2fe96131',
                                 url=register_url, response_url=register_url),
                    related_monthly_active_rows=[dict(csv_row=43732, zip_member='24_mie_all_20261030.csv',
                        source_fields=dict(sequenceNumber='43732', corporateNumber='7190005004962',
                            name=name, prefectureName='三重県', prefectureCode='24', cityCode='461', cityName=town,
                            streetNumber='蚊野２２１８番地の２', postCode='5190431', kind='399', latest='1',
                            closeDate='', process='01', hihyoji='0', nameImageId='', addressImageId='', furigana=''))])
    supplement = dict(
        supplement_kind='mie_registered_municipality', status='verified', facility_id=fid, entry_id=eid,
        expected_source_hash=digest, original=original, changes=dict(municipality=town), recorded_at=recorded,
        reason='市町村だけを補完し、野篠表記を別に保持する。',
        profile_original=dict(address_raw=address, name_raw=name, native_source_id=code, reading_raw=kana,
                              listing_url=profile, source_locator=locator, source_hash=digest,
                              page_hash=acquired_hash, fetched_at=acquired, excerpt=entry['evidence']),
        profile_rechecked=dict(address_raw=address, name_raw=name, native_source_id=code, reading_raw=kana,
                               url=profile, locator=locator, source_kind='agency', checked_at=observed,
                               page_hash='6f82da1d989ec039f3dcd433e2fb46cf49f4208cd6899c3154af965d71bb0f85',
                               excerpt=entry['evidence']),
        reference=dict(url='https://www.pref.mie.lg.jp/common/content/001217775.pdf',
                       page_hash='3807c96fd1480bc36e508b1e5102d9c6cfa1749c34ba7321cdeb155747e71830',
                       source_kind='government_religious_corporation_register',
                       source_publisher='三重県環境生活部文化振興課', checked_at=observed, fetched_at=observed,
                       name_raw=name, address_raw=full_address, as_of='2026-05-01', municipality_raw=town,
                       prefectural_heading_raw='玉城町', pdf_page_index=113, printed_page=111, printed_record_number=2,
                       locator='PDF 114枚目 / 印刷111頁 / 玉城町 / 番号2 / 宗教法人名・所在地列',
                       excerpt=f'玉城町、番号2、宗教法人名={name}、所在地={full_address}'),
        tourism_reference=dict(url='https://www.kankomie.or.jp/spot/23890',
                               page_hash='c6a9c970827298b304ff78760aac5e9607ebd8bc9aef03e8e4a239d0e567fe26',
                               checked_at=observed, source_kind='tourism_organization',
                               source_publisher='公益社団法人三重県観光連盟', name_raw=name, address_raw=full_address,
                               reading_raw='ヒガシトキダジンジャ', locator='住所欄',
                               excerpt=f'{name} ヒガシトキダジンジャ / 住所=〒519-0431 {full_address}'),
        national_registry_reference=national,
        unresolved_other_address=dict(url='https://kizuna.town.tamaki.mie.jp/chosei/shokai/documents/goriyaku.pdf',
                                     address_raw='玉城町野篠 2218-2', source_kind='government_tourism_booklet',
                                     scope='町域表記の相違を保持する。'))
    return data, dict(schema_version=1, facilities={fid: supplement}), supplement


class MieMunicipalityTests(unittest.TestCase):
    def test_verified_municipality_preserves_acquired_address_kana_and_other_observation(self):
        data, document, supplement = fixture()
        before = copy.deepcopy(data)
        result = apply_locations(data, document)
        facility, = result['facilities']
        entry, = result['entries']
        self.assertEqual(facility['municipality'], '度会郡玉城町')
        self.assertEqual(facility['address'], '三重県度会郡玉城蚊野2218-2')
        self.assertEqual(facility['address_raw'], facility['address'])
        self.assertEqual(entry['reading_raw'], 'ひがしときだじんじゃ')
        self.assertEqual(entry['reading'], entry['reading_raw'])
        self.assertEqual(facility['source_hash'], before['facilities'][0]['source_hash'])
        self.assertEqual(entry['source_hash'], before['entries'][0]['source_hash'])
        self.assertEqual(facility['location_supplement']['unresolved_other_address'],
                         supplement['unresolved_other_address'])
        self.assertEqual(blocking_problems(result), [])
        self.assertEqual(len(eligible(result)), 1)
        self.assertEqual(apply_locations(result, document), result)
        self.assertEqual(data, before)

    def test_wrong_town_row_branch_or_stale_source_leaves_original_on_reapplication(self):
        changes = {
            'proposed town': lambda s: s['changes'].update(municipality='度会郡度会町'),
            'address rewrite': lambda s: s['changes'].update(address='三重県度会郡玉城町蚊野2218-2'),
            'stale source': lambda s: s.update(expected_source_hash='a' * 64),
            'profile branch': lambda s: s['profile_rechecked'].update(address_raw='三重県度会郡玉城蚊野2218'),
            'wrong printed row': lambda s: s['reference'].update(printed_record_number=3),
            'adjacent parcel': lambda s: s['reference'].update(address_raw='度会郡玉城町蚊野2218-20'),
            'wrong independent town': lambda s: s['tourism_reference'].update(address_raw='度会郡度会町蚊野2218-2'),
            'wrong registry row': lambda s: s['national_registry_reference']['related_monthly_active_rows'][0]
                                           .update(csv_row=43733),
            'wrong registry branch': lambda s: s['national_registry_reference']['related_monthly_active_rows'][0]
                                              ['source_fields'].update(streetNumber='蚊野２２１８番地の３'),
            'later registry event': lambda s: s['national_registry_reference'].update(related_daily_events=1),
            'uninspected registry day': lambda s: s['national_registry_reference']['daily'].pop(),
            'erased conflicting observation': lambda s: s.pop('unresolved_other_address'),
            'different booklet locality': lambda s: s['unresolved_other_address'].update(address_raw='玉城町蚊野 2218-2'),
            'malformed evidence': lambda s: s.update(reference=None),
        }
        for label, change in changes.items():
            with self.subTest(label=label):
                data, document, supplement = fixture()
                accepted = apply_locations(data, document)
                self.assertEqual(len(eligible(accepted)), 1)
                change(supplement)
                self.assertTrue(location_problems(supplement, data['facilities'][0], data['collection']))
                rejected = apply_locations(accepted, document)
                facility, = rejected['facilities']
                self.assertEqual(facility['municipality'], '')
                self.assertEqual(facility['address'], '三重県度会郡玉城蚊野2218-2')
                self.assertEqual(eligible(rejected), [])

    def test_different_original_registration_keeps_facility_on_hold(self):
        for changes in (dict(id='different-registration'), dict(reading_raw='ひがしときだしゃ'),
                        dict(source_reading_raw='ひがしときだしゃ'), dict(reason='unrelated review'),
                        dict(status='excluded', reason='excluded')):
            with self.subTest(changes=changes):
                data, document, _ = fixture()
                self.assertEqual(len(eligible(apply_locations(data, document))), 1)
                data['entries'][0].update(changes)
                result = apply_locations(data, document)
                self.assertEqual(result['facilities'][0]['municipality'], '')
                self.assertEqual(eligible(result), [])

    def test_same_acquired_row_survives_a_new_page_hash(self):
        data, document, _ = fixture()
        observed = (data['facilities'][0], data['entries'][0])
        for row in observed:
            row['page_hash'] = 'b' * 64
        self.assertEqual(len(eligible(apply_locations(data, document))), 1)

        for row in observed:
            row['page_hash'] = 'invalid'
        result = apply_locations(data, document)
        self.assertFalse(result['facilities'][0]['location_supplement']['applied'])
