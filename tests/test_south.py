import unittest
from njd.adapters import south
from njd.http import Page

class SouthTests(unittest.TestCase):
    def test_okayama_separates_same_name_and_captures_native_id(self):
        html='''<div class="pageLead">2件の神社が該当しました。</div><a class="shrineList__row" href="/search/1"><div class="shrineList__cell">01001</div><div class="shrineList__cell">試験神社</div><div class="shrineList__cell">シケンジンジャ</div><div class="shrineList__cell">通称</div><div class="shrineList__cell"><span class="item-zip">000-0000</span><span class="item-address">試験市甲1</span></div></a><a class="shrineList__row" href="/search/2"><div class="shrineList__cell">01002</div><div class="shrineList__cell">試験神社</div><div class="shrineList__cell"></div><div class="shrineList__cell"></div><div class="shrineList__cell"><span class="item-address">試験市乙2</span></div></a>'''
        records=south.parse_okayama(self.page(html))
        self.assertEqual(len(records),2)
        self.assertEqual(records[0]['source_id'],'01001')
        self.assertEqual(records[0]['address'],'試験市甲1')
        self.assertEqual(records[1]['reading_raw'],'')
        self.assertNotEqual(records[0]['source_id'],records[1]['source_id'])
    def test_kagoshima_preserves_spelling_and_removes_postcode_from_address(self):
        html='''<div class="shrine_list"><h3>試驗神社</h3><div class="shrine_detail"><ul><li>神社名：試驗神社</li><li>神社名カナ：シケンジンジャ</li><li>鎮座地：〒000-0000 試験市甲1</li></ul><p class="btn"><a href="/shrine-search/area-x/city/123/">この神社の詳細を見る</a></p></div></div>'''
        r=south.parse_kagoshima(self.page(html))[0]
        self.assertEqual((r['name'],r['reading_raw'],r['address'],r['source_id']),('試驗神社','シケンジンジャ','試験市甲1','123'))
        self.assertIn('〒000-0000',r['address_raw'])
    def test_unrecognized_structure_fails_closed(self):
        with self.assertRaises(ValueError):south.parse_okayama(self.page('<p>changed</p>'))
        with self.assertRaises(ValueError):south.parse_kagoshima(self.page('<p>changed</p>'))
    def test_ehime_table_does_not_use_priest_name_or_deity_reading(self):
        html='<table><tr><th>神社名</th><td>試験神社</td></tr><tr><th>ふりがな</th><td>しけんじんじゃ</td></tr><tr><th>宮司名</th><td>試験 太郎</td></tr><tr><th>神社主祭神</th><td>試験命（しけんのみこと）</td></tr><tr><th>神社鎮座地</th><td>試験市甲1</td></tr></table>'
        r=south.parse_ehime(self.page(html))[0]
        self.assertEqual((r['name'],r['reading_raw'],r['address']),('試験神社','しけんじんじゃ','試験市甲1'))
    def test_okinawa_missing_reading_remains_empty(self):
        html='<p id="shrine"><b>試験神社</b><br>沖縄県試験市甲1<br>TEL:0000<br><a href="https://example.test/">公式</a></p><p id="group"><b>青年会</b><br>沖縄県試験市甲2</p>'
        r=south.parse_okinawa(self.page(html))
        self.assertEqual(len(r),1)
        self.assertEqual(r[0]['reading_raw'],'')
        self.assertEqual(r[0]['address'],'沖縄県試験市甲1')
    def test_kagawa_listing_missing_reading_and_distinct_links(self):
        html='<li class="c-entries__item"><a href="/shrine/one/"><h2 class="c-entry-summary__title">試験神社</h2><div class="location"><p>試験市甲1</p></div></a></li>'
        r=south.parse_kagawa(self.page(html))[0]
        self.assertEqual((r['name'],r['reading_raw'],r['address']),('試験神社','','試験市甲1'))
    def test_kumamoto_listing_does_not_use_contact_address(self):
        html='<table class="c-table"><tr><th>対象神社名</th><th>お住まいの地域</th></tr><tr><th>試験神社</th><td>試験市甲1</td><td><a href="tel:0000">0000</a>連絡先市乙2</td><td></td><td><a href="/patron-god/one/">詳細を見る</a></td></tr></table>'
        r=south.parse_kumamoto(self.page(html))[0]
        self.assertEqual(r['address'],'試験市甲1')
    def test_okinawa_unprefixed_address_and_repeated_html_ids(self):
        html='<p id="same"><b>甲神社</b><br>那覇市甲1<br>TEL:0000</p><p id="same"><b>乙神社</b><br>宮古島市乙2<br>TEL:0000</p>'
        rows=south.parse_okinawa(self.page(html))
        self.assertEqual(len(rows),2)
        self.assertNotEqual(rows[0]['source_id'],rows[1]['source_id'])
    def test_okinawa_unclosed_bold_title_does_not_capture_address_as_name(self):
        html='<p id="one"><B>甲神社<BR>那覇市甲1<BR>TEL:0000</p>'
        row=south.parse_okinawa(self.page(html))[0]
        self.assertEqual(row['name'],'甲神社')
    def test_saga_detail_preserves_parenthetical_listed_title(self):
        html='<h1 id="pageTit">試験神社（通称）</h1><div class="entry-content"><p>【鎮座地】<br>試験市甲1</p><p>【祭神】<br>試験命</p></div>'
        r=south.parse_saga(self.page(html))[0]
        self.assertEqual((r['name'],r['reading_raw'],r['address']),('試験神社（通称）','','試験市甲1'))
    def test_nagasaki_uses_only_prefectural_shrine_link_blocks(self):
        html='<div id="other"><a href="https://example.test/agency/">他県神社庁</a></div><div id="bk17860131"><a href="https://example.test/one/">試験神社</a></div>'
        r=south.parse_nagasaki(self.page(html))
        self.assertEqual(len(r),1)
        self.assertEqual((r[0]['name'],r[0]['address'],r[0]['reading_raw']),('試験神社','',''))
    def test_kochi_initial_ssr_row_assembles_only_explicit_address_parts(self):
        html='<div class="wixui-repeater__item" id="comp-ljqf2796__native-id"><div id="comp-ljqf2799__native-id" class="wixui-rich-text">試験神社</div><div id="comp-ljqf279d__native-id" class="wixui-rich-text">甲1番地</div><div id="comp-ljqlom9b__native-id" class="wixui-rich-text">高知県試験市</div></div>'
        r=south.parse_kochi(self.page(html))[0]
        self.assertEqual((r['name'],r['reading_raw'],r['address'],r['source_id']),('試験神社','','高知県試験市甲1番地','native-id'))
    def test_collection_keeps_conflicting_native_identity_for_builder_review(self):
        pages={'https://example.test/1':self.page('<a href="/2">next</a>'),'https://example.test/2':self.page('<p>second</p>')}
        class Client:
            def fetch(self,url):return pages[url]
        def parse(page):
            name='甲神社' if 'next' in page.text else '乙神社'
            return [south.record(page,name,'しけんじんじゃ','試験市甲1','explicit-row',source_id='same-native-id')]
        data=south._collect(Client(),'test','33','試験県','試験県神社庁',['https://example.test/1'],parse,r'https://example.test/2')
        self.assertEqual(data['collection']['source_rows_observed'],2)
        self.assertEqual(len(data['facilities']),1)
        self.assertEqual(data['entries'][0]['status'],'pending')
    def test_ehime_missing_address_remains_pending_source_record(self):
        html='<table><tr><th>神社名</th><td>試験神社</td></tr><tr><th>ふりがな</th><td>しけんじんじゃ</td></tr></table>'
        r=south.parse_ehime(self.page(html))[0]
        self.assertEqual(r['address'],'')
    def test_limited_collection_reports_observed_and_selected_separately(self):
        page=self.page('<p>two explicit source rows</p>')
        class Client:
            def fetch(self,url):return page
        def parse(p):return [south.record(p,'甲神社','しけんじんじゃ','試験市甲1','one',source_id='one'),south.record(p,'乙神社','しけんじんじゃ','試験市甲2','two',source_id='two')]
        data=south._collect(Client(),'test','33','試験県','試験県神社庁',['https://example.test/'],parse,r'(?!)',limit=1)
        self.assertEqual(data['collection']['source_rows_observed'],2)
        self.assertEqual(data['collection']['selected_rows'],1)
        self.assertFalse(data['collection']['traversal_complete'])
    @staticmethod
    def page(html):return Page('https://example.test/search/',200,{'content-type':'text/html;charset=utf-8'},html.encode(),'2026-11-08T00:00:00+00:00')
