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


    def test_suwa_requires_the_exact_legacy_link_and_current_shrine(self):
        self.assertEqual(resolution_problems(*suwa_alias()), [])
        for missing_part in ('historic href', 'quoted source terms', 'renewal notice', 'redirect'):
            with self.subTest(missing_part=missing_part):
                record, primary, duplicate = suwa_alias()
                old, redirect, *_ = record['link_proof']['references']
                if missing_part == 'historic href':
                    old['href_raw'] = 'https://www.osuwasan.jp/'
                elif missing_part == 'quoted source terms':
                    old.pop('terms_reference')
                elif missing_part == 'renewal notice':
                    record['corroboration'].clear()
                else:
                    redirect['location_header_raw'] = 'https://www.osuwasan.jp/index.html'
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


def suwa_alias():
    record = {'checked_at': '2026-11-27T01:40:08.238469+00:00',
     'corroboration': [{'fetched_at': '2026-11-27T01:34:17.648472+00:00',
                        'locator': '2020年6月20日のお知らせ「再度、ブログ始めます。」の本文',
                        'page_hash': '6bd2d63c8ac49a2291b7f2307d19e911545c3b30f379690fa16ab2f8265cbc04',
                        'role': 'official_site_renewal_without_old_path',
                        'source_publisher': '鎮西大社 諏訪神社',
                        'status': 200,
                        'url': 'https://www.osuwasan.jp/2020/06/20/%E5%86%8D%E5%BA%A6%E3%80%81%E3%83%96%E3%83%AD%E3%82%B0%E5%A7%8B%E3%82%81%E3%81%BE%E3%81%99%E3%80%82/'}],
     'duplicate_entry_id': '04d61230-f83c-5aba-bc9c-baad5173726b',
     'duplicate_id': '794e0c67-69a5-5dba-a5cc-7fb1f5eb5c8f',
     'evidence': [{'address_raw': '',
                   'branch_raw': '長崎市支部',
                   'fetched_at': '2026-11-26T13:58:35.224604+00:00',
                   'href_raw': 'https://www.osuwasan.jp/index.html',
                   'locator': 'div#bk17860131 a[href="https://www.osuwasan.jp/index.html"]',
                   'name_raw': '諏訪神社',
                   'native_source_id': 'https://www.osuwasan.jp/index.html',
                   'official_site_url': 'https://www.osuwasan.jp/index.html',
                   'page_hash': '307091be9b409e579a3163b03f301e3972c3ceabf9fd1ea5dfd375fcfad11b04',
                   'role': 'original_agency_link_observation',
                   'source_publisher': '長崎県神社庁',
                   'source_record_fetched_at': '2026-11-09T15:24:52.605602+00:00',
                   'status': 200,
                   'url': 'https://nagasaki-jinjacho.or.jp/link.html'},
                  {'address_column_raw': '鎮座地',
                   'address_locator': 'table[1] tr[2] td[7]',
                   'address_raw': '長崎市上西山町18番地15号',
                   'fetched_at': '2026-11-26T13:59:03.639971+00:00',
                   'href_locator': 'table[1] tr[2] td[2] a[href]',
                   'href_raw': 'http://www.osuwasan.jp/',
                   'locator': 'table[1] tr[2]',
                   'name_column_raw': '神社名',
                   'name_raw': '諏訪神社',
                   'native_source_id': None,
                   'official_site_url': 'http://www.osuwasan.jp/',
                   'page_hash': '84ed1414360b6f867f72e4099b42c13721dac7368d3c827d947e6d38545f0ebd',
                   'role': 'regional_agency_shrine_row',
                   'source_publisher': '長崎県神社庁',
                   'source_record_fetched_at': '2026-11-10T12:26:34.467147+00:00',
                   'status': 200,
                   'url': 'https://nagasaki-jinjacho.or.jp/nagasaki.html'}],
     'kind': 'nagasaki_explicit_shared_official_link',
     'link_proof': {'kind': 'historic_official_listing',
                    'reason': '2019年の現地訪問記事が同じ社名・全所在地の一欄に庁旧index.htmlへの実リンクを掲載。庁地域表のHTTPトップは同ホストの現公式トップに301で到達し、現公式アクセスと市公式観光の実リンク・住所が対応。旧index.htmlの404と2020年の神社公式ホームページ改修記事も保持。',
                    'references': [{'address_raw': '〒850-0006 長崎県長崎市上西山町１８−１５',
                                    'fetched_at': '2026-11-27T01:39:37.367250+00:00',
                                    'href_raw': 'https://www.osuwasan.jp/index.html',
                                    'locator': 'div.blog_spot の h3 と所在地段落、同ブロックの旧公式href',
                                    'name_raw': '鎮西大社諏訪神社',
                                    'page_hash': '02f80088dc2a484eefca1375ab6e6b9657e1a53e8d1fbc507c36be4380aceb36',
                                    'published_date': '2019-08-02',
                                    'role': 'historically_published_official_url',
                                    'source_publisher': '京都きもの巡り',
                                    'status': 200,
                                    'terms_reference': {'fetched_at': '2026-11-27T01:40:04.451662+00:00',
                                                        'locator': '著作権について',
                                                        'page_hash': '33ddcf045f378eca9985ec36613f98f8483146ec86cd41782b370d558aa9a4dd',
                                                        'source_publisher': '京都きもの巡り',
                                                        'status': 200,
                                                        'url': 'https://www.kyoto-kimonomeguri.com/privacy'},
                                    'terms_url': 'https://www.kyoto-kimonomeguri.com/privacy',
                                    'url': 'https://www.kyoto-kimonomeguri.com/other/1325.html'},
                                   {'fetched_at': '2026-11-27T01:30:51.727670+00:00',
                                    'location_header_raw': 'https://www.osuwasan.jp/',
                                    'page_hash': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
                                    'status': 301,
                                    'url': 'http://www.osuwasan.jp/'},
                                   {'address_raw': '長崎県長崎市上西山町18番15号',
                                    'fetched_at': '2026-11-27T01:28:54.165208+00:00',
                                    'href_raw': 'https://www.osuwasan.jp/',
                                    'locator': '社名・かな見出し／アクセス／rel=canonical',
                                    'name_raw': '鎮西大社 諏訪神社',
                                    'page_hash': 'dff5421b4e050f9e78b1dd421f2d87dfb6b38162f9d5dd65325b3b81db468f1c',
                                    'source_publisher': '鎮西大社 諏訪神社',
                                    'status': 200,
                                    'url': 'https://www.osuwasan.jp/'},
                                   {'address_raw': '長崎県長崎市上西山町18-15',
                                    'fetched_at': '2026-11-27T01:29:59.557462+00:00',
                                    'href_raw': 'https://www.osuwasan.jp/',
                                    'locator': '基本情報の住所とリンクURL',
                                    'name_raw': '鎮西大社\u3000諏訪神社',
                                    'page_hash': '2164286ea29fb12119fc13c07bbdda2a0b6c225457668c1e568fdfd3d725730b',
                                    'source_publisher': '長崎市公式観光サイト「travel nagasaki」',
                                    'status': 200,
                                    'url': 'https://www.at-nagasaki.jp/spot/94'}],
                    'retained_unavailable_ref': {'fetched_at': '2026-11-26T13:58:35.245092+00:00',
                                                 'page_hash': 'ae395b1d9c86fe5bcda9a58e46a33dfab3b7210f63323fd43ccf83bdec72aabf',
                                                 'role': 'unavailable_original_endpoint',
                                                 'status': 404,
                                                 'url': 'https://www.osuwasan.jp/index.html'}},
     'primary_entry_id': '0c15a418-9237-560a-bc2b-253f6a709fc8',
     'primary_id': '3a7913a5-aae4-50ca-ba2a-9f57f1acdd5a',
     'reason': '2019年の現地訪問記事が同じ社名・全所在地の一欄に庁旧index.htmlへの実リンクを掲載。庁地域表のHTTPトップは同ホストの現公式トップに301で到達し、現公式アクセスと市公式観光の実リンク・住所が対応。旧index.htmlの404と2020年の神社公式ホームページ改修記事も保持。',
     'snapshots': {'duplicate': {'address': '',
                                 'address_context': None,
                                 'address_raw': None,
                                 'id': '794e0c67-69a5-5dba-a5cc-7fb1f5eb5c8f',
                                 'name_raw': '諏訪神社',
                                 'native_source_id': 'https://www.osuwasan.jp/index.html',
                                 'prefecture': '長崎県',
                                 'prefecture_code': '42',
                                 'source_hash': 'd3f4887c34c674f52b1dbcfd7b24c43e7d2789baf92d038b69742ab1c28d8d31',
                                 'source_key': 'nagasaki'},
                   'primary': {'address': '長崎市上西山町18番地15号',
                               'address_context': None,
                               'address_raw': None,
                               'id': '3a7913a5-aae4-50ca-ba2a-9f57f1acdd5a',
                               'name_raw': '諏訪神社',
                               'native_source_id': None,
                               'prefecture': '長崎県',
                               'prefecture_code': '42',
                               'source_hash': '2e31cbbe072a57da4533d30d7361f1f3406951491f00ddae0bd87686291e43cf',
                               'source_key': 'nagasaki'}}}
    primary = {'address': '長崎市上西山町18番地15号',
     'address_context': None,
     'address_raw': None,
     'id': '3a7913a5-aae4-50ca-ba2a-9f57f1acdd5a',
     'name_raw': '諏訪神社',
     'native_source_id': None,
     'prefecture': '長崎県',
     'prefecture_code': '42',
     'source_hash': '2e31cbbe072a57da4533d30d7361f1f3406951491f00ddae0bd87686291e43cf',
     'source_key': 'nagasaki',
     'municipality': '長崎市',
     'official_site_url': 'http://www.osuwasan.jp/',
     'listing_url': 'https://nagasaki-jinjacho.or.jp/nagasaki.html',
     'source_locator': 'table[1] tr[2]',
     'page_hash': '84ed1414360b6f867f72e4099b42c13721dac7368d3c827d947e6d38545f0ebd',
     'fetched_at': '2026-11-10T12:26:34.467147+00:00'}
    duplicate = {'address': '',
     'address_context': None,
     'address_raw': None,
     'id': '794e0c67-69a5-5dba-a5cc-7fb1f5eb5c8f',
     'name_raw': '諏訪神社',
     'native_source_id': 'https://www.osuwasan.jp/index.html',
     'prefecture': '長崎県',
     'prefecture_code': '42',
     'source_hash': 'd3f4887c34c674f52b1dbcfd7b24c43e7d2789baf92d038b69742ab1c28d8d31',
     'source_key': 'nagasaki',
     'municipality': '',
     'official_site_url': 'https://www.osuwasan.jp/index.html',
     'listing_url': 'https://nagasaki-jinjacho.or.jp/link.html',
     'source_locator': 'div#bk17860131 a[href="https://www.osuwasan.jp/index.html"]',
     'page_hash': '307091be9b409e579a3163b03f301e3972c3ceabf9fd1ea5dfd375fcfad11b04',
     'fetched_at': '2026-11-09T15:24:52.605602+00:00'}
    return record, primary, duplicate
