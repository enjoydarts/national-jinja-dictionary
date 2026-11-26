import unittest

from njd.corrections import apply_corrections
from njd.records import build_dataset
from njd.validation import eligible
from test_corrections import correction
from test_records import row


class PublishedAddressFormsTest(unittest.TestCase):
    def fixture(self, code, prefecture, name, reading, acquired, printed):
        dataset = build_dataset('address_fixture', code, prefecture, prefecture+'神社庁', [
            row(name=name, reading_raw='', address=acquired),
        ])
        proposal = correction(dataset, {'reading': reading})
        reference = proposal['entries'][dataset['entries'][0]['id']]['references'][0]
        reference.update(address_raw=printed, excerpt=f'{name}（{reading}） {printed}')
        return dataset, proposal

    def test_marugame_municipal_glyph_preserves_the_printed_addresses(self):
        acquired, printed = '丸亀市三條町515番地', '香川県丸亀市三条町５１５番地'
        dataset, proposal = self.fixture('37', '香川県', '日吉神社', 'ひよしじんじゃ', acquired, printed)
        result = apply_corrections(dataset, proposal)
        self.assertEqual(len(eligible(result)), 1)
        self.assertEqual(result['facilities'], dataset['facilities'])
        self.assertEqual(result['entries'][0]['correction']['references'][0]['address_raw'], printed)

    def test_municipal_glyph_requires_the_same_parcel_in_marugame(self):
        for acquired, printed in (
            ('丸亀市三條町515番地', '丸亀市三条町515-1'),
            ('丸亀市三條町515番地', '丸亀市三条町'),
            ('高松市三條町515番地', '高松市三条町515番地'),
        ):
            with self.subTest(printed=printed):
                dataset, proposal = self.fixture('37', '香川県', '日吉神社', 'ひよしじんじゃ', acquired, printed)
                self.assertEqual(eligible(apply_corrections(dataset, proposal)), [])

    def test_kochi_explicit_parcel_list_preserves_both_items_in_both_sources(self):
        acquired = '高知県南国市十市字新宮山5937.5938番地'
        printed = '高知県南国市十市字新宮山５９３７番地・５９３８番地'
        dataset, proposal = self.fixture('39', '高知県', '新宮神社', 'しんぐうじんじゃ', acquired, printed)
        result = apply_corrections(dataset, proposal)
        self.assertEqual(len(eligible(result)), 1)
        self.assertEqual(result['facilities'], dataset['facilities'])
        self.assertEqual(result['entries'][0]['correction']['references'][0]['address_raw'], printed)

    def test_partial_different_and_range_addresses_remain_pending(self):
        acquired = '南国市十市字新宮山5937.5938番地'
        for end in ('5937番地', '5938番地', '5937番地・5939番地', '自5937至5938番地', '5937・5938-1番地'):
            with self.subTest(end=end):
                dataset, proposal = self.fixture(
                    '39', '高知県', '新宮神社', 'しんぐうじんじゃ', acquired, '南国市十市字新宮山'+end,
                )
                self.assertEqual(eligible(apply_corrections(dataset, proposal)), [])

    def test_kizugawa_compares_the_documented_town_prefix(self):
        acquired = '木津川市平尾里屋敷54'
        printed = '木津川市山城町平尾里屋敷54'
        dataset, proposal = self.fixture(
            '26', '京都府', '和伎座天乃夫岐賣神社', 'わきにますあめのふきめじんじゃ', acquired, printed,
        )
        result = apply_corrections(dataset, proposal)
        self.assertEqual(len(eligible(result)), 1)
        self.assertEqual(result['facilities'], dataset['facilities'])
        self.assertEqual(result['entries'][0]['correction']['references'][0]['address_raw'], printed)

    def test_kizugawa_requires_the_documented_locality_and_whole_parcel(self):
        for acquired, printed in (
            ('木津川市平尾里屋敷54', '木津川市山城町平尾里屋敷54-1'),
            ('木津川市平尾里屋敷54', '木津川市山城町平尾上垣内54'),
            ('木津川市平尾上垣内54', '木津川市山城町平尾上垣内54'),
        ):
            with self.subTest(acquired=acquired, printed=printed):
                dataset, proposal = self.fixture(
                    '26', '京都府', '和伎座天乃夫岐賣神社', 'わきにますあめのふきめじんじゃ', acquired, printed,
                )
                self.assertEqual(eligible(apply_corrections(dataset, proposal)), [])
