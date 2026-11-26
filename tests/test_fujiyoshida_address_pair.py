import copy
import unittest

from njd.corrections import apply_corrections
from njd.records import build_dataset
from njd.validation import eligible
from test_corrections import correction
from test_records import row


class FujiyoshidaAddressPairTest(unittest.TestCase):
    def fixture(self, listing_address='富士吉田市小明見5-4-17', property_address='富士吉田市小明見5-3352'):
        dataset = build_dataset('yamanashi', '19', '山梨県', '山梨県神社庁', [
            row(name='子之神社', reading_raw='', address=listing_address),
        ])
        facility, entry = dataset['facilities'][0], dataset['entries'][0]
        proposal = correction(dataset, {'reading': 'ねのかみしゃ'})
        ref = proposal['entries'][entry['id']]['references'][0]
        ref.update(
            url='https://www.city.fujiyoshida.yamanashi.jp/page/1107.html',
            page_hash='9d0be47fecae03058d9f6b9c3a048ee6811803fb77e201602a66e031ef09b16c',
            source_kind='municipal_cultural_property', reading_scope='full_name',
            address_raw=property_address,
            excerpt='小明見字海端子之神社のウワミズザクラ ／ こあすみあざうみばたねのかみしゃのうわみずざくら ／ '+property_address,
        )
        pair = dict(
            url='https://www.city.fujiyoshida.yamanashi.jp/uploaded/attachment/3948.pdf',
            page_hash='4fd1a0d66eb1e81119b84c0a4f2456e479f815819250f0354fe261fa1d5b4a2f',
            checked_at='2026-11-26T12:01:05.466032+00:00', source_publisher='富士吉田市',
            name_raw='子之神社', old_locality_raw='小明見', old_parcel_raw='3352',
            new_locality_raw='小明見五丁目', block_raw='4', residence_number_raw='17',
            forward_page=36, reverse_page=83,
            forward_row_raw='小明見 / 3352 / 子之神社 / 小明見五丁目 / 4 / 17',
            reverse_row_raw='小明見五丁目 / 4 / 17 / 子之神社 / 小明見 / 3352',
            locator='PDF36・83頁 子之神社の旧新・新旧行',
        )
        ref['address_identity_proof'] = dict(
            kind='documented_fujiyoshida_residence_pair', facility_id=facility['id'], entry_id=entry['id'],
            expected_source_hash=entry['source_hash'], listing_address_raw=listing_address,
            reference_address_raw=property_address, reference_url=ref['url'], reference_page_hash=ref['page_hash'],
            change_reference=pair,
        )
        return dataset, proposal, ref

    def test_named_address_pair_accepts_reading_and_preserves_each_source_address(self):
        dataset, proposal, reference = self.fixture()
        original = copy.deepcopy(dataset)
        result = apply_corrections(dataset, proposal)
        self.assertEqual(len(eligible(result)), 1)
        self.assertEqual(result['entries'][0]['reading'], 'ねのかみしゃ')
        self.assertEqual(result['facilities'], original['facilities'])
        self.assertEqual(
            result['entries'][0]['correction']['references'][0]['address_raw'], reference['address_raw'],
        )
        self.assertEqual(dataset, original)

    def test_another_number_cannot_use_the_pair(self):
        for listing, cultural in (
            ('富士吉田市小明見5-4-170', '富士吉田市小明見5-3352'),
            ('富士吉田市小明見5-4-17', '富士吉田市小明見4-3352'),
            ('富士吉田市小明見5-4-17', '富士吉田市小明見5-3352-1'),
        ):
            with self.subTest(listing=listing, cultural=cultural):
                dataset, proposal, _ = self.fixture(listing, cultural)
                self.assertEqual(eligible(apply_corrections(dataset, proposal)), [])

    def test_invalid_city_record_or_nonreading_entry_remains_pending(self):
        for edit in (
            lambda ref: ref.pop('address_identity_proof'),
            lambda ref: ref.update(reading_scope='partial_or_absent'),
            lambda ref: ref.update(page_hash='f'*64),
            lambda ref: ref['address_identity_proof'].update(reference_page_hash='f'*64),
            lambda ref: ref['address_identity_proof']['change_reference'].update(reverse_page=36),
            lambda ref: ref['address_identity_proof']['change_reference'].update(name_raw='別の子之神社'),
            lambda ref: ref['address_identity_proof']['change_reference'].update(old_parcel_raw='3351'),
            lambda ref: ref['address_identity_proof']['change_reference'].update(checked_at='2026-11-26'),
        ):
            dataset, proposal, reference = self.fixture()
            edit(reference)
            self.assertEqual(eligible(apply_corrections(dataset, proposal)), [])
        dataset, proposal, _ = self.fixture()
        dataset['entries'][0]['status'] = 'excluded'
        self.assertEqual(eligible(apply_corrections(dataset, proposal)), [])

    def test_invalid_proof_kind_does_not_raise(self):
        dataset, proposal, reference = self.fixture()
        reference['address_identity_proof']['kind'] = []
        self.assertEqual(eligible(apply_corrections(dataset, proposal)), [])
