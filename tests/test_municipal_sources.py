import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from njd.nationwide import save_collection
from njd.records import build_dataset
from njd.release import create_release
from njd.report import _counts
from njd.reviews import apply_reviews
from njd.validation import blocking_problems


class MunicipalSourceTest(unittest.TestCase):
    def setUp(self):
        website = 'https://www.city.hiroshima.lg.jp'
        observed = '2026-11-26T11:20:00+00:00'
        self.reference = dict(
            url=website + '/shrines.html', title='市の地域文化財',
            source_publisher='広島市', locator='対象の項目見出しと所在地欄',
            name_raw='例神社', reading_raw='れいじんじゃ', reading_scope='full_name',
            address_raw='広島市安芸区例町1-2', municipality='広島市安芸区',
            page_hash='1' * 64, checked_at=observed,
            excerpt='名称 例神社 / 読み れいじんじゃ / 所在地 広島市安芸区例町1-2',
            terms_url=website + '/terms.html',
            authority_reference=dict(url=website + '/terms.html', page_hash='2' * 64, checked_at=observed,
                                     excerpt='広島市ホームページの利用案内'),
        )

    def build(self, *references, existing=None):
        from njd.municipal_sources import dataset_from_references
        return dataset_from_references('hiroshima_municipal', '34', list(references), existing=existing)

    def test_literal_municipal_record_is_counted_in_its_own_basis(self):
        data = self.build(self.reference)
        self.assertEqual([], blocking_problems(data))
        facility, = data['facilities']
        entry, = data['entries']
        self.assertFalse(data['collection']['official_agency_listing_verified'])
        self.assertFalse(facility.get('agency'))
        self.assertEqual(self.reference['address_raw'], facility['address'])
        self.assertEqual(self.reference['reading_raw'], entry['reading_raw'])
        self.assertEqual('municipal_reference', facility['listing_basis'])
        self.assertEqual({'municipal_reference': dict(facilities=1, verified_facilities=1, dictionary_rows=1)},
                         _counts(data)['source_basis_counts'])

    def test_unobserved_full_reading_or_unbound_municipal_origin_is_rejected(self):
        for overrides in ({'reading_raw': 'れい'}, {'address_raw': '広島市安芸区例町1-20'},
                          {'terms_url': 'https://unrelated.example/terms'},
                          {'excerpt': self.reference['excerpt'] + '0'}):
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                self.build(dict(self.reference, **overrides))

    def test_mutated_original_reference_cannot_remain_eligible(self):
        data = self.build(self.reference)
        changed = copy.deepcopy(data)
        changed['facilities'][0]['source_reference']['address_raw'] = '広島市安芸区例町1-3'
        self.assertTrue(blocking_problems(changed))
        self.assertEqual(0, _counts(changed)['verified_facilities'])

    def test_existing_same_address_requires_identity_review(self):
        existing = self.build(self.reference)
        possible_duplicate = dict(self.reference, name_raw='別名の社', reading_raw='べつめいのやしろ',
                                  excerpt='名称 別名の社 / 読み べつめいのやしろ / 所在地 広島市安芸区例町1-2')
        with self.assertRaises(ValueError):
            self.build(possible_duplicate, existing=existing)

    def test_consistent_non_municipal_host_cannot_establish_authority(self):
        impostor = copy.deepcopy(self.reference)
        for record, field in ((impostor, 'url'), (impostor, 'terms_url'), (impostor['authority_reference'], 'url')):
            record[field] = record[field].replace('www.city.hiroshima.lg.jp', 'unrelated.example')
        with self.assertRaises(ValueError):
            self.build(impostor)

    def test_saving_a_supplement_preserves_an_existing_agency_state(self):
        data = self.build(self.reference)
        agency = dict(status='partial', source_key='hiroshima', reason='agency coverage')
        legacy = {'manifest.json': {'prefectures': {'34': agency}}}
        with patch('njd.canonical.is_canonical', return_value=True), patch(
            'njd.canonical.update_repository', side_effect=lambda _, change: change(legacy)
        ):
            save_collection('data', 'hiroshima_municipal', data)
        self.assertEqual(agency, legacy['manifest.json']['prefectures']['34'])

    def test_saving_a_municipal_only_prefecture_sets_reference_status(self):
        data = self.build(self.reference)
        legacy = {}
        with patch('njd.canonical.is_canonical', return_value=True), patch(
            'njd.canonical.update_repository', side_effect=lambda _, change: change(legacy)
        ):
            save_collection('data', 'hiroshima_municipal', data)
        state = legacy['manifest.json']['prefectures']['34']
        self.assertEqual(('hiroshima_municipal', 'collected_reference'), (state['source_key'], state['status']))

    def test_existing_agency_source_keeps_its_inferred_status(self):
        from njd.canonical import _merged_raw

        data = self.build(self.reference)
        agency = build_dataset('hiroshima', '34', '広島県', '例神社庁', [])
        legacy = {'sources/hiroshima.json': agency}
        with patch('njd.canonical.is_canonical', return_value=True), patch(
            'njd.canonical.update_repository', side_effect=lambda _, change: change(legacy)
        ):
            save_collection('data', 'hiroshima_municipal', data)
        state = _merged_raw(legacy)['collection']['prefecture_states']['34']
        self.assertEqual(('hiroshima', 'collected'), (state['source_key'], state['status']))

    def test_municipal_origin_cannot_be_relabelled_or_orphaned(self):
        data = self.build(self.reference)
        changed = copy.deepcopy(data)
        for record in (changed['collection'], changed['entries'][0], changed['facilities'][0]):
            record.pop('listing_basis')
        changed['entries'][0]['reading_source_kind'] = 'agency'
        changed['facilities'][0]['agency'] = '例神社庁'
        self.assertTrue(blocking_problems(changed))
        data['entries'].clear()
        data['facilities'][0].pop('source_reference')
        self.assertTrue(blocking_problems(data))

    def test_combining_snapshots_detects_duplicates_from_a_stale_comparison(self):
        reference = self.reference
        for address in (reference['address_raw'], '広島市安芸区例町5-3'):
            with self.subTest(address=address):
                data = self.build(reference)
                municipal = data['collection']
                agency = build_dataset('hiroshima', '34', '広島県', '例神社庁', [dict(
                    name=reference['name_raw'], address=address, reading_raw=reference['reading_raw'],
                    url='https://example.jp/agency', fetched_at=reference['checked_at'],
                    page_hash='3' * 64, locator='一覧', evidence='実資料',
                )])
                data['collection'] = dict(sources={'hiroshima_municipal': municipal, 'hiroshima': agency['collection']})
                data['facilities'].extend(agency['facilities'])
                data['entries'].extend(agency['entries'])
                self.assertTrue(blocking_problems(data))

    def test_explicit_user_review_keeps_the_original_municipal_reference(self):
        data = self.build(self.reference)
        facility, = data['facilities']
        entry, = data['entries']
        review = dict(case_id='explicit-test-review', facility_id=facility['id'],
                      expected_source_hash=entry['source_hash'], confirmation='user_confirmation',
                      recorded_at=self.reference['checked_at'], reason='Explicit reading review',
                      original=dict(name_raw=facility['name_raw'], reading_raw=entry['reading_raw'],
                                    address=facility['address'], listing_url=facility['listing_url']),
                      outputs=[dict(surface=entry['surface'], reading='れいじんしゃ',
                                    basis='user_confirmation', reading_url='')])
        reviewed = apply_reviews(data, dict(schema_version=1, entries={entry['id']: review}))
        self.assertEqual([], blocking_problems(reviewed))
        self.assertEqual('れいじんしゃ', reviewed['entries'][0]['reading'])
        self.assertEqual('れいじんじゃ', reviewed['entries'][0]['reading_raw'])

    def test_municipal_only_release_identifies_its_source(self):
        with tempfile.TemporaryDirectory() as temp:
            data = Path(temp) / 'data'
            output = Path(temp) / 'release'
            save_collection(data, 'hiroshima_municipal', self.build(self.reference))
            create_release(data, output, 'v0.1.0', 'a' * 40, legacy=True)
            destination = output / 'dictionaries'
            credits = json.loads((destination / 'ATTRIBUTION.json').read_text())
            self.assertEqual([dict(url=self.reference['url'], title=self.reference['title'],
                                   source_publisher=self.reference['source_publisher'],
                                   terms_url=self.reference['terms_url'])], credits['municipal'])
            introduction = (destination / 'README.md').read_text().splitlines()[2]
            self.assertTrue(introduction.startswith('自治体の公刊資料に基づく辞書です。'))


if __name__ == '__main__':
    unittest.main()
