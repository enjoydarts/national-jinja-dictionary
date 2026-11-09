import unittest
from njd.adapters.central import parse_nara, parse_osaka, parse_rows, decode_html
from njd.http import Page

class CentralTest(unittest.TestCase):
    def test_nara_same_row_and_missing_reading(self):
        html='<table><tr><td>例神社<br><span class="kana">れいじんじゃ</span></td><td>〒630-0000<br>奈良市例町１</td><td><a href="https://example.test">公式サイト</a></td></tr><tr><td>同名神社</td><td>奈良市別町２</td><td></td></tr></table>'
        rows=parse_nara(html)
        self.assertEqual([(r['name'],r['reading_raw'],r['address']) for r in rows],[('例神社','れいじんじゃ','奈良市例町１'),('同名神社','','奈良市別町２')])
        self.assertEqual(rows[0]['official_url'],'https://example.test')
    def test_osaka_alias_is_not_name_or_address(self):
        html='<table><tr><td>1</td><td><a href="one.html">例神社<br>（れいじんじゃ）</a></td><td><font>通称例</font><br>豊中市例町</td></tr></table>'
        r=parse_osaka(html)[0]
        self.assertEqual((r['name'],r['reading_raw'],r['address']),('例神社','れいじんじゃ','豊中市例町'))
    def test_table_headers_control_columns_and_nested_rows(self):
        html='<table><tr><th>神社名(正称)</th><th>主祭神</th><th>鎮座地</th><th>御神徳</th></tr><tr><td><a href="x.html">例神社</a></td><td>例神</td><td>松江市例町１</td><td>開運</td></tr></table>'
        r=parse_rows(html,'shimane')[0]
        self.assertEqual((r['name'],r['reading_raw'],r['address']),('例神社','','松江市例町１'))
        self.assertEqual(parse_rows('<table><tr><td>例神社</td><td>例神</td></tr></table>','shimane'),[])
    def test_meta_charset(self):
        raw='<meta charset="Shift_JIS">滋賀県'.encode('cp932')
        self.assertIn('滋賀県',decode_html(Page('https://example.test',200,{},raw,'2026-01-01')))

class MoreCentralTest(unittest.TestCase):
    def test_shizuoka_explicit_reading(self):
        from njd.adapters.central import parse_shizuoka
        h='<table><tr><th>神社名</th><th>よみがな</th><th>鎮座地</th><th></th></tr><tr><td><a href="jinja.php?id=1">例神社</a></td><td>れいじんじゃ</td><td>三島市例町１</td><td>詳細</td></tr></table>'
        self.assertEqual(parse_shizuoka(h)[0]['reading_raw'],'れいじんじゃ')
    def test_nagano_without_reading(self):
        from njd.adapters.central import parse_nagano
        h='<table><tr><td>神社名</td><td>〒</td><td>住所</td></tr><tr><td>例神社</td><td>389-0000</td><td>飯山市例町１</td></tr></table>'
        self.assertEqual(parse_nagano(h)[0]['address'],'飯山市例町１')
    def test_ishikawa_primary_ruby(self):
        from njd.adapters.central import parse_ishikawa
        h='<h1 class="title"><ruby>例神社<rp>（</rp><rt>れいじんじゃ</rt><rp>）</rp></ruby></h1><dl><dt>鎮座地</dt><dd><p>金沢市例町１</p></dd></dl>'
        self.assertEqual(parse_ishikawa(h)[0]['name'],'例神社')
    def test_tottori_labeled_details_only(self):
        from njd.adapters.central import parse_tottori
        h='<table><tr><td>神社名</td><td>例神社</td></tr><tr><td>よみ</td><td>れいじんじゃ</td></tr><tr><td>住所</td><td>鳥取市例町１</td></tr></table>'
        self.assertEqual(parse_tottori(h)[0]['reading_raw'],'れいじんじゃ')
    def test_shiga_list_pair(self):
        from njd.adapters.central import parse_shiga
        h='<a href="ycDB_02jinja-pc-detail.html?mode:view=1&view:oid=7" class="news_title"><font>〔大津〕</font> 例神社</a><br><span>〒5200000 大津市例町</span><br>'
        self.assertEqual(parse_shiga(h)[0]['name'],'例神社')

class FukuiTest(unittest.TestCase):
    def test_precinct_shrines_not_collected_as_main_shrine(self):
        from njd.adapters.central import parse_fukui
        h='<div class="m_top5 clearfix"><div class="result_shrine"><a href="javascript:clickDetail(\'123\');"><span>れいじんじゃ</span><br>例神社</a></div><div class="result_recinct">稲荷社、八幡神社</div><div class="result_enshrined">福井県小浜市例町１</div></div>'
        rows=parse_fukui(h)
        self.assertEqual(len(rows),1)
        self.assertEqual((rows[0]['name'],rows[0]['reading_raw'],rows[0]['source_id']),('例神社','れいじんじゃ','123'))

class CrawlTest(unittest.TestCase):
    def test_shizuoka_pagination_query_order(self):
        from njd.adapters.central import CONFIG,links
        url='http://www.shizuoka-jinjacho.or.jp/shokai/search.php?mode=city&city=14'
        found=links('<a href="./search.php?mode=city&amp;search=&amp;city=14&amp;p=2">次へ</a>',url,CONFIG['shizuoka'][4])
        self.assertEqual(found,[url.replace('&city=14','&search=&city=14&p=2')])
    def test_osaka_only_municipal_index_links_followed(self):
        from njd.adapters.central import collect_source,CONFIG
        start=CONFIG['osaka'][3];city=start.replace('index.html','dai1shibu/toyonaka-city/toyonaka.html')
        html={start:'<a href="dai1shibu/toyonaka-city/toyonaka.html">豊中市</a>',city:'<table><tr><td>1</td><td><a href="01001detail.html">例神社<br>（れいじんじゃ）</a></td><td>豊中市例町</td></tr></table>'}
        class Fake:
            calls=[]
            def fetch(self,url):
                self.calls.append(url)
                return Page(url,200,{'content-type':'text/html;charset=utf-8'},html[url].encode(),'2026-01-01T00:00:00+00:00')
        c=Fake();d=collect_source('osaka',c)
        self.assertEqual(c.calls,[start,city]);self.assertEqual(len(d['facilities']),1)

class TottoriInventoryTest(unittest.TestCase):
    def test_unlinked_inventory_rows_retained_pending(self):
        from njd.adapters.central import parse_tottori
        h='<table><tr><td>番号</td><td>神社名</td><td>鎮座地</td></tr><tr><td>1</td><td>例神社</td><td>鳥取市例町</td></tr><tr><td>2</td><td><a href="/pages/1/">別神社</a></td><td>鳥取市別町</td></tr></table>'
        rows=parse_tottori(h)
        self.assertEqual([(r['name'],r['reading_raw']) for r in rows],[('例神社','')])

class IshikawaSearchTest(unittest.TestCase):
    def test_search_cards_keep_each_ruby_address_and_native_identity_together(self):
        from njd.adapters.central import parse_ishikawa
        h='<li class="search_li"><a href="https://example.test/shrine/j1/"></a><h3><ruby>例神社<rp>（</rp><rt>れいじんじゃ</rt><rp>）</rp></ruby></h3><dl><dt>[氏子区域]</dt><dd>別の地域</dd><dt>[鎮座地]</dt><dd>七尾市例町１</dd></dl></li><li class="search_li"><a href="https://example.test/shrine/j2/"></a><h3><ruby>同名神社<rt>どうめいじんじゃ</rt></ruby></h3><dl><dt>[鎮座地]</dt><dd>七尾市別町２</dd></dl></li>'
        rows=parse_ishikawa(h)
        self.assertEqual([(r['name'],r['reading_raw'],r['address']) for r in rows],[('例神社','れいじんじゃ','七尾市例町１'),('同名神社','どうめいじんじゃ','七尾市別町２')])
        self.assertEqual(rows[0]['source_id'],'https://example.test/shrine/j1/')

class IshikawaContactTest(unittest.TestCase):
    def test_contact_shrine_link_is_not_primary_identity(self):
        from njd.adapters.central import parse_ishikawa
        h='<li class="search_li"><a href="https://example.test/shrine/j1/"></a><h3><ruby>例神社<rt>れいじんじゃ</rt></ruby></h3><dl><dt>[鎮座地]</dt><dd>七尾市例町１</dd><dt>[TEL]</dt><dd><a href="https://example.test/shrine/j2/">連絡は別神社へ</a></dd></dl></li>'
        rows=parse_ishikawa(h)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['source_id'],'https://example.test/shrine/j1/')

class AichiTest(unittest.TestCase):
    def test_explicit_api_fields_and_no_nickname_as_surface(self):
        from njd.adapters.central import parse_aichi
        data={'total_rows':2,'list':[{'id':7,'name':'例神社','kana':'レイジンジャ','nickname':'例の宮','pref':'愛知県','city':'名古屋市中区','addr':'例町','house_num':'１－２'}, {'id':8,'name':'同名神社','kana':None,'pref':'愛知県','city':'岡崎市','addr':'別町','house_num':None}]}
        rows=parse_aichi(data)
        self.assertEqual([(r['name'],r['reading_raw'],r['address']) for r in rows],[('例神社','レイジンジャ','愛知県名古屋市中区例町１－２'),('同名神社','','愛知県岡崎市別町')])
        self.assertEqual(rows[0]['municipality'],'名古屋市中区')
        self.assertEqual(rows[0]['source_id'],'7')
    def test_all_results_count_mismatch_fails_closed(self):
        from njd.adapters.central import parse_aichi
        with self.assertRaises(ValueError):parse_aichi({'total_rows':3,'list':[]})

class AichiIncompleteAddressTest(unittest.TestCase):
    def test_missing_street_is_not_filled_from_postcode_or_parishioner_area(self):
        from njd.adapters.central import parse_aichi
        rows=parse_aichi({'total_rows':1,'list':[{'id':'x','name':'例神社','kana':'れいじんじゃ','pref':'愛知県','city':'丹羽郡大口町','addr':'','house_num':'2丁目305番地','parishioner_area_summary':'推測に使わない'}]})
        self.assertEqual(rows[0]['address'],'')
        self.assertEqual(rows[0]['address_raw'],'愛知県丹羽郡大口町2丁目305番地')

class AichiGaijiTest(unittest.TestCase):
    def test_svg_gaiji_name_is_not_truncated_to_a_verified_word(self):
        from njd.adapters.central import parse_aichi,aichi_unrenderable_names
        raw='鳴海<svg><use href="gaiji.svg#x"></use></svg>神社'
        data={'total_rows':1,'list':[{'id':'svg','name':raw,'kana':'なるみじんじゃ','pref':'愛知県','city':'名古屋市','addr':'例町','house_num':'1'}]}
        rows=parse_aichi(data)
        self.assertEqual(rows[0]['name'],raw)
        self.assertEqual(rows[0]['name_rendering_status'],'external_glyph')
        self.assertEqual(aichi_unrenderable_names(data)[0]['name_html_raw'],raw)

class AichiPrefectureTest(unittest.TestCase):
    def test_explicit_other_prefecture_does_not_become_aichi(self):
        from njd.adapters.central import parse_aichi
        with self.assertRaises(ValueError):
            parse_aichi({'total_rows':1,'list':[{'id':'x','name':'例神社','kana':'れいじんじゃ','pref':'岐阜県','city':'岐阜市','addr':'例町','house_num':'1'}]})
