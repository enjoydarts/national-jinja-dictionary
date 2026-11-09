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
    def test_kochi_follows_published_next_link_and_checks_native_total(self):
        import json
        def page(native,next_link='',blank=False,total=2):
            html=f'<div class="wixui-repeater__item" id="comp-ljqf2796__{native}"><div id="comp-ljqf2799__{native}" class="wixui-rich-text">試験神社</div><div id="comp-ljqf279d__{native}" class="wixui-rich-text">甲1</div><div id="comp-ljqlom9b__{native}" class="wixui-rich-text">高知県試験市</div></div>'
            warm={'appsWarmupData':{'dataBinding':{'dataStore':{'recordInfosByDatasetId':{'comp-ljqfjyd6':{'datasetSize':{'total':total}}}}}}}
            warm['appsWarmupData']['dataBinding']['dataStore']['recordsByCollectionId']={'4gq343hu3awdp28flsx':{native:{'_id':native,'text':'試験神社','text1':'甲1','newField':'高知県試験市'}}}
            if blank:warm['appsWarmupData']['dataBinding']['dataStore']['recordsByCollectionId']['4gq343hu3awdp28flsx'][native]={'_id':native}
            return self.page(html+f'<link rel="next" href="{next_link}">'*(bool(next_link))+'<script id="wix-warmup-data">'+json.dumps(warm)+'</script>')
        pages=[page('one','?comp-ljqfjyd6_page=2'),page('two')]
        class Client:
            def __init__(self):self.urls=[]
            def fetch(self,url):
                from dataclasses import replace
                self.urls.append(url);return replace(pages[len(self.urls)-1],url=url)
        client=Client();data=south.collect_kochi(client)
        self.assertEqual(len(data['facilities']),2)
        self.assertTrue(data['collection']['traversal_complete'])
        self.assertEqual(data['collection']['source_rows_observed'],2)
        self.assertIn('comp-ljqfjyd6_page=2',client.urls[1])
        # Repeated native rows must not silently count as complete coverage.
        pages[1]=page('one')
        partial=south.collect_kochi(Client())
        self.assertFalse(partial['collection']['traversal_complete'])
        self.assertIn('duplicate native',partial['collection']['failed_pages'][0]['reason'])
        pages[1]=self.page('<script id="wix-warmup-data">{}</script>')
        partial=south.collect_kochi(Client())
        self.assertEqual(len(partial['facilities']),1)
        self.assertFalse(partial['collection']['traversal_complete'])
        self.assertEqual(partial['collection']['published_page_bound'],2)
        pages[1]=page('two',blank=True)
        with_blank=south.collect_kochi(Client())
        self.assertEqual(len(with_blank['facilities']),1)
        self.assertEqual(with_blank['collection']['source_rows_observed'],2)
        self.assertEqual(len(with_blank['collection']['unresolved_source_records']),1)
        self.assertTrue(with_blank['collection']['traversal_complete'])
        # A reviewed empty-body exception is specific to both URL and hash.
        from unittest.mock import patch
        from dataclasses import replace
        base=client.urls[0];second=base+'?comp-ljqfjyd6_page=2';third=base+'?comp-ljqfjyd6_page=3'
        pages[:]=[page('one','?comp-ljqfjyd6_page=2',total=3),self.page('<script id="wix-warmup-data">{}</script>'),page('three',total=3)]
        review={second:dict(sha256=pages[1].sha256,next_url=third,discovery='reviewed public pagination recovery')}
        with patch.object(south,'KOCHI_REVIEWED_PAGINATION_RECOVERY',review):
            recovered=south.collect_kochi(Client())
            self.assertEqual(len(recovered['facilities']),2)
            self.assertFalse(recovered['collection']['traversal_complete'])
            self.assertEqual(recovered['collection']['failed_pages'][0]['url'],second)
            pages[1]=replace(pages[1],status=403)
            denied=south.collect_kochi(Client())
            self.assertEqual(len(denied['facilities']),1)
            pages[1]=self.page('<script id="wix-warmup-data">{"changed":true}</script>')
            changed=south.collect_kochi(Client())
            self.assertEqual(len(changed['facilities']),1)
    def test_kochi_uses_explicit_cms_original_over_corrupted_rendered_text(self):
        import json
        html='<div class="wixui-repeater__item" id="comp-ljqf2796__native"><div id="comp-ljqf2799__native" class="wixui-rich-text">試験神社</div><div id="comp-ljqf279d__native" class="wixui-rich-text">甲1</div><div id="comp-ljqlom9b__native" class="wixui-rich-text">高知\x00県試験市</div></div>'
        store={'recordsByCollectionId':{'4gq343hu3awdp28flsx':{'native':{'_id':'native','text':'試験神社','text1':'甲1','newField':'高知県試験市'}}}}
        html+='<script id="wix-warmup-data">'+json.dumps({'appsWarmupData':{'dataBinding':{'dataStore':store}}})+'</script>'
        row=south.parse_kochi(self.page(html))[0]
        self.assertEqual(row['address'],'高知県試験市甲1')
        self.assertIn('wix-warmup-data',row['locator'])
        store['recordsByCollectionId']['4gq343hu3awdp28flsx']['native'].pop('newField')
        store['recordsByCollectionId']['4gq343hu3awdp28flsx']['native']['text1']='試験郡試験町甲1'
        html=html[:html.index('<script')]+'<script id="wix-warmup-data">'+json.dumps({'appsWarmupData':{'dataBinding':{'dataStore':store}}})+'</script>'
        row=south.parse_kochi(self.page(html))[0]
        self.assertEqual(row['address'],'試験郡試験町甲1')
        self.assertEqual(row['address_context'],'')
        store['recordsByCollectionId']['4gq343hu3awdp28flsx']['native']={'_id':'native'}
        html=html[:html.index('<script')]+'<script id="wix-warmup-data">'+json.dumps({'appsWarmupData':{'dataBinding':{'dataStore':store}}})+'</script>'
        row=south.parse_kochi(self.page(html))[0]
        self.assertEqual((row['name'],row['address']),('',''))
    def test_kochi_first_page_failure_raises_and_preserves_previous_source(self):
        from njd.http import FetchError
        from njd.nationwide import run_collections,save_collection,source_path
        from njd.records import build_dataset
        from unittest.mock import patch
        from tempfile import TemporaryDirectory
        from pathlib import Path
        class DeniedClient:
            def __init__(self,*args,**kwargs):pass
            def fetch(self,url):raise FetchError('HTTP 403: '+url)
        with self.assertRaises(FetchError):south.collect_kochi(DeniedClient())
        malformed=self.page('<script id="wix-warmup-data">{}</script>')
        class ChangedClient:
            def fetch(self,url):return malformed
        with self.assertRaises((KeyError,ValueError)):south.collect_kochi(ChangedClient())
        with TemporaryDirectory() as tmp:
            root=Path(tmp);data=root/'data'
            previous=build_dataset('kochi','39','高知県','高知県神社庁',[south.record(self.page('original'),'試験神社','しけんじんじゃ','高知県試験市甲1','original',source_id='prior')])
            save_collection(data,'kochi',previous);path=source_path(data,'kochi');before=path.read_bytes()
            with patch('njd.nationwide.Client',DeniedClient):
                run_collections(data,{'kochi':south.REGISTRY['kochi']},['kochi'],cache_dir=root/'cache')
            self.assertEqual(path.read_bytes(),before)
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
