"""Explicit editor-selected separator removal never supplies missing kana."""
import copy
import unittest

from test_records import build, row
from test_reviews import decision
from njd.reviews import apply_reviews, review_problems
from njd.validation import eligible, blocking_problems


class SeparatorReviewTests(unittest.TestCase):
    def case(self, name='架空・別架空神社', raw='かくう・べつかくうじんじゃ',
             surface='架空別架空神社', name_remove=('・',), reading_remove=('・',)):
        data = build([row(name=name, reading_raw=raw)])
        review = decision(data, [dict(surface=surface, reading='かくうべつかくうじんじゃ',
            basis='agency_separator_normalization', reading_url=data['facilities'][0]['listing_url'])],
            review_kind='source_separator_normalization',
            separator_review=dict(name_remove=list(name_remove), reading_remove=list(reading_remove)))
        return data, review

    def test_explicit_single_registration_removes_only_recorded_separators(self):
        data, review = self.case()
        before = copy.deepcopy(data)
        result = apply_reviews(data, review)
        self.assertEqual(len(eligible(result)), 1)
        entry = eligible(result)[0]
        self.assertEqual((entry['surface'], entry['reading']), ('架空別架空神社', 'かくうべつかくうじんじゃ'))
        self.assertEqual(len(result['entries']), 1)
        self.assertEqual(entry['name_raw'], '架空・別架空神社')
        self.assertEqual(entry['reading_raw'], 'かくう・べつかくうじんじゃ')
        self.assertEqual(blocking_problems(result), [])
        self.assertEqual(data, before)

    def test_surface_can_keep_middle_dot_while_reading_loses_space(self):
        data, review = self.case(raw='かくう べつかくうじんじゃ', surface='架空・別架空神社',
                                 name_remove=(), reading_remove=(' ',))
        result = apply_reviews(data, review)
        self.assertEqual(eligible(result)[0]['surface'], '架空・別架空神社')

    def test_missing_suffix_new_kana_and_unapproved_name_changes_are_rejected(self):
        for change in ('suffix', 'sound', 'name', 'unlisted_separator', 'permission', 'url', 'hash', 'split'):
            with self.subTest(change=change):
                data, review = self.case()
                item = next(iter(review['entries'].values()))
                output = item['outputs'][0]
                if change == 'suffix': output['reading'] += 'じんじゃ'
                elif change == 'sound': output['reading'] = output['reading'].replace('べつ', 'べち')
                elif change == 'name': output['surface'] += '下社'
                elif change == 'unlisted_separator': item['separator_review']['reading_remove'] = ['う']
                elif change == 'permission': item['confirmation'] = 'source_review'
                elif change == 'url': output['reading_url'] = 'https://other.example.invalid/'
                elif change == 'hash': item['expected_source_hash'] = '0' * 64
                elif change == 'split': item['split'] = True
                self.assertTrue(review_problems(item, data['facilities'][0], data['entries'][0], data['collection']))
                self.assertEqual(eligible(apply_reviews(data, review)), [])

    def test_separator_edit_cannot_clear_existing_location_or_identity_hold(self):
        data, review = self.case()
        data['facilities'][0].update(status='pending', reason='unresolved facility identity')
        self.assertEqual(eligible(apply_reviews(data, review)), [])

    def test_ordinary_review_cannot_enable_separator_edit_implicitly(self):
        data, review = self.case()
        item = next(iter(review['entries'].values()))
        item.pop('review_kind')
        self.assertTrue(review_problems(item, data['facilities'][0], data['entries'][0], data['collection']))

    def test_retained_annotation_keeps_full_surface_and_unchanged_source_reading(self):
        data = build([row(name='架空神社（下社）')])
        data['facilities'][0].update(status='pending', reason='annotated official name requires review',
                                   review_reason='annotated official name requires review')
        review = decision(data, [dict(surface='架空神社（下社）', reading='かくうじんじゃ',
            basis='agency_selected', reading_url=data['facilities'][0]['listing_url'])],
            review_kind='retained_source_annotation', annotation_review=dict(annotation_raw='下社'))
        result = apply_reviews(data, review)
        self.assertEqual(len(eligible(result)), 1)
        self.assertEqual(eligible(result)[0]['surface'], '架空神社（下社）')
        self.assertEqual(eligible(result)[0]['reading'], 'かくうじんじゃ')
        self.assertEqual(blocking_problems(result), [])
        for change in ('reading', 'annotation', 'address'):
            with self.subTest(change=change):
                bad = copy.deepcopy(review); original = copy.deepcopy(data)
                item = next(iter(bad['entries'].values()))
                if change == 'reading': item['outputs'][0]['reading'] += 'しもしゃ'
                elif change == 'annotation': item['annotation_review']['annotation_raw'] = '上社'
                else: original['facilities'][0]['review_reason'] = 'multiple address lines'
                self.assertEqual(eligible(apply_reviews(original, bad)), [])
