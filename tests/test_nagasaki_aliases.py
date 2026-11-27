import unittest

from njd.nagasaki_aliases import KIND, resolution_problems


class NagasakiAliasTests(unittest.TestCase):
    def test_missing_members_require_review(self):
        self.assertTrue(resolution_problems({'kind': KIND}, None, {}))

    def test_same_name_and_url_spelling_are_insufficient(self):
        primary = {'id': 'region', 'name_raw': '阿蘇神社',
                   'official_site_url': 'http://asojinja.jp/'}
        duplicate = {'id': 'legacy', 'name_raw': '阿蘇神社',
                     'official_site_url': 'http://www.asojinja.jp/'}
        record = {'kind': KIND, 'primary_id': primary['id'], 'duplicate_id': duplicate['id']}
        self.assertTrue(resolution_problems(record, primary, duplicate))

    def test_same_bytes_and_independent_precinct_address_are_accepted(self):
        args = aso_alias()
        self.assertEqual(resolution_problems(*args), [])

    def test_office_parcel_cannot_replace_shrine_parcel(self):
        record, primary, duplicate = aso_alias()
        primary['address'] = record['snapshots']['primary']['address'] = '諫早市多良見町化屋862番地'
        record['evidence'][1]['address_raw'] = primary['address']
        self.assertTrue(resolution_problems(record, primary, duplicate))

    def test_both_publisher_bodies_and_public_precinct_witness_are_required(self):
        for failed_part in ('body hash', 'independent witness', 'receipt URL', 'proof date'):
            with self.subTest(failed_part=failed_part):
                record, primary, duplicate = aso_alias()
                receipts = record['link_proof']['references']
                if failed_part == 'body hash':
                    receipts[1]['page_hash'] = 'f' * 64
                elif failed_part == 'independent witness':
                    record['corroboration'].clear()
                elif failed_part == 'receipt URL':
                    receipts[1]['url'] = receipts[0]['url']
                else:
                    receipts[1]['fetched_at'] = '2026-12-01T01:00:00+00:00'
                self.assertTrue(resolution_problems(record, primary, duplicate))

    def test_pair_cannot_bind_other_entries_or_other_original_rows(self):
        for field in ('primary_entry_id', 'duplicate_entry_id', 'source_hash', 'source_locator'):
            with self.subTest(field=field):
                record, primary, duplicate = aso_alias()
                if field.endswith('entry_id'):
                    record[field] = 'other-registration'
                else:
                    duplicate[field] = 'other-original-row'
                    if field in record['snapshots']['duplicate']:
                        record['snapshots']['duplicate'][field] = duplicate[field]
                self.assertTrue(resolution_problems(record, primary, duplicate))

    def test_missing_original_acquisition_date_requires_review(self):
        record, primary, duplicate = aso_alias()
        del primary['fetched_at']
        self.assertTrue(resolution_problems(record, primary, duplicate))

    def test_agency_receipt_must_bind_link_to_same_regional_row(self):
        record, primary, duplicate = aso_alias()
        record['evidence'][1]['href_locator'] = 'table[5] tr[7] td[2] a[href]'
        self.assertTrue(resolution_problems(record, primary, duplicate))


_ORIGINAL_DATE = '2026-11-10T12:26:30+00:00'
_FETCH_DATE = '2026-11-27T01:30:50+00:00'
_LEGACY_URL = 'https://nagasaki-jinjacho.or.jp/link.html'
_REGIONAL_URL = 'https://nagasaki-jinjacho.or.jp/seihi.html'


def aso_alias():
    common = dict(source_key='nagasaki', prefecture='長崎県', prefecture_code='42',
                  name_raw='阿蘇神社', fetched_at=_ORIGINAL_DATE)
    primary = dict(
        common,
        id='d9975756-7562-556b-bc8f-8061f50a67ac',
        address='諫早市多良見町化屋861番地', municipality='諫早市',
        source_hash='b691f7fc1c86c040b3b846cebb162988302f378250a1feb4684d84d827e84f09',
        listing_url=_REGIONAL_URL, source_locator='table[5] tr[6]', native_source_id=None,
        official_site_url='http://asojinja.jp/',
        page_hash='3533c16893b5756f34c4c93b68d6a771d88f132c7109becca2fe0c958489bdd5',
    )
    legacy_href = 'http://www.asojinja.jp/'
    duplicate = dict(
        common,
        id='e21c64ca-c91f-59f5-91ca-3a7460c6690c', address='', municipality='',
        source_hash='9d2343c011e312e4ed43b754c7bf9fe03599253ce28f3216b3162456a9542a00',
        listing_url=_LEGACY_URL, source_locator='div#bk17860131 a[href="http://www.asojinja.jp/"]',
        native_source_id=legacy_href, official_site_url=legacy_href,
        page_hash='307091be9b409e579a3163b03f301e3972c3ceabf9fd1ea5dfd375fcfad11b04',
    )
    evidence = [
        dict(role='original_agency_link_observation', branch_raw='西彼支部'),
        dict(role='regional_agency_shrine_row', name_column_raw='神社名', address_column_raw='鎮座地',
             address_locator='table[5] tr[6] td[7]', href_locator='table[5] tr[6] td[2] a[href]'),
    ]
    for observation, source in zip(evidence, (duplicate, primary)):
        observation.update(url=source['listing_url'], locator=source['source_locator'], status=200,
                           source_publisher='長崎県神社庁', name_raw=source['name_raw'],
                           address_raw=source['address'], href_raw=source['official_site_url'],
                           native_source_id=source['native_source_id'],
                           official_site_url=source['official_site_url'], page_hash=source['page_hash'],
                           source_record_fetched_at=source['fetched_at'], fetched_at=_FETCH_DATE)
    endpoint = dict(
        status=200, locator='title／阿蘇神社社務所', fetched_at=_FETCH_DATE, name_raw='阿蘇神社',
        address_raw='長崎県諫早市多良見町化屋862', address_role='shrine_office',
        title='阿蘇神社（諫早市多良見町）',
        page_hash='48b210005e0b5f19985e2c0691d904541a7b37f713f68aa91db54abca51ffaca',
    )
    address = dict(
        status=200, url='https://www.pref.nagasaki.jp/uploads/2025/02/1739522392.pdf',
        locator='戦没者追悼施設 No.47 忠魂碑 所在地欄', fetched_at=_FETCH_DATE, pdf_page=17,
        source_publisher='長崎県', name_raw='忠魂碑', address_raw='諫早市多良見町化屋 861',
        address_role='monument_inside_shrine_precinct',
        page_hash='53fea64fdca3d3a74c25787807507baf42d162c6ba28762b9a534706e5df96f3',
    )
    snapshot_fields = ('id', 'source_key', 'prefecture_code', 'prefecture', 'name_raw', 'address',
                       'address_raw', 'address_context', 'native_source_id', 'source_hash')
    snapshots = {role: {key: source.get(key) for key in snapshot_fields}
                 for role, source in (('primary', primary), ('duplicate', duplicate))}
    return dict(
        kind=KIND, primary_id=primary['id'], duplicate_id=duplicate['id'], snapshots=snapshots,
        primary_entry_id='98894a79-bb3e-5cc3-9b96-e9656f4a9297',
        duplicate_entry_id='de900201-e788-526a-a9f4-95f1be2abac5',
        checked_at='2026-11-27T01:31:00+00:00',
        reason='両方の公式サイトの実取得本文が同一で、県資料の境内地番と地域表が対応。',
        evidence=evidence, corroboration=[address],
        link_proof=dict(
            kind='same_endpoint_body',
            references=[dict(endpoint, url=legacy_href), dict(endpoint, url=primary['official_site_url'])],
        ),
    ), primary, duplicate
