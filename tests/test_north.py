import unittest
from njd.adapters import north
from njd.http import Page


def page(html):
    return Page('https://example.org/list/',200,{'content-type':'text/html; charset=utf-8'},html.encode(),'2026-11-08T00:00:00+00:00')


class NorthTests(unittest.TestCase):
    def test_akita_keeps_alias_in_raw_reading_and_separate_same_names(self):
        p=page('''<table><tr><th>神社名(漢字)</th><th>神社名(かな)</th><th>市町村</th><th>鎮座地</th></tr>
        <tr><th><a href="/a/">架空神社</a></th><td>かくうじんじゃ通称：おみや</td><td>架空市</td><td>〒000-0000 架空市一丁目</td></tr>
        <tr><th>架空神社</th><td>かくうじんじゃ</td><td>仮市</td><td>仮市二丁目</td></tr></table>''')
        rows=north.parse_akita(p)
        self.assertEqual(len(rows),2)
        self.assertEqual(rows[0]['reading_raw'],'かくうじんじゃ通称：おみや')
        self.assertEqual(rows[0]['address'],'架空市一丁目')
        self.assertEqual(rows[0]['address_raw'],'〒000-0000 架空市一丁目')
        self.assertNotEqual(rows[0]['address'],rows[1]['address'])
        self.assertEqual(rows[0]['url'],'https://example.org/list/')
        self.assertIn('架空神社',rows[0]['evidence'])

    def test_akita_rejects_unknown_structure(self):
        with self.assertRaises(ValueError): north.parse_akita(page('<table><tr><td>架空神社</td></tr></table>'))

    def test_akita_empty_category_is_valid_with_header(self):
        self.assertEqual(north.parse_akita(page('<table><tr><th>神社名(漢字)</th><th>神社名(かな)</th><th>市町村</th><th>鎮座地</th></tr></table>')),[])

    def test_meta_declared_encoding_is_used(self):
        p=Page('https://example.org/',200,{'content-type':'text/html'},'<meta charset="Shift_JIS">架空神社'.encode('shift_jis'),'now')
        self.assertIn('架空神社',north.decode(p))

class MoreNorthTests(unittest.TestCase):
    def test_miyagi_only_shrine_name_reading_and_location(self):
        rows=north.parse_miyagi(page('''<div class="simple-list-item"><a href="detail.php?code=123">架空神社（かくうじんじゃ）</a><div class="simple-meta">[鎮座地] 宮城県架空市一番</div><div class="simple-meta">[連絡先] 電話</div></div>'''))
        self.assertEqual([(r['name'],r['reading_raw'],r['address'],r['source_id']) for r in rows],[('架空神社','かくうじんじゃ','宮城県架空市一番','123')])

    def test_tochigi_does_not_take_priest_as_reading(self):
        rows=north.parse_tochigi(page('''<table class="shrine_info"><tr><th>本務神社名</th><th>宮司名</th><th>住所</th><th>TEL</th></tr><tr><td>架空神社<br>（かくうじんじゃ）</td><td>仮名人</td><td>仮市架空町</td><td>000</td></tr><tr><td>架空社</td><td>かりなひと</td><td>仮市二丁目</td><td>000</td></tr></table>'''))
        self.assertEqual(rows[0]['reading_raw'],'かくうじんじゃ')
        self.assertEqual(rows[1]['reading_raw'],'')
        self.assertEqual(rows[1]['name'],'架空社')

    def test_tokyo_detail_ignores_deity_furigana(self):
        r=north.parse_tokyo(page('''<div class="s_in_tl01">架空神社</div><div class="s_in_rubi">かくうじんじゃ</div><div class="s_tx01">別神（べつかみ）</div><div class="s_ad_box"><ul><li class="s_ad">所在地</li><li class="s_ad_in">〒000-0000 東京都仮区一番</li></ul></div>'''))[0]
        self.assertEqual((r['name'],r['reading_raw'],r['address']),('架空神社','かくうじんじゃ','東京都仮区一番'))

class XMLNorthTests(unittest.TestCase):
    def test_fukushima_reads_only_shrine_fields_and_keeps_homonyms(self):
        rows=north.parse_fukushima(page('''<Locations><Locate><name>架空神社</name><furigana>かくうじんじゃ</furigana><address>福島県仮市一番</address><tinzati2>仮市</tinzati2><gosaishin>別神（べつかみ）</gosaishin></Locate><Locate><name>架空神社</name><furigana></furigana><address>福島県仮市二番</address></Locate></Locations>'''))
        self.assertEqual(len(rows),2)
        self.assertEqual(rows[0]['reading_raw'],'かくうじんじゃ')
        self.assertEqual(rows[1]['reading_raw'],'')
        self.assertEqual(rows[1]['address'],'福島県仮市二番')

class EmptyNorthTests(unittest.TestCase):
    def test_akita_explicit_no_results_row_is_not_a_facility(self):
        self.assertEqual(north.parse_akita(page('<table><tr><th>神社名(漢字)</th><th>神社名(かな)</th><th>市町村</th><th>鎮座地</th></tr><tr><td colspan="4">見つかりません。</td></tr></table>')),[])

class RegionalNorthTests(unittest.TestCase):
    def test_hokkaido_list_has_no_inferred_reading(self):
        r=north.parse_hokkaido(page('<div class="lineup"><div class="block"><h4><a href="/shrine/">架空神社</a></h4><span class="address">仮市架空町</span><span class="tel">000</span></div></div>'))[0]
        self.assertEqual((r['name'],r['reading_raw'],r['address']),('架空神社','','仮市架空町'))

    def test_aomori_accepts_only_numbered_facility_rows(self):
        r=north.parse_aomori(page('<div id="list_1"><table><tr><th scope="row">１</th><td>架空神社</td><td>仮市一番</td></tr></table></div>'))[0]
        self.assertEqual((r['name'],r['reading_raw'],r['address']),('架空神社','','仮市一番'))

    def test_yamagata_detail_reading_is_small_title(self):
        r=north.parse_yamagata(page('<h1 class="p-detail__name">架空神社<small>（カクウジンジャ）</small></h1><li><span class="p-detail__item">鎮座地</span>仮市一番</li>'))[0]
        self.assertEqual((r['name'],r['reading_raw'],r['address']),('架空神社','カクウジンジャ','仮市一番'))

    def test_kanagawa_detail_excludes_precinct_shrine_names(self):
        r=north.parse_kanagawa(page('<div class="shrineList"><div class="shrineName"><a><h2>架空神社</h2></a><span class="ruby">かくうじんじゃ</span></div><div class="address">住所： 〒000-0000 仮市 一番</div><div>境内社：別社</div></div>'))[0]
        self.assertEqual((r['name'],r['reading_raw'],r['address']),('架空神社','かくうじんじゃ','仮市 一番'))

    def test_saitama_detail_missing_reading_stays_empty(self):
        r=north.parse_saitama(page('<table class="data_shrine"><caption id="shrine_name">架空神社</caption><tr><th>鎮座地</th><td><span id="shrine_address">仮市一番</span></td></tr></table>'))[0]
        self.assertEqual((r['name'],r['reading_raw'],r['address']),('架空神社','','仮市一番'))

class WalkNorthTests(unittest.TestCase):
    def test_miyagi_next_page_collected_once_with_cache(self):
        from tempfile import TemporaryDirectory
        from njd.http import Client
        first='https://miyagi-jinjacho.or.jp/jinja-search/list.php?chinzachi=&jinja_name=&jinja_kana='
        second='https://miyagi-jinjacho.or.jp/jinja-search/list.php?page=1'
        def item(name,code,reading,address):
            return f'<div class="simple-list-item"><a href="detail.php?code={code}">{name}（{reading}）</a><div class="simple-meta">[鎮座地] {address}</div></div>'
        bodies={first:item('架空神社','1','かくうじんじゃ','宮城県仮市一番')+'<a href="list.php?page=1">次の15件</a>',second:item('仮想神社','2','かそうじんじゃ','宮城県仮市二番')}
        def transport(url,timeout,agent):
            if url.endswith('/robots.txt'):return 404,{'content-type':'text/plain'},b''
            return 200,{'content-type':'text/html; charset=utf-8'},bodies[url].encode()
        with TemporaryDirectory() as cache:
            data=north.collect_miyagi(Client(cache,interval=0,transport=transport))
        self.assertEqual([f['listed_name'] for f in data['facilities']],['架空神社','仮想神社'])
        self.assertEqual([e['reading'] for e in data['entries']],['かくうじんじゃ','かそうじんじゃ'])
        self.assertEqual(len(data['collection']['pages']),2)

class LastNorthTests(unittest.TestCase):
    def test_toyama_uses_shrine_location_and_not_parish_address(self):
        r=north.parse_toyama(page('<table><tr><th>神社名</th><td>架空神社</td></tr><tr><th>社名カナ</th><td>カクウジンジャ</td></tr><tr><th>住所</th><td>仮市広域</td></tr><tr><th>鎮座地</th><td>仮市一番</td></tr><tr><th>ホームページ</th><td><a href="https://other.example/">宮司所在神社</a></td></tr></table>'))[0]
        self.assertEqual((r['name'],r['reading_raw'],r['address']),('架空神社','カクウジンジャ','仮市一番'))
        self.assertNotIn('official_url',r)

    def test_ibaraki_region_preserves_explicit_city_granularity(self):
        r=north.parse_ibaraki(page('<table><tr><td><img></td><td><a href="jinja/123.html">架空神社</a></td><td>かくうじんじゃ</td><td>仮市</td></tr></table>'))[0]
        self.assertEqual((r['name'],r['reading_raw'],r['address']),('架空神社','かくうじんじゃ','仮市'))
        self.assertIn('municipality only',r['address_context'])

class IwateNorthTests(unittest.TestCase):
    def test_iwate_county_list_excludes_national_links_and_missing_reading(self):
        r=north.parse_iwate(page('<div id="block141"><section><a href="https://external.example/">対象外神宮</a></section></div><div id="block142"><section data-record-id="21"><a href="https://example.org/official/">架空神社（仮市一番鎮座）</a></section></div>'))[0]
        self.assertEqual((r['name'],r['reading_raw'],r['address']),('架空神社','','仮市一番'))
        self.assertEqual(r['official_url'],'https://example.org/official/')

class ChibaNorthTests(unittest.TestCase):
    def test_chiba_preserves_explicit_kana_and_joins_address_lines(self):
        p=page('''<table><tr><td rowspan="3">兼務</td><td rowspan="3">カクウジンジャ<br><a href="javascript:openNewWindow( '/ycDB/Board.cgi/001/db/ycDB-pc-jinja_detail.html?search:word=123' , 'detail', 720, 650 );"><b>架空神社</b></a></td><td>祭日</td><td colspan="2">千葉県 仮市<br>一番</td><td>TEL</td></tr></table>''')
        r=north.parse_chiba(p)[0]
        self.assertEqual((r['name'],r['reading_raw'],r['address']),('架空神社','カクウジンジャ','千葉県 仮市 一番'))
        self.assertEqual(r['source_id'],'123')
        self.assertIn('\n',r['address_raw'])

class ToyamaPlaceholderTests(unittest.TestCase):
    def test_toyama_empty_parish_placeholder_is_not_a_facility(self):
        self.assertEqual(north.parse_toyama(page('<table><tr><th>神社名</th><td></td></tr><tr><th>社名カナ</th><td></td></tr><tr><th>鎮座地</th><td></td></tr><tr><th>住所</th><td>仮市地域のみ</td></tr></table>')),[])

class ToyamaMissingNameTests(unittest.TestCase):
    def test_toyama_kana_only_does_not_invent_a_shrine_name(self):
        self.assertEqual(north.parse_toyama(page('<table><tr><th>神社名</th><td></td></tr><tr><th>社名カナ</th><td>クマノジンジャ</td></tr><tr><th>鎮座地</th><td></td></tr></table>')),[])

class SaitamaPublishedReadingTests(unittest.TestCase):
    def test_saitama_published_name_kana_is_used_when_present(self):
        p=page('<h2 class="post-title">架空神社<span class="name_kana">かくうじんじゃ</span></h2><table><caption id="shrine_name">架空神社</caption><tr><th>鎮座地</th><td><span id="shrine_address">仮市一番</span></td></tr></table>')
        self.assertEqual(north.parse_saitama(p)[0]['reading_raw'],'かくうじんじゃ')

class PaginationNorthTests(unittest.TestCase):
    def test_toyama_next_link_without_css_class_is_followed(self):
        r=north.Document('<nav><a href="/ujigami/page/2/?s=x">次へ →</a></nav>').root
        self.assertEqual(north.toyama_next(r,'https://example.org/ujigami/?s=x'),['https://example.org/ujigami/page/2/?s=x'])

    def test_tokyo_tama_region_drills_into_city_links(self):
        r=north.Document('<div><a href="http://example.org/nishitama/ome/">仮市</a><a href="http://example.org/jinja/">神社を探す</a></div>').root
        self.assertEqual(north.tokyo_subareas(r,'http://example.org/nishitama/'),['http://example.org/nishitama/ome/'])

class StableChibaTests(unittest.TestCase):
    def test_chiba_sorts_by_unique_native_id_for_stable_pagination(self):
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        from hashlib import sha256
        library=b'<html>Fictional library reference</html>'
        from njd.http import Client
        from urllib.parse import urlsplit,parse_qs
        def row(sid):
            return f'<table><tr><td rowspan="3">兼務</td><td rowspan="3">カクウジンジャ<br><a href="javascript:openNewWindow(\'/detail?search:word={sid}\')"><b>架空神社</b></a></td><td></td><td>千葉県 仮市{sid}番</td><td></td></tr></table>'
        def transport(url,timeout,agent):
            if url.endswith('/robots.txt'):return 404,{'content-type':'text/plain'},b''
            if url==north.CHIBA_LIBRARY_URL:return 200,{'content-type':'application/pdf'},library
            if url=='https://www.jinjacho.or.jp/':html='<a href="https://www.jinja.ne.jp/exploration/index.html">千葉県の神社</a>'
            elif url.endswith('/exploration/index.html'):html='監修 千葉県神社庁 /ycDB/Board.cgi/001/db/ycDB-pc-jinja_list.html'
            else:
                q=parse_qs(urlsplit(url).query); stable=q.get('view:sort')==['jinja_id']; second=q.get('view:page')==['2']
                sid='2' if stable and second else '1'
                html=row(sid)+'<form name="viewPages"><input type="hidden" name="view:sort" value="'+q.get('view:sort',[''])[0]+'"></form>'
                if not second:html+='<a href="javascript:viewPage( 2 );">次の30件</a>'
            return 200,{'content-type':'text/html; charset=utf-8'},html.encode()
        with TemporaryDirectory() as cache,patch.object(north,'CHIBA_LIBRARY_SHA256',sha256(library).hexdigest()):data=north.collect_chiba(Client(cache,interval=0,transport=transport))
        self.assertEqual([f['native_source_id'] for f in data['facilities']],['1','2'])
        self.assertEqual(data['collection']['authority_status'],'officially_designated_supervised_search')
        self.assertEqual([e['status'] for e in data['entries']],['verified','verified'])

class ToyamaIdentityTests(unittest.TestCase):
    def test_missing_locations_do_not_merge_same_named_parish_records(self):
        from njd.records import build_dataset
        html='<table><tr><th>神社名</th><td>架空神社</td></tr><tr><th>社名カナ</th><td>カクウジンジャ</td></tr><tr><th>鎮座地</th><td></td></tr></table>'
        one=page(html);two=Page('https://example.org/other/',one.status,one.headers,one.body,one.fetched_at)
        data=north.toyama_dataset(north.parse_toyama(one)+north.parse_toyama(two),[one,two])
        self.assertEqual(data['facilities'],[])
        self.assertEqual(len(data['collection']['unresolved_parish_records']),2)
        self.assertEqual([r['source_record_id'] for r in data['collection']['unresolved_parish_records']],['https://example.org/list/','https://example.org/other/'])

class WebShiftJISTests(unittest.TestCase):
    def test_html_shift_jis_accepts_web_windows31j_extension_without_replacement(self):
        p=Page('https://example.org/',200,{'content-type':'text/html'},b'<meta charset="Shift_JIS">'+b'\x87\x71','2026-11-08T00:00:00+00:00')
        self.assertEqual(north.decode(p),'<meta charset="Shift_JIS">㎞')

class IbarakiAddressTests(unittest.TestCase):
    def test_exact_linked_name_adds_address_without_changing_reading_source(self):
        index=page('<table><tr><td></td><td><a href="jinja/123.html">架空神社</a></td><td>かくうじんじゃ</td><td>仮市</td></tr></table>')
        row=north.parse_ibaraki(index)[0]
        detail=Page(row['source_id'],200,index.headers,'<table><tr><td>神社名</td><td>：架空神社</td></tr><tr><td>鎮座地</td><td>：〒000-0000 仮市一番</td></tr></table>'.encode(),index.fetched_at)
        out=north.enrich_ibaraki(row,detail)
        self.assertEqual(out['address'],'仮市一番')
        self.assertEqual(out['url'],'https://example.org/list/')
        self.assertEqual(out['page_hash'],index.sha256)
        self.assertEqual(out['reading_raw'],'かくうじんじゃ')
        self.assertEqual(out['address_source']['page_hash'],detail.sha256)
        self.assertEqual(out['address_source']['link_url'],row['source_id'])

    def test_different_detail_name_keeps_region_name_and_requires_review(self):
        index=page('<table><tr><td></td><td><a href="jinja/123.html">架空神社</a></td><td>かくうじんじゃ</td><td>仮市</td></tr></table>')
        row=north.parse_ibaraki(index)[0]
        detail=Page(row['source_id'],200,index.headers,'<table><tr><td>神社名</td><td>：別表記神社</td></tr><tr><td>鎮座地</td><td>：仮市一番</td></tr></table>'.encode(),index.fetched_at)
        out=north.enrich_ibaraki(row,detail)
        self.assertEqual((out['name'],out['address']),('架空神社','仮市'))
        self.assertTrue(out['review_reason'])
        self.assertEqual(out['address_source']['name_raw'],'別表記神社')


class IbarakiPostalLayoutTests(unittest.TestCase):
    def test_postal_code_line_is_separated_and_original_layout_is_retained(self):
        index=page('<table><tr><td></td><td><a href="jinja/123.html">架空神社</a></td><td>かくうじんじゃ</td><td>仮市</td></tr></table>')
        row=north.parse_ibaraki(index)[0]
        detail=Page(row['source_id'],200,index.headers,'<table><tr><td>神社名</td><td>：架空神社</td></tr><tr><td>鎮座地</td><td>：〒000-0000<br>仮市一番</td></tr></table>'.encode(),index.fetched_at)
        out=north.enrich_ibaraki(row,detail)
        self.assertEqual(out['address'],'仮市一番')
        self.assertEqual(out['address_raw'],'〒000-0000\n仮市一番')
        self.assertEqual(out['address_source']['postal_code_raw'],'〒000-0000')
        self.assertEqual(out['address_source']['published_value_raw'],'〒000-0000\n仮市一番')
        self.assertEqual(out['address_source']['address_raw'],'仮市一番')

class IbarakiWidePostalTests(unittest.TestCase):
    def test_explicit_full_width_postal_hyphen_is_preserved_separately(self):
        index=page('<table><tr><td></td><td><a href="jinja/123.html">架空神社</a></td><td>かくうじんじゃ</td><td>仮市</td></tr></table>')
        row=north.parse_ibaraki(index)[0]
        detail=Page(row['source_id'],200,index.headers,'<table><tr><td>神社名</td><td>：架空神社</td></tr><tr><td>鎮座地</td><td>：〒000－0000<br>仮市一番</td></tr></table>'.encode(),index.fetched_at)
        out=north.enrich_ibaraki(row,detail)
        self.assertEqual(out['address'],'仮市一番')
        self.assertEqual(out['address_source']['postal_code_raw'],'〒000－0000')


class ToyamaResolvedIdentityTests(unittest.TestCase):
    def test_only_exact_nonempty_name_and_shrine_location_merge_parish_pages(self):
        html='<table><tr><th>神社名</th><td>架空神社</td></tr><tr><th>社名カナ</th><td>カクウジンジャ</td></tr><tr><th>住所</th><td>富山市別の氏子区域</td></tr><tr><th>鎮座地</th><td>富山市一番</td></tr></table>'
        one=page(html);two=Page('https://example.org/other/',one.status,one.headers,one.body,one.fetched_at)
        records=north.parse_toyama(one)+north.parse_toyama(two)
        self.assertNotIn('source_id',records[0])
        data=north.toyama_dataset(records,[one,two])
        self.assertEqual(len(data['facilities']),1)
        self.assertEqual(data['facilities'][0]['address'],'富山市一番')
        self.assertEqual(len(data['facilities'][0]['listing_occurrences']),2)
        self.assertEqual(data['collection']['named_parish_source_records'],2)
        self.assertEqual(data['collection']['unresolved_parish_records'],[])

class IbarakiLabelLayoutTests(unittest.TestCase):
    def test_label_layout_whitespace_does_not_hide_published_name_and_location(self):
        index=page('<table><tr><td></td><td><a href="jinja/123.html">架空神社</a></td><td>かくうじんじゃ</td><td>仮市</td></tr></table>')
        row=north.parse_ibaraki(index)[0]
        detail=Page(row['source_id'],200,index.headers,'<table><tr><td>神\n社名</td><td>：架空神社</td></tr><tr><td>鎮\n 座地</td><td>：〒000-0000 仮市一番</td></tr></table>'.encode(),index.fetched_at)
        out=north.enrich_ibaraki(row,detail)
        self.assertEqual(out['address'],'仮市一番')
        self.assertNotIn('review_reason',out)

class ToyamaSpecificLocationTests(unittest.TestCase):
    def test_advisory_and_ambiguous_locations_remain_source_records(self):
        p=page('')
        rows=[north.record(p,'架空神社','カクウジンジャ',address,'test') for address in ('宮司所在地は架空神社','同上','上善名、下善名','富山市上善名・下善名')]
        data=north.toyama_dataset(rows,[p])
        self.assertEqual(data['facilities'],[])
        self.assertEqual(data['collection']['unresolved_parish_record_count'],4)

    def test_public_index_rejects_outside_service_links(self):
        with self.assertRaises(ValueError):
            north.toyama_index_links([{'id':1,'link':'https://other.example/0001/'}], 'https://example.org/ujigami/')

class ToyamaPublicIndexTraversalTests(unittest.TestCase):
    def test_public_collection_pagination_keeps_parish_ids_out_of_facility_identity(self):
        import json
        from tempfile import TemporaryDirectory
        from urllib.parse import urlsplit,parse_qs
        from njd.http import Client
        origin='https://toyama-jinjacho.sakura.ne.jp'
        base=origin+'/ujigami/'
        def transport(url,timeout,user_agent):
            headers={'content-type':'text/html; charset=utf-8'}
            if url.endswith('/robots.txt'):return 200,{'content-type':'text/plain'},b'User-agent: *\nAllow: /'
            if '/wp-json/' in url:
                headers={'content-type':'application/json','x-wp-total':'2','x-wp-totalpages':'2'}
                if url.endswith('/4329'):body={'_links':{'collection':[{'href':base+'wp-json/wp/v2/pages'}]}}
                else:
                    number=int(parse_qs(urlsplit(url).query).get('page',['1'])[0]);body=[{'id':number,'link':base+str(number)+'/'}]
                return 200,headers,json.dumps(body).encode()
            if url==base:html='<link rel="alternate" type="application/json" href="'+base+'wp-json/wp/v2/pages/4329">'
            elif url in (base+'1/',base+'2/'):html='<table><tr><th>神社名</th><td>架空神社</td></tr><tr><th>社名カナ</th><td>カクウジンジャ</td></tr><tr><th>鎮座地</th><td>富山市架空一番</td></tr></table>'
            else:html='<iframe src="'+base+'"></iframe>'
            return 200,headers,html.encode()
        with TemporaryDirectory() as cache:data=north.collect_toyama(Client(cache,interval=0,transport=transport))
        self.assertEqual(len(data['facilities']),1)
        self.assertIsNone(data['facilities'][0]['native_source_id'])
        self.assertEqual(data['collection']['published_pages_observed'],2)
        self.assertEqual(len(data['facilities'][0]['listing_occurrences']),2)

class ToyamaMunicipalityLocationTests(unittest.TestCase):
    def test_city_only_or_unknown_municipality_is_not_a_concrete_location(self):
        for address in ('富山市内','富山市','架空市一番','鎮座地不明','富山市不明'):
            with self.subTest(address=address):self.assertFalse(north.toyama_specific_location(address))

class ChibaConfirmedAuthorityTests(unittest.TestCase):
    def test_confirmed_supervision_keeps_valid_and_invalid_reading_states(self):
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        from hashlib import sha256
        from njd.http import Client
        library=b'<html>Fictional public library reference</html>'
        def transport(url,timeout,agent):
            if url.endswith('/robots.txt'):return 404,{'content-type':'text/plain'},b''
            if url==north.CHIBA_LIBRARY_URL:return 200,{'content-type':'application/pdf'},library
            if url=='https://www.jinjacho.or.jp/':html='<a href="http://www.jinja.ne.jp/exploration/index.html">千葉県の神社</a>'
            elif url.endswith('/exploration/index.html'):html='監修 千葉県神社庁 /ycDB/Board.cgi/001/db/ycDB-pc-jinja_list.html'
            else:
                html=''.join(f'<tr><td rowspan="3">兼務</td><td rowspan="3">{raw}<br><a href="javascript:openNewWindow(\'/detail?search:word={sid}\')">{name}</a></td><td></td><td>千葉県 仮市{sid}番</td><td></td></tr>' for sid,raw,name in [('1','カクウジンジャ','架空神社'),('2','','架空神社'),('3','カクウジンジャ','架空\n神社')])
                html='<table>'+html+'</table><form name="viewPages"></form>'
            return 200,{'content-type':'text/html; charset=utf-8'},html.encode()
        with TemporaryDirectory() as cache,patch.object(north,'CHIBA_LIBRARY_SHA256',sha256(library).hexdigest()):data=north.collect_chiba(Client(cache,interval=0,transport=transport))
        self.assertEqual(data['collection']['authority_status'],'officially_designated_supervised_search')
        self.assertEqual([e['status'] for e in data['entries']],['verified','pending','pending'])
        self.assertEqual(data['entries'][0]['reading'],'かくうじんじゃ')
        self.assertEqual(data['entries'][1]['reason'],'missing agency reading')
        self.assertIn('control or layout characters',data['entries'][2]['reason'])
        self.assertEqual(data['facilities'][2]['name_raw'],'架空\n神社')
        self.assertEqual(len(data['collection']['authority_evidence']),3)
        self.assertEqual(data['collection']['redistribution_status'],'unconfirmed')

    def test_library_document_change_requires_review(self):
        from njd.http import Page
        p=Page('https://www.library.pref.chiba.lg.jp/chibabeginner202411.pdf',200,{'content-type':'application/pdf'},b'changed document','2026-11-09T00:00:00+00:00')
        with self.assertRaises(ValueError):north.chiba_library_evidence(p)
