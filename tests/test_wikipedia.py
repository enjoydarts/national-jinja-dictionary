"""Synthetic full-page fixtures; no network or acquired data mutation."""
import copy
from pathlib import Path
import tempfile
import unittest
from njd.http import Page, FetchError
from njd.storage import write_json, load_dataset
from njd import wikipedia as w

BASE='https://ja.wikipedia.org'
ROOT=BASE+'/wiki/Category:%E5%B3%B6%E6%A0%B9%E7%9C%8C%E3%81%AE%E7%A5%9E%E7%A4%BE'
ARTICLE=BASE+'/wiki/%E5%AE%87%E5%8F%97%E8%B3%80%E5%91%BD%E7%A5%9E%E7%A4%BE'

def article(name='宇受賀命神社',reading='うづかみことじんじゃ',address='島根県隠岐郡海士町宇受賀747'):
    return ('<script>mw.config.set({"wgRevisionId":12345,"wgArticleId":99});</script>'
        '<h1 id="firstHeading">'+name+'</h1><div class="mw-parser-output"><section data-mw-section-id="0">'
        '<table class="infobox"><tr><th colspan="2">'+name+'</th></tr>'
        '<tr><th>所在地</th><td><a>島根県</a>'+address.removeprefix('島根県')+'</td></tr></table>'
        '<p><b>'+name+'</b>（'+reading+'）は神社。</p></section></div>')

def page(url,body):
    return Page(url,200,{'content-type':'text/html; charset=utf-8'},body.encode(),'2026-11-09T00:00:00+00:00')

class FixtureClient:
    def __init__(self,pages):self.pages=pages;self.calls=[]
    def fetch(self,url,**kwargs):
        self.calls.append(url)
        if url not in self.pages:raise FetchError('fixture unavailable: '+url)
        return page(url,self.pages[url])

class WikipediaTests(unittest.TestCase):
    def test_explicit_generated_empty_category_is_a_complete_empty_inventory(self):
        html = '<div class="mw-category-generated"><p><em>現在このカテゴリには、ページまたはメディアがありません。</em></p></div><nav><a href="/wiki/別の神社">別の神社</a></nav>'
        self.assertEqual(w.category_links(page(ROOT, html)), {'categories': [], 'articles': []})
        with self.assertRaises(ValueError):
            w.category_links(page(ROOT, '<p>現在このカテゴリには、ページまたはメディアがありません。</p>'))
    def test_full_rendered_article_preserves_reading_address_and_revision(self):
        ref=w.article_reference(page(ARTICLE,article()),'宇受賀命神社')
        self.assertEqual(ref['reading_raw'],'うづかみことじんじゃ')
        self.assertEqual(ref['address_raw'],'島根県隠岐郡海士町宇受賀747')
        self.assertEqual(ref['revision_id'],12345)
        self.assertIn('所在地',ref['locator'])
        self.assertIn(ref['address_raw'],ref['excerpt'])

    def test_ambiguous_alias_stem_wrong_name_and_multiple_infoboxes_rejected(self):
        for body in [article(reading='うづかみこと'),article(reading='うづかみことじんじゃ、うづか'),
                     article(name='別神社'),article().replace('</p>','（うづかじんじゃ）</p>'),
                     article().replace('</section>','<table class="infobox"></table></section>'),
                     article().replace('"wgRevisionId":12345','"wgRevisionId":0')]:
            with self.subTest(body=body),self.assertRaises(ValueError):w.article_reference(page(ARTICLE,body),'宇受賀命神社')

    def test_non_target_place_and_old_name_readings_do_not_invalidate_primary_name(self):
        base=article(name='例神社',reading='れいじんじゃ')
        for extra in ['所在地の秘密尾（ひみつお）にある。','旧称は別神社（べつじんじゃ）。','通称「別宮」（べつみや）とも呼ばれる。']:
            with self.subTest(extra=extra):
                ref=w.article_reference(page(ARTICLE,base.replace('は神社。','は神社。'+extra)),'例神社')
                self.assertEqual(ref['reading_raw'],'れいじんじゃ')
        for extra in ['（べつじんじゃ）','別の例神社（べつじんじゃ）とも記載。']:
            with self.subTest(extra=extra),self.assertRaises(ValueError):
                w.article_reference(page(ARTICLE,base.replace('は神社。','は神社。'+extra)),'例神社')

    def test_address_separates_coordinate_markup_and_preserves_cell_observation(self):
        address='島根県隠岐郡海士町宇受賀747'
        coordinates='<span class="plainlinks nourlexpansion"><a href="https://geohack.toolforge.org/geohack.php?params=34_N_135_E"><span class="geo-dms">北緯34度 東経135度</span><span class="geo">34;135</span></a></span>'
        body=article().replace(address.removeprefix('島根県')+'</td>',address.removeprefix('島根県')+coordinates+'</td>')
        ref=w.article_reference(page(ARTICLE,body),'宇受賀命神社')
        self.assertEqual(ref['address_raw'],address)
        self.assertIn('北緯34度',ref['address_cell_raw'])
        self.assertEqual(ref['address_extraction'],'literal address text; coordinate-link subtree excluded')
        self.assertIn(address,ref['excerpt'])

    def test_explicit_coordinate_index_is_not_a_second_facility_infobox(self):
        mapbox='<table id="GeoGroup" class="mw-collapsible noprint infobox"><tr><th>全ての座標を示した地図 - OSM</th><td>表示</td></tr></table>'
        body=article().replace('</section>',mapbox+'</section>')
        self.assertEqual(w.article_reference(page(ARTICLE,body),'宇受賀命神社')['reading_raw'],'うづかみことじんじゃ')
        for fake in [mapbox.replace('GeoGroup','Other'),mapbox.replace('全ての座標を示した地図 - OSM','別施設'),mapbox.replace('noprint','unknown')]:
            with self.subTest(fake=fake),self.assertRaises(ValueError):
                w.article_reference(page(ARTICLE,article().replace('</section>',fake+'</section>')),'宇受賀命神社')

    def test_primary_infobox_does_not_absorb_a_museum_or_festival_in_a_later_section(self):
        other='<section data-mw-section-id="1"><table class="infobox"><tr><th>資料館</th></tr><tr><th>所在地</th><td>別住所</td></tr></table></section>'
        body=article().replace('</div>',other+'</div>')
        ref=w.article_reference(page(ARTICLE,body),'宇受賀命神社')
        self.assertEqual(ref['address_raw'],'島根県隠岐郡海士町宇受賀747')
        ambiguous=article().replace('</section>',other+'</section>')
        with self.assertRaises(ValueError):w.article_reference(page(ARTICLE,ambiguous),'宇受賀命神社')

    def test_primary_reading_followed_by_explicit_kanji_notation_preserves_primary_only(self):
        for suffix in ['、別神社','、旧字表記：別神社','、正式名称：別神社','、別神社とも']:
            body=article().replace('うづかみことじんじゃ）','うづかみことじんじゃ'+suffix+'）')
            with self.subTest(suffix=suffix):
                ref=w.article_reference(page(ARTICLE,body),'宇受賀命神社')
                self.assertEqual(ref['reading_raw'],'うづかみことじんじゃ')
                self.assertEqual(ref['name_raw'],'宇受賀命神社')
        for suffix in ['、べつじんじゃ','、別神社（べつじんじゃ）','、別神社、べつじんじゃ']:
            with self.subTest(suffix=suffix),self.assertRaises(ValueError):
                w.article_reference(page(ARTICLE,article().replace('うづかみことじんじゃ）','うづかみことじんじゃ'+suffix+'）')),'宇受賀命神社')

    def test_one_address_line_wrap_is_distinct_from_multiple_locations(self):
        base=article()
        for raw,expected in [('〒684-0403<br>島根県隠岐郡海士町宇受賀747','〒684-0403 島根県隠岐郡海士町宇受賀747'),
                             ('島根県隠岐郡<br>海士町宇受賀747','島根県隠岐郡海士町宇受賀747')]:
            body=base.replace('<a>島根県</a>隠岐郡海士町宇受賀747',raw)
            with self.subTest(raw=raw):
                ref=w.article_reference(page(ARTICLE,body),'宇受賀命神社')
                self.assertEqual(ref['address_raw'],expected)
                self.assertEqual(ref['address_lines_raw'],raw.split('<br>'))
                self.assertIn('line wrap',ref['address_layout_normalization'])
        for raw in ['島根県例市1<br>島根県別市2','島根県隠岐郡<br>別県海士町1',
                    '〒684-0403<br>島根県隠岐郡<br>海士町1','【現社地】島根県例市1<br>【元宮】島根県例市2']:
            body=base.replace('<a>島根県</a>隠岐郡海士町宇受賀747',raw)
            with self.subTest(raw=raw),self.assertRaises(ValueError):w.article_reference(page(ARTICLE,body),'宇受賀命神社')

    def test_literal_reading_may_cross_the_written_shrine_suffix_boundary(self):
        for name,reading in [('例大神社','れいおおみわしゃ'),('例神宮','れいぜんぐう')]:
            with self.subTest(name=name):
                ref=w.article_reference(page(ARTICLE,article(name=name,reading=reading)),name)
                self.assertEqual(ref['reading_raw'],reading)
        for name,reading in [('例大神社','れいおおみわ'),('例神宮','れいぜん')]:
            with self.subTest(name=name),self.assertRaises(ValueError):w.article_reference(page(ARTICLE,article(name=name,reading=reading)),name)

    def test_category_reads_only_content_regions_and_actual_pagination(self):
        body='<a href="/wiki/Outside">outside</a><div id="mw-subcategories"><a href="/wiki/Category:島根県の旧郷社">sub</a></div><div id="mw-pages"><a href="/wiki/宇受賀命神社">宇受賀命神社</a><a href="https://evil.test/wiki/Other">bad</a><a href="/wiki/特別:検索">special</a><a href="/w/index.php?title=Category:島根県の神社&amp;pagefrom=宇">next</a></div>'
        result=w.category_links(page(ROOT,body))
        self.assertEqual(result['articles'],[ARTICLE])
        self.assertEqual(len(result['categories']),2)
        self.assertTrue(any('pagefrom=' in u for u in result['categories']))
        with self.assertRaises(ValueError):w.category_links(page(ROOT,'<p>blocked or unexpected page</p>'))

    def setup_data(self,root):
        f=dict(id='f1',name_raw='宇受賀命神社',listed_name='宇受賀命神社',address='隠岐郡海士町宇受賀747',municipality='隠岐郡海士町',prefecture='島根県',prefecture_code='32',listing_url='https://agency.example/list',status='verified',source_key='shimane')
        e=dict(id='e1',facility_id='f1',surface='宇受賀命神社',reading_raw='',reading='',source_hash='abc',status='pending',reason='missing agency reading')
        data=dict(facilities=[f],entries=[e],collection=dict(source_key='shimane',prefecture_code='32',authority_status='confirmed'))
        write_json(root/'sources/shimane.json',data)
        return data

    def test_inventory_then_resume_proposal_without_touching_canonical(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);data_dir=root/'data';self.setup_data(data_dir);state=root/'state'
            body='<div id="mw-pages"><a href="/wiki/宇受賀命神社">宇受賀命神社</a></div>'
            client=FixtureClient({ROOT:body,ARTICLE:article()})
            result=w.research(data_dir,state,['32'],client,inventory_only=True)
            self.assertEqual(result['remaining_articles'],1)
            self.assertFalse(result['complete'])
            result=w.research(data_dir,state,['32'],client,limit=1)
            proposals=load_dataset(state/'proposals.json')['entries']
            self.assertEqual(proposals['e1']['changes'],{'reading':'うづかみことじんじゃ'})
            self.assertTrue(result['complete'])
            self.assertFalse((data_dir/'corrections.json').exists())
            count=len(client.calls);w.research(data_dir,state,['32'],client)
            self.assertEqual(len(client.calls),count)

    def test_category_failure_is_auditable_not_complete_and_retried(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.setup_data(root/'data');client=FixtureClient({})
            result=w.research(root/'data',root/'state',['32'],client)
            self.assertFalse(result['complete']);self.assertEqual(len(result['category_errors']),1)
            client.pages[ROOT]='<div id="mw-pages"></div>'
            self.assertTrue(w.research(root/'data',root/'state',['32'],client)['complete'])

    def test_existing_judgments_identity_and_agency_readings_excluded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);data=self.setup_data(root/'data')
            for change in ['correction','review','decision','identity','reading']:
                trial=copy.deepcopy(data)
                if change=='identity':trial['entries'][0]['identity_review_required']=True
                if change=='reading':trial['entries'][0]['reading_raw']='うづかみことじんじゃ'
                write_json(root/'data/sources/shimane.json',trial)
                for name in ['corrections','reviews','decisions']:
                    p=root/'data'/(name+'.json')
                    if p.exists():p.unlink()
                if change in ['correction','review','decision']:
                    name={'correction':'corrections','review':'reviews','decision':'decisions'}[change]
                    write_json(root/'data'/(name+'.json'),{'entries':{'e1':{}}} if name!='decisions' else {'e1':{}})
                self.assertEqual(w.pending_targets(root/'data',['32']),[])

    def test_rejects_state_and_cache_inside_repository(self):
        repository=Path(w.__file__).resolve().parents[1]
        with self.assertRaises(ValueError):w.external_directory(repository/'tmp-state')

    def test_address_mismatch_is_pending_and_never_proposed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.setup_data(root/'data')
            client=FixtureClient({ROOT:'<div id="mw-pages"><a href="/wiki/宇受賀命神社">one</a></div>',ARTICLE:article(address='島根県隠岐郡海士町宇受賀748')})
            result=w.research(root/'data',root/'state',['32'],client)
            self.assertEqual(result['proposals'],0)
            saved=load_dataset(root/'state/state/progress.json')['prefectures']['32']['articles'][ARTICLE]
            self.assertIn('e1',saved['pending'])

    def test_subcategory_pagination_and_article_limit_checkpoint_remaining(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);data=self.setup_data(root/'data')
            f=copy.deepcopy(data['facilities'][0]);f.update(id='f2',name_raw='別神社',listed_name='別神社',address='隠岐郡海士町宇受賀748')
            e=copy.deepcopy(data['entries'][0]);e.update(id='e2',facility_id='f2',surface='別神社')
            data['facilities'].append(f);data['entries'].append(e);write_json(root/'data/sources/shimane.json',data)
            child=w.wiki_url('Category:島根県の旧郷社');other=w.wiki_url('別神社 (海士町)')
            nextpage=BASE+'/w/index.php?title=Category:島根県の神社&pagefrom=z'
            client=FixtureClient({ROOT:'<div id="mw-subcategories"><a href="'+child+'">child</a></div><div id="mw-pages"><a href="'+nextpage.replace('&','&amp;')+'">next</a></div>',child:'<div id="mw-pages"><a href="'+ARTICLE+'">one</a></div>',nextpage:'<div id="mw-pages"><a href="'+other+'">two</a></div>',ARTICLE:article(),other:article('別神社','べつじんじゃ','島根県隠岐郡海士町宇受賀748')})
            result=w.research(root/'data',root/'state',['32'],client,limit=1)
            self.assertEqual(result['remaining_articles'],1);self.assertFalse(result['complete'])
            result=w.research(root/'data',root/'state',['32'],client,limit=1)
            self.assertTrue(result['complete']);self.assertEqual(result['proposals'],2)
            self.assertEqual(load_dataset(root/'state/proposals.json')['entries']['e2']['references'][0]['name_raw'],'別神社')

    def test_refresh_invalidates_old_proposal_and_unrequested_scope_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.setup_data(root/'data')
            client=FixtureClient({ROOT:'<div id="mw-pages"><a href="'+ARTICLE+'">one</a></div>',ARTICLE:article()})
            w.research(root/'data',root/'state',['32'],client)
            hokkaido=w.wiki_url('Category:北海道の神社');client.pages[hokkaido]='<div id="mw-pages"></div>'
            w.research(root/'data',root/'state',['01'],client)
            self.assertIn('e1',load_dataset(root/'state/proposals.json')['entries'])
            client.pages[ARTICLE]=article(address='違う住所')
            w.research(root/'data',root/'state',['32'],client,refresh=True)
            self.assertNotIn('e1',load_dataset(root/'state/proposals.json')['entries'])

    def test_category_input_must_remain_same_host_category(self):
        for url in ['https://evil.test/wiki/Category:島根県の神社',BASE+'/wiki/普通の記事']:
            with self.subTest(url=url),self.assertRaises(ValueError):w.category_links(page(url,'<div id="mw-pages"></div>'))

    def test_conflicting_full_readings_across_candidate_articles_are_quarantined(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.setup_data(root/'data');second=w.wiki_url('宇受賀命神社 (海士町)')
            body='<div id="mw-pages"><a href="'+ARTICLE+'">one</a><a href="'+second+'">two</a></div>'
            client=FixtureClient({ROOT:body,ARTICLE:article(),second:article(reading='うずかみことじんじゃ')})
            result=w.research(root/'data',root/'state',['32'],client)
            self.assertEqual(result['proposals'],0)
            scope=load_dataset(root/'state/state/progress.json')['prefectures']['32']
            self.assertEqual(scope['conflicting_reading_entry_ids'],['e1'])

    def test_failed_candidate_withholds_sibling_proposal_and_resume_retries_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.setup_data(root/'data');second=w.wiki_url('宇受賀命神社 (海士町)')
            client=FixtureClient({ROOT:'<div id="mw-pages"><a href="'+ARTICLE+'">one</a><a href="'+second+'">two</a></div>',ARTICLE:article()})
            result=w.research(root/'data',root/'state',['32'],client)
            self.assertFalse(result['complete']);self.assertEqual(result['remaining_articles'],1)
            self.assertEqual(result['proposals'],0)
            client.calls.clear();client.pages[second]=article(reading='うずかみことじんじゃ')
            result=w.research(root/'data',root/'state',['32'],client)
            self.assertTrue(result['complete']);self.assertEqual(result['proposals'],0)
            self.assertEqual(client.calls,[second])
            scope=load_dataset(root/'state/state/progress.json')['prefectures']['32']
            self.assertEqual(scope['conflicting_reading_entry_ids'],['e1'])

    def test_recheck_reparses_saved_pending_article_without_http_refresh(self):
        class CacheClient(FixtureClient):
            def fetch(self,url,**kwargs):
                if kwargs.get('refresh'):raise FetchError('forced network forbidden in cache-only test')
                return super().fetch(url,**kwargs)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.setup_data(root/'data')
            client=CacheClient({ROOT:'<div id="mw-pages"><a href="'+ARTICLE+'">one</a></div>',ARTICLE:article()})
            w.research(root/'data',root/'state',['32'],client)
            path=root/'state/state/progress.json';state=load_dataset(path)
            saved=state['prefectures']['32']['articles'][ARTICLE]
            saved['proposals']={};saved['pending']={'e1':'previous parser rejected this structure'};write_json(path,state)
            self.assertEqual(w.research(root/'data',root/'state',['32'],client)['proposals'],0)
            client.calls.clear()
            self.assertEqual(w.research(root/'data',root/'state',['32'],client,recheck=True)['proposals'],1)
            self.assertEqual(client.calls,[ARTICLE])

    def test_explicit_full_shrine_suffix_variants_accepted_but_stem_not(self):
        for raw in ['うづかみことじんしゃ','うづかみことしんじゃ','うづかみことしんしゃ']:
            with self.subTest(raw=raw):self.assertEqual(w.article_reference(page(ARTICLE,article(reading=raw)),'宇受賀命神社')['reading_raw'],raw)
        with self.assertRaises(ValueError):w.article_reference(page(ARTICLE,article(reading='うづかみこと')),'宇受賀命神社')
