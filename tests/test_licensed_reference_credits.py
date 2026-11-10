import unittest
from njd.release import licensed_reference_credits


class LicensedReferenceCreditsTests(unittest.TestCase):
    def test_prescribed_credit_license_and_processing_notice_survive_dedup(self):
        ref=dict(source_kind='gazetteer_reference',url='https://source.example.invalid/item/1',
            title='Gazetteer',license_url='https://creativecommons.org/licenses/by/4.0/',
            attribution='Dataset (Publisher) doi:example',processed_notice='Name and address only; no kana inferred.')
        credits=licensed_reference_credits([ref,dict(ref),None,dict(source_kind='reference',url='https://unconfirmed.example.invalid/')])
        self.assertEqual(len(credits),1)
        self.assertEqual(credits[0]['attribution'],ref['attribution'])
        self.assertEqual(credits[0]['processed_notice'],ref['processed_notice'])
        self.assertEqual(credits[0]['license_url'],ref['license_url'])

    def test_wikipedia_remains_in_its_separate_versioned_credit_list(self):
        refs=[dict(source_kind='encyclopedia',url='https://ja.wikipedia.org/wiki/Example',license_url='https://creativecommons.org/licenses/by-sa/4.0/'),
            dict(source_kind='government_corporate_register',url='https://government.example.invalid/',license_url='https://license.example.invalid/',attribution='Government')]
        self.assertEqual(licensed_reference_credits(refs),licensed_reference_credits(list(reversed(refs))))
        self.assertEqual(len(licensed_reference_credits(refs)),1)
        self.assertEqual(licensed_reference_credits(refs)[0]['source_kind'],'government_corporate_register')
