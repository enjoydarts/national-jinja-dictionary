import copy
import unittest

from njd.locations import apply_locations, location_problems, raw_address
from njd.records import build_dataset


def fixture():
    url = 'https://www.kochi-jinjyacho.com/高知県神社一覧?comp-ljqfjyd6_page=166'
    source_id = 'bcf2b020-e99b-41cd-984f-b6f0be9b4a71'
    name = '朝倉神社'
    context, street = '高知県高岡郡', '朝倉丙2100番地ｲ'
    address = '高知県高知市朝倉丙2100-イ'
    registered = '高知県高知市朝倉丙２１００番地イ'
    observed = '2026-11-27T01:08:31+00:00'
    dataset = build_dataset('kochi', '39', '高知県', '高知県神社庁', [
        dict(name=name, reading_raw='', address=context + street, url=url,
             locator='acquired agency row', fetched_at=observed, page_hash='a' * 64,
             source_id=source_id, evidence='acquired address fields'),
    ])
    facility = dataset['facilities'][0]
    official = dict(url=url, name_raw=name, page_hash='b' * 64, fetched_at=observed,
                    source_kind='agency', institutional_phone_sha256='c' * 64)
    supplement = dict(
        supplement_kind='kochi_agency_documented_municipality', status='verified',
        facility_id=facility['id'], expected_source_hash=facility['source_hash'],
        original={key: facility.get(key) for key in ('name_raw', 'address', 'municipality',
                  'listing_url', 'official_site_url', 'native_source_id')},
        changes=dict(address=address, municipality='高知市'),
        reason='Same-address agency profile and government registry were inspected.',
        agency_cms_reference=dict(official, locator='agency search row', native_source_id=source_id,
                                  address_context_raw=context, address_raw=street, branch_raw='高知市支部'),
        reference=dict(official, locator='agency profile card', address_raw=address,
                       location_role='shrine', href_raw='https://asakurajinja.yamanoha.com/',
                       excerpt=name + '\n' + address),
        registry_reference=dict(
            url='https://www.houjin-bangou.nta.go.jp/henkorireki-johoto.html?selHouzinNo=5490005000776',
            name_raw=name, address_raw=registered, excerpt=name + '\n' + registered,
            locator='Name and address cells', page_hash='d' * 64, fetched_at=observed,
            corporate_number='5490005000776', location_role='principal_office',
        ),
    )
    return dataset, supplement


class KochiLocationTest(unittest.TestCase):
    def test_same_page_agency_card_and_registry_recover_the_missing_municipality(self):
        dataset, supplement = fixture()
        facility = dataset['facilities'][0]
        self.assertEqual(location_problems(supplement, facility), [])
        document = dict(schema_version=1, facilities={facility['id']: supplement})
        result = apply_locations(dataset, document)
        verified = result['facilities'][0]
        self.assertEqual(verified['address'], supplement['changes']['address'])
        self.assertEqual(verified['municipality'], '高知市')
        self.assertEqual(raw_address(verified), facility['address'])
        self.assertEqual(result['entries'][0]['reason'], 'missing agency reading')
        self.assertEqual(apply_locations(result, document), result)

    def test_location_requires_the_acquired_row_and_corroborated_complete_branch(self):
        dataset, supplement = fixture()
        facility = dataset['facilities'][0]
        for field, key, value in (
            ('agency_cms_reference', 'native_source_id', 'another-record'),
            ('agency_cms_reference', 'page_hash', 'e' * 64),
            ('reference', 'institutional_phone_sha256', 'e' * 64),
            ('reference', 'address_raw', '高知県高知市朝倉丙2100-1'),
            ('registry_reference', 'address_raw', '高知県高知市朝倉丙２１００番地'),
        ):
            with self.subTest(field=field, key=key):
                invalid = copy.deepcopy(supplement)
                invalid[field][key] = value
                self.assertTrue(location_problems(invalid, facility))
