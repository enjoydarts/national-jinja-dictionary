"""Synthetic bounded map/profile evidence; no acquired prose or images."""
import copy
from pathlib import Path
import tempfile
import unittest
from njd.http import Page, FetchError
try:
    from njd.adapters import hyogo as h
except ImportError:
    h=None

BASE='https://www.hyogo-jinjacho.com/'
QUERY=BASE+'data/xml.php?ne_lat=36&sw_lat=34&ne_lng=136&sw_lng=134'
CODE='6301046';URL=BASE+'data/'+CODE+'.html';ADDR='神戸市中央区多聞通3-1-1'
def page(url,text,status=200,headers=None):
    return Page(url,status,headers or {'content-type':'text/html; charset=utf-8'},text.encode(),'2026-11-09T00:00:00+00:00')
def xml(rows=None):
    if rows is None:rows=[(CODE,'湊川神社',ADDR)]
    return '<Locations>'+''.join(f'<Locate><code>{code}</code><name>{name}</name><place>{addr}</place><lat>34.681991</lat><lng>135.175146</lng></Locate>' for code,name,addr in rows)+'</Locations>'
def detail(name='湊川神社',kana='ミナトガワジンジャ',code=CODE,address=ADDR):
    return f'<header class="hero"><div class="hero-head"><div class="kana">{kana}</div><div class="title-row"><h1>{name}</h1><div class="code">神社コード<strong>{code}/本務</strong></div></div></div><div class="hero-grid"><img src="photo.jpg"><dl><div class="row"><dt>所在地</dt><dd>〒650-0015\n{address}</dd></div><div class="row"><dt>通称名</dt><dd>ALIAS SECRET</dd></div></dl></div></header><section>ARTICLE SECRET</section>'
class Client:
    def __init__(self,pages):self.pages=pages;self.calls=[]
    def fetch(self,url):
        self.calls.append(url)
        if url not in self.pages:raise FetchError('connection failure')
        p=self.pages[url];return p if isinstance(p,Page) else page(url,p)
class HyogoTests(unittest.TestCase):
    def setUp(self):self.assertIsNotNone(h,'Hyogo adapter must exist')
    def collect(self,**kw):return h.collect_hyogo(Client({QUERY:xml(),URL:detail(**kw)}))
    def test_xml_explicit_records_and_bound_detail_url(self):
        rows=h.parse_xml(page(QUERY,xml()));self.assertEqual(len(rows),1)
        self.assertEqual((rows[0]['source_id'],rows[0]['name'],rows[0]['address'],rows[0]['url']),(CODE,'湊川神社',ADDR,URL))
        self.assertEqual(rows[0]['xml_source']['page_hash'],page(QUERY,xml()).sha256)
    def test_profile_literal_fields_and_fact_only_evidence(self):
        p=page(URL,detail());r=h.parse_detail(p,h.parse_xml(page(QUERY,xml()))[0])
        self.assertEqual((r['name'],r['reading_raw'],r['address']),('湊川神社','ミナトガワジンジャ',ADDR))
        self.assertEqual(r['reading_display_raw'],'ミナトガワジンジャ');self.assertTrue(r['address_raw'].startswith('〒650-0015'))
        self.assertNotIn('SECRET',r['evidence']);self.assertNotIn('photo.jpg',str(r))
    def test_verified_rows_counts_and_scope_are_separate(self):
        d=self.collect();self.assertEqual(d['entries'][0]['reading'],'みなとがわじんじゃ')
        self.assertEqual(d['collection']['xml_records_observed'],1);self.assertEqual(d['collection']['xml_unique_codes'],1)
        self.assertTrue(d['collection']['traversal_complete']);self.assertFalse(d['collection']['collection_complete'])
        self.assertFalse(d['collection']['api_cap_confirmed']);self.assertFalse(d['collection']['ui_viewport_observed'])
        self.assertEqual(d['facilities'][0]['xml_occurrences'][0]['name_raw'],'湊川神社')
    def test_suffix_only_partial_missing_or_annotated_readings_are_pending(self):
        for kana in ['', 'ミナトガワ','ジンジャ','シャ','ミナトガワジンジャ（通称）','ミナトガワ ジンジャ']:
            d=self.collect(kana=kana);self.assertEqual(d['entries'][0]['status'],'pending');self.assertEqual(d['entries'][0]['reading'],'')
        self.assertEqual(h._reading_reason('神社','ジンジャ'),'')
    def test_annotated_names_remain_pending(self):
        self.assertEqual(self.collect(name='湊川神社（旧称）')['entries'][0]['status'],'pending')
    def test_map_detail_name_address_or_printed_code_disagreement_is_pending(self):
        for kw in [dict(name='別神社'),dict(address=ADDR+'9'),dict(code='6301048')]:
            with self.subTest(kw=kw):
                d=self.collect(**kw);self.assertEqual(d['facilities'][0]['status'],'pending');self.assertEqual(d['entries'][0]['status'],'pending')
    def test_documented_city_rename_compares_only_without_changing_raw_fields(self):
        old='篠山市今田町本荘1-2';new='丹波篠山市今田町本荘1-2'
        refs=h.parse_xml(page(QUERY,xml([(CODE,'湊川神社',old)])));before=copy.deepcopy(refs[0])
        row=h.parse_detail(page(URL,detail(address=new)),refs[0])
        self.assertFalse(row.get('review_reason'))
        self.assertEqual(refs[0],before)
        d=h.collect_hyogo(Client({QUERY:xml([(CODE,'湊川神社',old)]),URL:detail(address=new)}))
        f=d['facilities'][0];e=d['entries'][0]
        self.assertEqual((f['status'],e['status'],e['reading']),('verified','verified','みなとがわじんじゃ'))
        self.assertEqual(f['address'],new);self.assertEqual(f['map_address_raw'],old)
        self.assertEqual(f['xml_occurrences'][0]['address_raw'],old)
        self.assertEqual(f['address_raw'],'〒650-0015\n'+new)
        comparison=f['address_comparisons'][0]
        self.assertEqual((comparison['old_prefix'],comparison['new_prefix'],comparison['effective_date']),('篠山市','丹波篠山市','2019-05-01'))
        self.assertEqual((comparison['xml_address_raw'],comparison['profile_address_compared'],comparison['unchanged_suffix_raw']),(old,new,'今田町本荘1-2'))
        self.assertEqual(comparison['profile_address_raw'],'〒650-0015\n'+new)
        ref=comparison['ordinance_reference']
        self.assertEqual(ref['url'],'https://www.city.tambasasayama.lg.jp/section/reiki_int/reiki_honbun/j700RG00001635.html')
        self.assertEqual(ref['page_hash'],'0a2df8df9c6102f1ef5f1fddbd8e5b723835417ad56e379250736ae3776080be')
        self.assertEqual(ref['checked_at'][:10],'2026-11-09')
        self.assertIn('篠山市の名称を丹波篠山市に変更する。',ref['excerpt'])
        ordinary=h.collect_hyogo(Client({QUERY:xml([(CODE,'湊川神社',new)]),URL:detail(address=new)}))
        self.assertEqual(f['source_hash'],ordinary['facilities'][0]['source_hash'])
        self.assertNotIn('address_comparisons',ordinary['facilities'][0])
        from njd.validation import validate
        self.assertFalse([p for p in validate(d) if p.get('severity')=='error'])

    def test_city_rename_requires_literal_name_even_when_glyph_pattern_matches(self):
        old='篠山市今田町本荘1-2';new='丹波篠山市今田町本荘1-2'
        d=h.collect_hyogo(Client({QUERY:xml([(CODE,'湊川神社',old)]),
            URL:detail(name='湊<img src="glyph.gif" alt="" />神社',address=new)}))
        f=d['facilities'][0]
        self.assertEqual(f['status'],'pending');self.assertEqual(d['entries'][0]['status'],'pending')
        self.assertEqual(f['name_rendering_status'],'external_glyph')
        self.assertNotIn('address_comparisons',f)
        self.assertEqual(f['map_address_raw'],old);self.assertEqual(f['address'],new)
        self.assertIn('addresses differ',f['review_reason'])

    def test_city_rename_never_uses_two_empty_names_as_confirmation(self):
        old='篠山市今田町本荘1-2';new='丹波篠山市今田町本荘1-2'
        d=h.collect_hyogo(Client({QUERY:xml([(CODE,'',old)]),URL:detail(name='',address=new)}))
        self.assertEqual(d['facilities'][0]['status'],'pending')
        self.assertNotIn('address_comparisons',d['facilities'][0])

    def test_city_rename_does_not_clear_other_identity_or_address_differences(self):
        suffix='今田町本荘1-2'
        cases=[('篠山市'+suffix,'丹波市'+suffix,{}),
               ('篠山市'+suffix,'丹波丹波篠山市'+suffix,{}),
               ('篠山市'+suffix,'丹波篠山市今田町本荘1-3',{}),
               ('篠山市'+suffix,'丹波篠山市今田町別町1-2',{}),
               ('篠山市','丹波篠山市',{}),
               ('篠山市  ','丹波篠山市  ',{}),
               ('丹波篠山市'+suffix,'篠山市'+suffix,{}),
               ('兵庫県篠山市'+suffix,'兵庫県丹波篠山市'+suffix,{}),
               ('篠山市'+suffix,'丹波篠山市'+suffix,{'name':'別神社'}),
               ('篠山市'+suffix,'丹波篠山市'+suffix,{'code':'6301048'})]
        for old,new,kwargs in cases:
            with self.subTest(old=old,new=new,kwargs=kwargs):
                d=h.collect_hyogo(Client({QUERY:xml([(CODE,'湊川神社',old)]),URL:detail(address=new,**kwargs)}))
                self.assertEqual(d['facilities'][0]['status'],'pending')
                self.assertEqual(d['entries'][0]['status'],'pending')
                self.assertNotIn('address_comparisons',d['facilities'][0])
                self.assertEqual(d['facilities'][0]['map_address_raw'],old)

    def test_glyph_raw_tag_position_whitespace_and_source_hash(self):
        tag="<IMG  SRC='glyph/a.gif'\n ALT='two  words' />";hashes=[]
        for actual in [tag,tag.replace('a.gif','b.gif'),tag.replace('two  words','two words')]:
            d=self.collect(name='湊'+actual+'神社');f=d['facilities'][0];e=d['entries'][0]
            self.assertEqual(f['name_raw'],'湊'+actual+'神社');self.assertEqual(f['name_rendering_status'],'external_glyph')
            self.assertEqual(e['reading'],'');self.assertEqual(e['status'],'pending');hashes.append(f['source_hash'])
            from njd.validation import eligible
            self.assertEqual(eligible(d),[])
        self.assertEqual(len(set(hashes)),3)
    def test_bound_glyph_correction_resolves_only_rendering_defect(self):
        from test_corrections import correction
        from njd.corrections import apply_corrections
        from njd.validation import eligible
        raw='湊<img src="glyph.gif" alt="" />神社'
        d=self.collect(name=raw)
        c=correction(d,dict(surface='湊川神社',reading='みなとがわじんじゃ'))
        out=apply_corrections(d,c)
        self.assertEqual(len(eligible(out)),1)
        self.assertEqual(out['facilities'][0]['name_raw'],raw)
        self.assertEqual(out['facilities'][0]['xml_occurrences'][0]['name_raw'],'湊川神社')
        self.assertEqual(out['entries'][0]['surface'],'湊川神社')

    def test_glyph_correction_cannot_clear_actual_identity_disagreement(self):
        from test_corrections import correction
        from njd.corrections import apply_corrections
        from njd.validation import eligible
        for kw in [dict(code='6301048'),dict(address=ADDR+'9'),dict(name='別<img src="glyph.gif" />神社')]:
            args=dict(name='湊<img src="glyph.gif" />神社');args.update(kw)
            d=self.collect(**args)
            c=correction(d,dict(surface='湊川神社',reading='みなとがわじんじゃ'))
            self.assertEqual(eligible(apply_corrections(d,c)),[])

    def test_same_name_different_codes_stay_separate(self):
        other='6301048';other_url=BASE+'data/'+other+'.html';second_addr=ADDR+'9'
        d=h.collect_hyogo(Client({QUERY:xml([(CODE,'湊川神社',ADDR),(other,'湊川神社',second_addr)]),URL:detail(),other_url:detail(code=other,address=second_addr)}))
        self.assertEqual(len(d['facilities']),2);self.assertNotEqual(d['facilities'][0]['id'],d['facilities'][1]['id'])
    def test_duplicate_native_codes_conflicting_map_rows_are_pending(self):
        c=Client({QUERY:xml([(CODE,'湊川神社',ADDR),(CODE,'別神社',ADDR)]),URL:detail()});d=h.collect_hyogo(c)
        self.assertEqual(c.calls.count(URL),1);self.assertEqual(len(d['facilities']),1);self.assertEqual(d['entries'][0]['status'],'pending')
        self.assertEqual(len(d['facilities'][0]['xml_occurrences']),2)
    def test_limit_is_detail_upper_bound_and_remaining_is_explicit(self):
        other='6301048';other_url=BASE+'data/'+other+'.html'
        c=Client({QUERY:xml([(CODE,'湊川神社',ADDR),(other,'湊川神社',ADDR)]),URL:detail()});d=h.collect_hyogo(c,limit=1)
        self.assertEqual(len(d['facilities']),1);self.assertNotIn(other_url,c.calls);self.assertFalse(d['collection']['traversal_complete'])
        self.assertIn(other_url,d['collection']['remaining_scope']);self.assertEqual(d['collection']['xml_unique_codes'],2)
        for limit in [0,-1,True]:
            with self.assertRaises(ValueError):h.collect_hyogo(c,limit=limit)
    def test_host_failures_stop_before_further_details(self):
        other='6301048';other_url=BASE+'data/'+other+'.html'
        for failure in [page(URL,'denied',403),page(URL,'rate limited',429),page(URL,'<input type="password">'),None]:
            pages={QUERY:xml([(CODE,'湊川神社',ADDR),(other,'湊川神社',ADDR)]),other_url:detail(code=other)}
            if failure is not None:pages[URL]=failure
            c=Client(pages);d=h.collect_hyogo(c)
            self.assertNotIn(other_url,c.calls);self.assertIn(other_url,d['collection']['remaining_scope']);self.assertTrue(d['collection']['failed_pages'])
    def test_200_challenge_header_stops_before_next_profile(self):
        other='6301048';other_url=BASE+'data/'+other+'.html'
        c=Client({QUERY:xml([(CODE,'湊川神社',ADDR),(other,'湊川神社',ADDR)]),
            URL:page(URL,'<title>Just a moment...</title>',headers={'cf-mitigated':'challenge'}),other_url:detail(code=other)})
        d=h.collect_hyogo(c)
        self.assertNotIn(other_url,c.calls)
        self.assertTrue(d['collection']['failed_pages'])

    def test_glyph_correction_cannot_clear_conflicting_xml_identity(self):
        from test_corrections import correction
        from njd.corrections import apply_corrections
        from njd.validation import eligible
        for names_addresses in [[(CODE,'湊川神社',ADDR),(CODE,'湊河神社',ADDR)],
                                [(CODE,'湊川神社',ADDR),(CODE,'湊川神社',ADDR+'9')]]:
            d=h.collect_hyogo(Client({QUERY:xml(names_addresses),URL:detail(name='湊<img src="glyph.gif" />神社')}))
            c=correction(d,dict(surface='湊川神社',reading='みなとがわじんじゃ'))
            self.assertEqual(eligible(apply_corrections(d,c)),[])
            self.assertTrue(d['facilities'][0].get('review_reason'))

    def test_unknown_profile_is_isolated_and_incomplete(self):
        other='6301048';other_url=BASE+'data/'+other+'.html'
        d=h.collect_hyogo(Client({QUERY:xml([(CODE,'湊川神社',ADDR),(other,'湊川神社',ADDR)]),URL:'<p>unknown</p>',other_url:detail(code=other)}))
        self.assertEqual(len(d['facilities']),1);self.assertFalse(d['collection']['traversal_complete']);self.assertTrue(d['collection']['failed_pages'])
    def test_empty_or_invalid_xml_is_not_complete_or_deletion_eligible(self):
        for text in [xml([]),'<Locations/>','<html>blocked</html>','<Locations><Locate></Locate></Locations>']:
            d=h.collect_hyogo(Client({QUERY:text}));self.assertFalse(d['collection']['traversal_complete']);self.assertTrue(d['collection']['remaining_scope'])
        from njd.nationwide import save_collection,PartialSnapshotError
        with tempfile.TemporaryDirectory() as tmp:
            save_collection(tmp,'hyogo',self.collect());before=(Path(tmp)/'sources/hyogo.json').read_bytes()
            empty=h.collect_hyogo(Client({QUERY:xml([])}))
            with self.assertRaises(PartialSnapshotError):save_collection(tmp,'hyogo',empty)
            self.assertEqual((Path(tmp)/'sources/hyogo.json').read_bytes(),before)
    def test_unobserved_query_or_detail_scope_is_rejected(self):
        for url in [QUERY.replace('ne_lat=36','ne_lat=37'),QUERY+'&x=1',QUERY+'&ne_lat=36',BASE+'data/../data/'+CODE+'.html','https://evil.test/data/'+CODE+'.html',URL+'?x=1',BASE+'data/123.html']:
            with self.subTest(url=url),self.assertRaises(ValueError):h._url(url)
        for code in ['../bad','6301046/evil','1','']:
            with self.assertRaises(ValueError):h.parse_xml(page(QUERY,xml([(code,'湊川神社',ADDR)])))
    def test_redirect_identity_guard_precedes_target_network_and_policy(self):
        class Redirect:
            def __init__(self,target):self.calls=[];self.target=target
            def _policy(self,url,**kw):self.calls.append(('policy',url))
            def _raw(self,url,**kw):self.calls.append(('request',url));return page(url,'',302,{'location':self.target})
        for target in ['https://evil.test/data/'+CODE+'.html',BASE+'data/6301048.html',QUERY,URL]:
            c=Redirect(target)
            with self.assertRaises((ValueError,FetchError)):h._fetch(c,URL)
            self.assertEqual(c.calls,[('policy',URL),('request',URL)])
    def test_refresh_intent_is_honored(self):
        class Raw:
            refresh_requested=True
            def __init__(self):self.flags=[]
            def _policy(self,url,**kw):self.flags.append(kw['refresh'])
            def _raw(self,url,**kw):self.flags.append(kw['refresh']);return page(url,xml())
        c=Raw();h._fetch(c,QUERY);self.assertEqual(c.flags,[True,True])
    def test_input_map_row_is_not_mutated(self):
        ref=h.parse_xml(page(QUERY,xml()))[0];before=copy.deepcopy(ref);h.parse_detail(page(URL,detail()),ref);self.assertEqual(ref,before)
    def test_broader_data_restriction_stops_host_traversal(self):
        other='6301048';other_url=BASE+'data/'+other+'.html'
        c=Client({QUERY:xml([(CODE,'湊川神社',ADDR),(other,'湊川神社',ADDR)]),URL:detail()+'<footer>情報の無断転載を禁止します。</footer>',other_url:detail(code=other)})
        d=h.collect_hyogo(c)
        self.assertNotIn(other_url,c.calls)
        self.assertEqual(d['facilities'],[])
        self.assertTrue(d['collection']['failed_pages'])
    def test_cached_resume_uses_existing_xml_and_profile_responses(self):
        from njd.http import Client as HttpClient
        other='6301048';other_url=BASE+'data/'+other+'.html';calls=[]
        bodies={BASE+'robots.txt':(404,b''),QUERY:(200,xml([(CODE,'湊川神社',ADDR),(other,'湊川神社',ADDR)]).encode()),URL:(200,detail().encode()),other_url:(200,detail(code=other).encode())}
        def transport(url,timeout,user_agent):
            calls.append(url);status,body=bodies[url];return status,{'content-type':'text/html; charset=utf-8'},body
        with tempfile.TemporaryDirectory() as tmp:
            first=h.collect_hyogo(HttpClient(tmp,interval=0,retries=0,transport=transport),limit=1)
            self.assertEqual(len(first['facilities']),1)
            second=h.collect_hyogo(HttpClient(tmp,interval=0,retries=0,transport=transport))
            self.assertEqual(len(second['facilities']),2);self.assertTrue(second['collection']['traversal_complete'])
            self.assertEqual(calls.count(QUERY),1);self.assertEqual(calls.count(URL),1);self.assertEqual(calls.count(other_url),1)
    def test_blank_xml_place_binds_code_name_and_uses_explicit_detail_address(self):
        refs=h.parse_xml(page(QUERY,xml([(CODE,'湊川神社','')])))
        self.assertEqual(refs[0]['address'],'')
        r=h.parse_detail(page(URL,detail()),refs[0])
        self.assertFalse(r.get('review_reason'))
        self.assertEqual(r['address'],ADDR)
        self.assertEqual(r['map_address_raw'],'')
        self.assertEqual(r['address_role'],'agency profile shrine location')
        d=h.collect_hyogo(Client({QUERY:xml([(CODE,'湊川神社','')]),URL:detail()}))
        self.assertEqual(d['entries'][0]['status'],'verified')
        self.assertEqual(d['facilities'][0]['map_address_raw'],'')
        self.assertEqual(d['facilities'][0]['xml_occurrences'][0]['address_raw'],'')
    def test_missing_detail_location_is_pending_even_if_map_place_is_blank(self):
        d=h.collect_hyogo(Client({QUERY:xml([(CODE,'湊川神社','')]),URL:detail(address='')}))
        self.assertEqual(d['facilities'][0]['status'],'pending')
    def test_nonempty_limited_snapshot_cannot_remove_saved_native_ids(self):
        from njd.nationwide import save_collection,PartialSnapshotError
        other='6301048';other_url=BASE+'data/'+other+'.html'
        pages={QUERY:xml([(CODE,'湊川神社',ADDR),(other,'湊川神社',ADDR)]),URL:detail(),other_url:detail(code=other)}
        with tempfile.TemporaryDirectory() as tmp:
            save_collection(tmp,'hyogo',h.collect_hyogo(Client(pages)))
            before=(Path(tmp)/'sources/hyogo.json').read_bytes()
            with self.assertRaises(PartialSnapshotError):save_collection(tmp,'hyogo',h.collect_hyogo(Client(pages),limit=1))
            self.assertEqual((Path(tmp)/'sources/hyogo.json').read_bytes(),before)
    def test_registry(self):
        from njd.catalog import registry
        self.assertEqual(registry()['hyogo']['code'],'28')
