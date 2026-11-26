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

    def test_kyotango_compares_documented_minor_locality_markers(self):
        for name, reading, acquired, printed in (
            ('八幡神社', 'はちまんじんじゃ', '京丹後市峰山町鱒留大成354', '京都府京丹後市峰山町鱒留小字大成354'),
            ('金刀比羅神社', 'ことひらじんじゃ', '京丹後市峰山町泉奥山1165-2', '京都府京丹後市峰山町泉小字奥山1165番2'),
            ('生王部神社', 'いくおうべじんじゃ', '京丹後市網野町生野内下大クゴ443', '京丹後市網野町生野内小字下大クゴ 443'),
        ):
            with self.subTest(acquired=acquired):
                dataset, proposal = self.fixture('26', '京都府', name, reading, acquired, printed)
                result = apply_corrections(dataset, proposal)
                self.assertEqual(len(eligible(result)), 1)
                self.assertEqual(result['facilities'], dataset['facilities'])
                self.assertEqual(result['entries'][0]['correction']['references'][0]['address_raw'], printed)

    def test_kyotango_requires_the_documented_minor_locality_and_parcel(self):
        for acquired, printed in (
            ('京丹後市峰山町鱒留大成354', '京丹後市峰山町鱒留小字大成354-1'),
            ('京丹後市峰山町泉奥山1165-2', '京丹後市峰山町泉小字奥山1165'),
            ('京丹後市峰山町泉奥山1165-2', '京丹後市峰山町泉小字別字1165-2'),
            ('京丹後市網野町生野内下大クゴ443', '京丹後市網野町生野内小字下大クゴ443-1'),
            ('京丹後市網野町木津次田115', '京丹後市網野町木津小字次田115'),
        ):
            with self.subTest(acquired=acquired, printed=printed):
                dataset, proposal = self.fixture(
                    '26', '京都府', '神明神社', 'しんめいじんじゃ', acquired, printed,
                )
                self.assertEqual(eligible(apply_corrections(dataset, proposal)), [])

    def test_kitakyushu_compares_documented_street_spellings(self):
        for name, reading, acquired, printed in (
            ('日峯神社', 'ひのみねじんじゃ', '北九州市八幡西区浅川日の峰1-8-8',
             '福岡県北九州市八幡西区浅川日の峯１丁目８番８号'),
            ('豊山八幡神社', 'とよやまはちまんじんじゃ', '北九州市八幡東区春ノ町4-4-1',
             '福岡県北九州市八幡東区春の町４丁目４番１号'),
        ):
            with self.subTest(acquired=acquired):
                dataset, proposal = self.fixture('40', '福岡県', name, reading, acquired, printed)
                result = apply_corrections(dataset, proposal)
                self.assertEqual(len(eligible(result)), 1)
                self.assertEqual(result['facilities'], dataset['facilities'])
                self.assertEqual(result['entries'][0]['correction']['references'][0]['address_raw'], printed)

    def test_kitakyushu_requires_exact_ward_and_house_number(self):
        for acquired, printed in (
            ('北九州市八幡西区浅川日の峰1-8-8', '北九州市八幡西区浅川日の峯1丁目8番9号'),
            ('北九州市八幡東区春ノ町4-4-1', '北九州市八幡西区春の町4丁目4番1号'),
            ('北九州市八幡東区春ノ町4-4-1', '北九州市八幡東区春の町4丁目4番'),
        ):
            with self.subTest(acquired=acquired, printed=printed):
                dataset, proposal = self.fixture('40', '福岡県', '神明神社', 'しんめいじんじゃ', acquired, printed)
                self.assertEqual(eligible(apply_corrections(dataset, proposal)), [])

    def test_miyako_shrine_compares_the_documented_nishizato_address(self):
        acquired = '宮古島市平良市西里5-1'
        printed = '沖縄県宮古島市平良字西里５番地の１'
        dataset, proposal = self.fixture(
            '47', '沖縄県', '宮古神社', 'みやこじんじゃ', acquired, printed,
        )
        result = apply_corrections(dataset, proposal)
        self.assertEqual(len(eligible(result)), 1)
        self.assertEqual(result['facilities'], dataset['facilities'])
        self.assertEqual(result['entries'][0]['correction']['references'][0]['address_raw'], printed)

    def test_miyako_comparison_does_not_extend_to_other_names_or_parcels(self):
        for name, acquired, printed in (
            ('宮古神社', '宮古島市平良市西里5-1', '宮古島市平良字西里5-10'),
            ('宮古神社', '宮古島市平良市西里5-2', '宮古島市平良字西里5-2'),
            ('宮古神社', '宮古島市平良市西里5-1', '宮古島市平良字西仲宗根5-1'),
            ('別神社', '宮古島市平良市西里5-1', '宮古島市平良字西里5-1'),
        ):
            with self.subTest(name=name, acquired=acquired, printed=printed):
                dataset, proposal = self.fixture(
                    '47', '沖縄県', name, 'みやこじんじゃ', acquired, printed,
                )
                self.assertEqual(eligible(apply_corrections(dataset, proposal)), [])

    def test_sasebo_compares_the_documented_takanashi_town_spelling(self):
        acquired = '佐世保市髙梨町1番9号'
        printed = '長崎県佐世保市高梨町1-9'
        dataset, proposal = self.fixture(
            '42', '長崎県', '須佐神社', 'すさじんじゃ', acquired, printed,
        )
        result = apply_corrections(dataset, proposal)
        self.assertEqual(len(eligible(result)), 1)
        self.assertEqual(result['facilities'], dataset['facilities'])
        self.assertEqual(result['entries'][0]['correction']['references'][0]['address_raw'], printed)

    def test_takanashi_comparison_requires_the_same_city_and_street_number(self):
        for printed in ('佐世保市高梨町1-90', '佐世保市高梨町2-9', '佐世保市高梨町', '長崎市高梨町1番9号'):
            with self.subTest(printed=printed):
                dataset, proposal = self.fixture(
                    '42', '長崎県', '須佐神社', 'すさじんじゃ', '佐世保市髙梨町1番9号', printed,
                )
                self.assertEqual(eligible(apply_corrections(dataset, proposal)), [])
