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

    def test_kochi_explicit_combined_parcels_compare_with_both_numbers_preserved(self):
        acquired = '香美市土佐山田町本村字ｱｶﾉﾐﾂﾞ497.498合番地'
        printed = '高知県香美市土佐山田町本村字アカノミヅ４９７・４９８合番地'
        dataset, proposal = self.fixture('39', '高知県', '星神社', 'ほしじんじゃ', acquired, printed)
        result = apply_corrections(dataset, proposal)
        self.assertEqual(len(eligible(result)), 1)
        self.assertEqual(result['facilities'], dataset['facilities'])
        self.assertEqual(result['entries'][0]['correction']['references'][0]['address_raw'], printed)

    def test_kochi_combined_parcel_comparison_requires_the_complete_list(self):
        acquired = '香美市土佐山田町本村字ｱｶﾉﾐﾂﾞ497.498合番地'
        for end in ('497合番地', '498・497合番地', '497・499合番地', '497・498-1合番地', '497・498番地'):
            with self.subTest(end=end):
                dataset, proposal = self.fixture(
                    '39', '高知県', '星神社', 'ほしじんじゃ', acquired, '香美市土佐山田町本村字アカノミヅ'+end,
                )
                self.assertEqual(eligible(apply_corrections(dataset, proposal)), [])

    def test_muroto_ebisu_glyph_comparison_preserves_the_branch_and_raw_addresses(self):
        acquired = '高知県室戸市元米ｹ谷西甲2737番地15'
        printed = '高知県室戸市元米ヶ谷西甲２７３７番地１５'
        dataset, proposal = self.fixture('39', '高知県', '惠美須神社', 'えびすじんじゃ', acquired, printed)
        result = apply_corrections(dataset, proposal)
        self.assertEqual(len(eligible(result)), 1)
        self.assertEqual(result['facilities'], dataset['facilities'])
        self.assertEqual(result['entries'][0]['correction']['references'][0]['address_raw'], printed)

    def test_muroto_ebisu_glyph_comparison_requires_the_name_locality_and_full_parcel(self):
        acquired = '高知県室戸市元米ｹ谷西甲2737番地15'
        for name, printed in (
            ('惠美須神社', '高知県室戸市元米ヶ谷西甲2737番地'),
            ('惠美須神社', '高知県室戸市元米ヶ谷西甲2737番地151'),
            ('惠美須神社', '高知県室戸市元米ヶ谷2060番地'),
            ('恵美須神社', '高知県室戸市元米ヶ谷西甲2737番地15'),
        ):
            with self.subTest(name=name, printed=printed):
                dataset, proposal = self.fixture('39', '高知県', name, 'えびすじんじゃ', acquired, printed)
                self.assertEqual(eligible(apply_corrections(dataset, proposal)), [])

    def test_shimanto_egawasaki_forms_preserve_each_shrine_and_parcel(self):
        for name, reading, parcel, printed_parcel in (
            ('天神社', 'てんじんじゃ', '2432', '２４３２'),
            ('鷣神社', 'はいたかじんじゃ', '2972', '２９７２'),
        ):
            with self.subTest(name=name, parcel=parcel):
                acquired = '高知県四万十市西土佐江川崎'+parcel+'番地'
                printed = '高知県四万十市西土佐江川﨑'+printed_parcel+'番地'
                dataset, proposal = self.fixture('39', '高知県', name, reading, acquired, printed)
                result = apply_corrections(dataset, proposal)
                self.assertEqual(len(eligible(result)), 1)
                self.assertEqual(result['facilities'], dataset['facilities'])
                self.assertEqual(result['entries'][0]['correction']['references'][0]['address_raw'], printed)

    def test_shimanto_egawasaki_forms_do_not_link_other_names_or_parcel_branches(self):
        for name, old, new in (
            ('天神社', '2432', '2432番地1'), ('天神社', '2972', '2972番地'),
            ('鷣神社', '2972', '2432番地'), ('別神社', '2972', '2972番地'),
        ):
            with self.subTest(name=name, old=old, new=new):
                dataset, proposal = self.fixture('39', '高知県', name, 'はいたかじんじゃ',
                    '高知県四万十市西土佐江川崎'+old+'番地', '高知県四万十市西土佐江川﨑'+new)
                self.assertEqual(eligible(apply_corrections(dataset, proposal)), [])

    def test_kameoka_sogabe_forms_compare_only_the_documented_shrines_and_parcels(self):
        for name, reading, locality, lot, other_lot in (
            ('八幡宮社', 'はちまんぐうしゃ', '西条丙中垣内', '1-1', '1-2'),
            ('若宮神社', 'わかみやじんじゃ', '南条中荒水代', '4', '40'),
        ):
            with self.subTest(name=name):
                acquired = '亀岡市曽我部町'+locality+lot
                address = '亀岡市曽我部町'+locality.replace('条', '條')
                data, proposal = self.fixture('26', '京都府', name, reading, acquired, address+lot)
                result = apply_corrections(data, proposal)
                self.assertEqual(len(eligible(result)), 1)
                self.assertEqual(result['facilities'], data['facilities'])
                data, proposal = self.fixture('26', '京都府', name, reading, acquired, address+other_lot)
                self.assertEqual(eligible(apply_corrections(data, proposal)), [])

    def test_goto_and_hokuto_published_glyphs_compare_only_at_the_documented_parcels(self):
        for code, pref, name, reading, acquired, printed in (
            ('42', '長崎県', '神﨑神社', 'かんざきじんじゃ', '五島市岐宿町川原字神崎3482番地',
             '長崎県五島市岐宿町川原字神﨑３４８２番地'),
            ('19', '山梨県', '天神社', 'てんじんしゃ', '北杜市武川町柳沢2351',
             '山梨県北杜市武川町柳澤２３５１番地'),
        ):
            with self.subTest(name=name):
                data, proposal = self.fixture(code, pref, name, reading, acquired, printed)
                result = apply_corrections(data, proposal)
                self.assertEqual(len(eligible(result)), 1)
                self.assertEqual(result['facilities'], data['facilities'])
                data, proposal = self.fixture(code, pref, name, reading, acquired, printed+'1')
                self.assertEqual(eligible(apply_corrections(data, proposal)), [])

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

    def test_arasu_shrine_compares_the_parcel_printed_in_kanji(self):
        acquired = '舞鶴市小倉フル宮13'
        printed = '舞鶴市大字小倉小字フル宮十三番地'
        dataset, proposal = self.fixture('26', '京都府', '阿良須神社', 'あらすじんじゃ', acquired, printed)
        result = apply_corrections(dataset, proposal)
        self.assertEqual(len(eligible(result)), 1)
        self.assertEqual(result['facilities'], dataset['facilities'])
        self.assertEqual(result['entries'][0]['correction']['references'][0]['address_raw'], printed)

    def test_arasu_parcel_comparison_requires_the_shrine_and_the_complete_address(self):
        for name, acquired, printed in (
            ('阿良須神社', '舞鶴市小倉フル宮13-1', '舞鶴市大字小倉小字フル宮十三番地'),
            ('阿良須神社', '舞鶴市小倉フル宮13', '舞鶴市大字小倉小字フル宮十四番地'),
            ('阿良須神社', '舞鶴市小倉フル宮13', '舞鶴市大字小倉十三番地'),
            ('別神社', '舞鶴市小倉フル宮13', '舞鶴市大字小倉小字フル宮十三番地'),
        ):
            with self.subTest(name=name, acquired=acquired, printed=printed):
                dataset, proposal = self.fixture('26', '京都府', name, 'あらすじんじゃ', acquired, printed)
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

    def test_motooka_yasaka_compares_the_documented_parcel_branch(self):
        acquired = '福岡市西区元岡26411'
        printed = '福岡県福岡市西区大字元岡２６４１番地１'
        dataset, proposal = self.fixture(
            '40', '福岡県', '八坂神社', 'やさかじんじゃ', acquired, printed,
        )
        result = apply_corrections(dataset, proposal)
        self.assertEqual(len(eligible(result)), 1)
        self.assertEqual(result['facilities'], dataset['facilities'])
        self.assertEqual(result['entries'][0]['correction']['references'][0]['address_raw'], printed)

    def test_motooka_parcel_comparison_is_limited_to_this_shrine_and_branch(self):
        for name, acquired, printed in (
            ('八坂神社', '福岡市西区元岡26411', '福岡市西区元岡2641'),
            ('八坂神社', '福岡市西区元岡26411', '福岡市西区元岡2641-10'),
            ('八坂神社', '福岡市西区元岡26421', '福岡市西区元岡2642-1'),
            ('別神社', '福岡市西区元岡26411', '福岡市西区元岡2641-1'),
        ):
            with self.subTest(name=name, acquired=acquired, printed=printed):
                dataset, proposal = self.fixture(
                    '40', '福岡県', name, 'やさかじんじゃ', acquired, printed,
                )
                self.assertEqual(eligible(apply_corrections(dataset, proposal)), [])

    def test_hara_shrine_compares_the_documented_subdistrict_omission(self):
        acquired = '高松市牟礼町原井手東651番地'
        printed = '香川県高松市牟礼町原651'
        dataset, proposal = self.fixture(
            '37', '香川県', '幡羅八幡神社', 'はらはちまんじんじゃ', acquired, printed,
        )
        result = apply_corrections(dataset, proposal)
        self.assertEqual(len(eligible(result)), 1)
        self.assertEqual(result['facilities'], dataset['facilities'])
        self.assertEqual(result['entries'][0]['correction']['references'][0]['address_raw'], printed)

    def test_hara_subdistrict_comparison_keeps_the_name_and_parcel_scope(self):
        for name, acquired, printed in (
            ('幡羅八幡神社', '高松市牟礼町原井手東651番地', '高松市牟礼町原651-1'),
            ('幡羅八幡神社', '高松市牟礼町原上井手西651番地', '高松市牟礼町原651'),
            ('幡羅八幡神社', '高松市牟礼町原井手東652番地', '高松市牟礼町原652'),
            ('別神社', '高松市牟礼町原井手東651番地', '高松市牟礼町原651'),
        ):
            with self.subTest(name=name, acquired=acquired, printed=printed):
                dataset, proposal = self.fixture(
                    '37', '香川県', name, 'はらはちまんじんじゃ', acquired, printed,
                )
                self.assertEqual(eligible(apply_corrections(dataset, proposal)), [])

    def test_minobu_documented_shrine_addresses_preserve_the_printed_localities(self):
        for name, reading, acquired, printed in (
            ('十二天神社', 'じゅうにてんじんじゃ', '下八木沢字太田43', '下八木沢４３番地'),
            ('山神社', 'やまじんじゃ', '上八木沢宮之前18', '上八木沢１８番地'),
            ('諏訪神社', 'すわじんじゃ', '古関宮ノ平1382', '古関１３８２番地'),
        ):
            with self.subTest(name=name):
                address = '山梨県南巨摩郡身延町' + printed
                dataset, proposal = self.fixture('19', '山梨県', name, reading, '南巨摩郡身延町' + acquired, address)
                result = apply_corrections(dataset, proposal)
                self.assertEqual(len(eligible(result)), 1)
                self.assertEqual(result['facilities'], dataset['facilities'])
                self.assertEqual(result['entries'][0]['correction']['references'][0]['address_raw'], address)

    def test_minobu_subdistrict_comparison_keeps_the_shrine_and_complete_parcel_scope(self):
        for name, acquired, printed in (
            ('十二天神社', '下八木沢字太田43', '下八木沢43-1'),
            ('十二天神社', '下八木沢字太田44', '下八木沢44'),
            ('山神社', '上八木沢向山18', '上八木沢18'),
            ('諏訪神社', '古関宮ノ平1382', '古関1383'),
            ('別神社', '古関宮ノ平1382', '古関1382'),
        ):
            with self.subTest(name=name, acquired=acquired, printed=printed):
                dataset, proposal = self.fixture(
                    '19', '山梨県', name, 'すわじんじゃ', '南巨摩郡身延町' + acquired, '南巨摩郡身延町' + printed,
                )
                self.assertEqual(eligible(apply_corrections(dataset, proposal)), [])
