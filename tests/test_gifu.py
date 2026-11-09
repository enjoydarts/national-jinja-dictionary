"""Synthetic official field fixtures; no acquired article/photo content."""
import unittest
from urllib.parse import quote
from njd.http import Page, FetchError
try:
    from njd.adapters import gifu as g
except ImportError:
    g = None

BASE='https://www.gifu-jinjacho.jp/'
INDEX=BASE+'jnjyalist.php'
SEARCH=BASE+'search.php?jinjya='+quote('秋葉神社')
DETAIL=BASE+'syosai.php?shrno=752&shrname='+quote('■秋葉神社■')
ADDRESS='岐阜県海津市海津町高須町874番地'
def page(url,html,status=200,headers=None):
    return Page(url,status,headers or {'content-type':'text/html; charset=utf-8'},html.encode(),'2026-11-09T00:00:00+00:00')
def idx(readings=('あきはじんじゃ','あきばじんじゃ','あきわじんじゃ'),next_url=None,total=3):
    return f'{total} 件の神社名が登録されています。<table class="jnm_list">'+''.join(f'<tr><td><a class="jnm_font" href="{SEARCH}">秋葉神社</a></td><td>{r}</td><td>7</td></tr>' for r in readings)+'</table>'+ (f'<a href="{next_url}">次の 20 件&gt;</a>' if next_url else '')
def search(items=None,total=1,next_url=None):
    if items is None:items=[(DETAIL,'秋葉神社',ADDRESS)]
    return f'{total} 件の神社がみつかりました。<table class="sc_tbl">'+''.join(f'<tr><td width="555" style="color:purple"><a href="{u}">{n}</a></td><tr><td colspan="2" style="color:#cc0066">ARTICLE SECRET</td></tr><tr><td width="555" style="color:#993300">503-0653 {a}</td></tr>' for u,n,a in items)+'</table>'+ (f'<a href="{next_url}">次の 10 件&gt;</a>' if next_url else '')
def detail(name='秋葉神社',kana='(あきばじんじゃ)',address=ADDRESS):
    return f'<table><tr><td height="80"><font class="hyodai">{name}</font><font>{kana}</font></td></tr><tr><td class="moji1">alias</td></tr><tr><td class="moji3">〒503-0653 {address}</td></tr><tr><td class="moji4">ARTICLE SECRET</td></tr></table>'
class Client:
    def __init__(self,pages):self.pages=pages;self.calls=[]
    def fetch(self,url):
        self.calls.append(url)
        if url not in self.pages:raise FetchError('unfetched fixture')
        value=self.pages[url];return value if isinstance(value,Page) else page(url,value)
class GifuTests(unittest.TestCase):
    def setUp(self):self.assertIsNotNone(g,'Gifu adapter must exist')
    def collect(self,**kw):return g.collect_gifu(Client({INDEX:idx(),SEARCH:search(),DETAIL:detail(**kw)}))
    def test_index_keeps_group_readings_but_shared_search_is_fetched_once(self):
        p=g.parse_index(page(INDEX,idx(total=828)));self.assertEqual(p['total'],828);self.assertEqual(len(p['rows']),3)
        c=Client({INDEX:idx(),SEARCH:search(),DETAIL:detail()});d=g.collect_gifu(c)
        self.assertEqual(c.calls.count(SEARCH),1);self.assertEqual(d['entries'][0]['reading'],'あきばじんじゃ')
        self.assertEqual(d['collection']['index_groups_observed'],3)
    def test_detail_literal_fields_and_fact_only_evidence(self):
        r=g.parse_detail(page(DETAIL,detail()),expected_name='秋葉神社',expected_address=ADDRESS)
        self.assertEqual((r['name'],r['reading_raw'],r['address'],r['source_id']),('秋葉神社','あきばじんじゃ',ADDRESS,'752'))
        self.assertEqual(r['reading_display_raw'],'(あきばじんじゃ)');self.assertTrue(r['address_raw'].startswith('〒503'))
        self.assertNotIn('SECRET',r['evidence']);self.assertNotIn('alias',r['evidence'])
    def test_search_nested_rows_exclude_snippet(self):
        p=g.parse_search(page(SEARCH,search()));self.assertEqual(p['total'],1);self.assertEqual(len(p['rows']),1)
        self.assertEqual(p['rows'][0]['address'],ADDRESS);self.assertNotIn('SECRET',str(p))
    def test_missing_partial_annotated_or_multiple_reading_stays_pending(self):
        for kana in ['', '(あきば)', '(あきばじんじゃ)(あきはじんじゃ)', '(あきばじんじゃ（通称）)']:
            with self.subTest(kana=kana):self.assertEqual(self.collect(kana=kana)['entries'][0]['status'],'pending')
    def test_glyph_and_annotated_name_remain_pending(self):
        for name in ['秋<img src="gaiji/x.gif">神社','秋葉神社（旧称）']:
            r=g.parse_detail(page(DETAIL,detail(name=name)));self.assertTrue(r.get('review_reason') or r.get('name_rendering_status'))
    def test_name_and_address_mismatch_stays_pending(self):
        for kw in [dict(name='別神社'),dict(address='岐阜県海津市海津町高須町999番地')]:
            d=self.collect(**kw);self.assertEqual(d['facilities'][0]['status'],'pending')
    def test_unknown_or_missing_structures_fail(self):
        for func,url in [(g.parse_index,INDEX),(g.parse_search,SEARCH),(g.parse_detail,DETAIL)]:
            with self.assertRaises(ValueError):func(page(url,'<p>unknown</p>'))
    def test_explicit_zero_search_is_complete(self):
        self.assertEqual(g.parse_search(page(SEARCH,search([],0)))['rows'],[])
        d=g.collect_gifu(Client({INDEX:idx(readings=(),total=0)}));self.assertTrue(d['collection']['traversal_complete'])
    def test_limit_and_failed_detail_are_recorded(self):
        d=g.collect_gifu(Client({INDEX:idx(),SEARCH:search()}));self.assertFalse(d['collection']['traversal_complete']);self.assertTrue(d['collection']['failed_pages'])
        second=BASE+'syosai.php?shrno=753&shrname='+quote('■秋葉神社■')
        c=Client({INDEX:idx(),SEARCH:search([(DETAIL,'秋葉神社',ADDRESS),(second,'秋葉神社',ADDRESS)],2),DETAIL:detail()})
        d=g.collect_gifu(c,limit=1);self.assertNotIn(second,c.calls);self.assertFalse(d['collection']['traversal_complete'])
        for v in [0,-1,True]:
            with self.assertRaises(ValueError):g.collect_gifu(c,limit=v)
    def test_index_and_search_pagination_only_follow_real_next_and_detect_loop(self):
        n=BASE+'jnjyalist.php?page=2&tcnt=828&keysel='
        c=Client({INDEX:idx(next_url=n),n:idx(next_url=INDEX),SEARCH:search(),DETAIL:detail()})
        d=g.collect_gifu(c);self.assertFalse(d['collection']['traversal_complete']);self.assertTrue(any('loop' in x['reason'] for x in d['collection']['failed_pages']))
        sn=SEARCH+'&page=2&tcnt=2'
        p=g.parse_search(page(SEARCH,search(next_url=sn)));self.assertEqual(p['next_url'],sn)
    def test_forbidden_urls_are_rejected(self):
        for url in ['https://evil.test/syosai.php?shrno=752',BASE+'other.php',DETAIL+'&unknown=1',BASE+'../syosai.php?shrno=752',BASE+'syosai.php?shrno=752&shrno=753']:
            with self.subTest(url=url),self.assertRaises(ValueError):g.parse_detail(page(url,detail()))
    def test_redirect_guards_before_request_and_http_status(self):
        class Redirect:
            def __init__(self,target,status=302):self.calls=[];self.target=target;self.status=status
            def _policy(self,url,**kw):pass
            def _raw(self,url,**kw):self.calls.append(url);return page(url,'',self.status,{'location':self.target})
        for url in ['https://evil.test/syosai.php?shrno=752',BASE+'syosai.php?shrno=753',BASE+'search.php?jinjya='+quote('別神社')]:
            c=Redirect(url)
            with self.assertRaises((ValueError,FetchError)):g._fetch(c,DETAIL)
            self.assertEqual(c.calls,[DETAIL])
        with self.assertRaises(FetchError):g._fetch(Redirect(DETAIL,500),DETAIL)
    def test_conflicting_search_rows_for_one_native_id_are_pending(self):
        s=search([(DETAIL,'秋葉神社',ADDRESS),(DETAIL,'別神社',ADDRESS)],2)
        d=g.collect_gifu(Client({INDEX:idx(),SEARCH:s,DETAIL:detail()}));self.assertEqual(d['entries'][0]['status'],'pending')
    def test_actual_detail_button_is_used_and_conflicting_button_identity_fails(self):
        star=DETAIL.replace(quote('■秋葉神社■'),quote('★秋葉神社★'))
        html=search().replace(DETAIL,star).replace('</td><tr>',f'</td><td width="200"><a href="{DETAIL}">詳細</a></td><tr>',1)
        self.assertEqual(g.parse_search(page(SEARCH,html))['rows'][0]['url'],DETAIL)
        bad=html.replace(f'href="{DETAIL}"',f'href="{BASE}syosai.php?shrno=999"')
        with self.assertRaises(ValueError):g.parse_search(page(SEARCH,bad))
    def test_detail_query_label_and_search_group_name_cannot_silently_change(self):
        r=g.parse_detail(page(DETAIL,detail(name='別神社')))
        self.assertIn('review_reason',r)
        other=BASE+'syosai.php?shrno=753&shrname='+quote('■別神社■')
        d=g.collect_gifu(Client({INDEX:idx(),SEARCH:search([(other,'別神社',ADDRESS)]),other:detail(name='別神社',kana='(べつじんじゃ)')}))
        self.assertEqual(d['entries'][0]['status'],'pending')
    def test_limit_stops_before_starting_another_group_search(self):
        other=BASE+'search.php?jinjya='+quote('別神社')
        html=idx(readings=('あきばじんじゃ',),total=2).replace('</table>',f'<tr><td><a href="{other}">別神社</a></td><td>べつじんじゃ</td><td>1</td></tr></table>')
        c=Client({INDEX:html,SEARCH:search(),DETAIL:detail()});d=g.collect_gifu(c,limit=1)
        self.assertNotIn(other,c.calls);self.assertIn(other,d['collection']['remaining_scope'])
    def test_explicit_incomplete_totals_are_not_complete(self):
        d=g.collect_gifu(Client({INDEX:idx(total=828),SEARCH:search(total=79),DETAIL:detail()}))
        self.assertFalse(d['collection']['traversal_complete'])
        self.assertTrue(any('total' in p['reason'] for p in d['collection']['failed_pages']))
    def test_raw_name_layout_and_postal_address_are_not_rewritten(self):
        r=g.parse_detail(page(DETAIL,detail(name='秋葉\n神社',address=ADDRESS.replace('海津町','海津町　'))))
        self.assertEqual(r['name'],'秋葉\n神社')
        self.assertIn('海津町　',r['address_raw'])
    def test_glyph_tags_keep_position_spelling_and_affect_source_fingerprint(self):
        tag="<IMG  SRC='gaiji/a.gif' ALT='unknown' />"
        hashes=[]
        for actual in [tag,tag.replace('a.gif','b.gif'),tag.replace('unknown','different')]:
            name='秋'+actual+'神社'
            row=g.parse_detail(page(DETAIL,detail(name=name)))
            self.assertEqual(row['name'],name)
            d=self.collect(name=name)
            f=d['facilities'][0];e=d['entries'][0]
            self.assertEqual(f['name_raw'],name)
            self.assertEqual(f['name_rendering_status'],'external_glyph')
            self.assertEqual(e['status'],'pending');self.assertEqual(e['reading'],'')
            from njd.validation import eligible
            self.assertEqual(eligible(d),[])
            from njd.exporters import render
            self.assertEqual(render(d,'mozc').rows,0)
            self.assertEqual(render(d,'macos').rows,0)
            self.assertEqual(e['reading_display_raw'],'(あきばじんじゃ)')
            hashes.append(f['source_hash'])
        self.assertEqual(len(set(hashes)),3)
    def test_suffix_only_reading_is_partial_and_never_exported(self):
        for kana in ['(じんじゃ)','(しゃ)']:
            d=self.collect(kana=kana)
            self.assertEqual(d['entries'][0]['status'],'pending')
            self.assertEqual(d['entries'][0]['reading'],'')
        self.assertEqual(g._reading_reason('神社','じんじゃ'),'')
    def test_positive_group_count_zero_search_must_be_partial(self):
        d=g.collect_gifu(Client({INDEX:idx(readings=('あきばじんじゃ',),total=1),SEARCH:search([],0)}))
        self.assertFalse(d['collection']['traversal_complete'])
        self.assertTrue(d['collection']['failed_pages'])
        self.assertIn(SEARCH,d['collection']['remaining_scope'])
    def test_complete_shared_query_group_count_sum_must_match_search_total(self):
        # Each reading group reports one; search covers their combined three.
        html=idx().replace('<td>7</td>','<td>1</td>')
        d=g.collect_gifu(Client({INDEX:html,SEARCH:search(),DETAIL:detail()}))
        self.assertFalse(d['collection']['traversal_complete'])
        self.assertIn(SEARCH,d['collection']['remaining_scope'])
        self.assertTrue(any('group' in x['reason'] for x in d['collection']['failed_pages']))
    def test_shared_query_sum_is_checked_after_all_index_pages(self):
        n=BASE+'jnjyalist.php?page=2&tcnt=2&keysel='
        first=idx(readings=('あきばじんじゃ',),next_url=n,total=2).replace('<td>7</td>','<td>1</td>')
        second=idx(readings=('あきはじんじゃ',),total=2).replace('<td>7</td>','<td>1</td>')
        other=BASE+'syosai.php?shrno=753&shrname='+quote('■秋葉神社■')
        results=search([(DETAIL,'秋葉神社',ADDRESS),(other,'秋葉神社',ADDRESS)],2)
        d=g.collect_gifu(Client({INDEX:first,n:second,SEARCH:results,DETAIL:detail(),other:detail()}))
        self.assertTrue(d['collection']['traversal_complete'])
        self.assertEqual(len(d['facilities']),2)
    def test_raw_glyph_attribute_whitespace_and_newlines_are_preserved(self):
        tag="<IMG  SRC = 'gaiji/a.gif'\n ALT = 'two  words'   />"
        name='秋'+tag+'神社'
        row=g.parse_detail(page(DETAIL,detail(name=name)))
        self.assertEqual(row['name'],name)
        self.assertIn(tag,row['evidence'])
        d=self.collect(name=name)
        self.assertEqual(d['facilities'][0]['name_raw'],name)
        self.assertEqual(d['entries'][0]['status'],'pending')
        other=self.collect(name=name.replace('two  words','two words'))
        self.assertNotEqual(d['facilities'][0]['source_hash'],other['facilities'][0]['source_hash'])
    def stop_scope_fixture(self):
        second=BASE+'syosai.php?shrno=753&shrname='+quote('■秋葉神社■')
        other=BASE+'search.php?jinjya='+quote('別神社')
        index_next=BASE+'jnjyalist.php?page=2&tcnt=3&keysel='
        search_next=SEARCH+'&page=2&tcnt=3'
        listing=idx(readings=('あきばじんじゃ',),total=3,next_url=index_next).replace('<td>7</td>','<td>2</td>').replace('</table>',f'<tr><td><a href="{other}">別神社</a></td><td>べつじんじゃ</td><td>1</td></tr></table>')
        pages={INDEX:listing,SEARCH:search([(DETAIL,'秋葉神社',ADDRESS),(second,'秋葉神社',ADDRESS)],total=3,next_url=search_next),DETAIL:detail(),second:detail(),other:search([],0),index_next:idx(readings=(),total=3),search_next:search([],0)}
        return pages,second,other,index_next,search_next
    def test_first_detail_fetch_failure_stops_all_host_traversal(self):
        for failure in [FetchError('ConnectionRefused'),OSError('connection refused')]:
            pages,second,other,index_next,search_next=self.stop_scope_fixture()
            class Broken(Client):
                def fetch(self,url):
                    if url==DETAIL:self.calls.append(url);raise failure
                    return super().fetch(url)
            c=Broken(pages);d=g.collect_gifu(c)
            self.assertEqual(c.calls,[INDEX,SEARCH,DETAIL])
            self.assertEqual(len(d['collection']['failed_pages']),1)
            self.assertFalse(d['collection']['traversal_complete'])
            for url in [DETAIL,second,other,index_next,search_next]:self.assertIn(url,d['collection']['remaining_scope'])
    def test_search_fetch_failure_stops_before_next_group_and_index(self):
        pages,second,other,index_next,search_next=self.stop_scope_fixture();del pages[SEARCH]
        c=Client(pages);d=g.collect_gifu(c)
        self.assertEqual(c.calls,[INDEX,SEARCH])
        for url in [SEARCH,other,index_next]:self.assertIn(url,d['collection']['remaining_scope'])
    def test_search_next_page_fetch_failure_preserves_records_and_stops(self):
        pages,second,other,index_next,search_next=self.stop_scope_fixture();del pages[search_next]
        c=Client(pages);d=g.collect_gifu(c)
        self.assertEqual(c.calls,[INDEX,SEARCH,DETAIL,second,search_next])
        self.assertEqual(len(d['facilities']),2)
        for url in [search_next,other,index_next]:self.assertIn(url,d['collection']['remaining_scope'])
    def test_detail_auth_or_redirect_rejection_stops_host_traversal(self):
        for response in [page(DETAIL,'<input type="password">'),page(DETAIL,'',302,{'location':BASE+'syosai.php?shrno=999'})]:
            pages,second,other,index_next,search_next=self.stop_scope_fixture();pages[DETAIL]=response
            c=Client(pages);d=g.collect_gifu(c)
            self.assertEqual(c.calls,[INDEX,SEARCH,DETAIL])
            self.assertIn(second,d['collection']['remaining_scope'])
    def test_unknown_detail_html_is_isolated_without_inventing_a_row(self):
        pages,second,other,index_next,search_next=self.stop_scope_fixture()
        pages[DETAIL]='<p>unknown detail structure</p>'
        c=Client(pages);d=g.collect_gifu(c)
        self.assertIn(second,c.calls)
        self.assertFalse(any(f['native_source_id']=='752' for f in d['facilities']))
        self.assertFalse(d['collection']['traversal_complete'])
    def test_later_detail_failure_keeps_previously_confirmed_record(self):
        pages,second,other,index_next,search_next=self.stop_scope_fixture();del pages[second]
        c=Client(pages);d=g.collect_gifu(c)
        self.assertEqual(c.calls,[INDEX,SEARCH,DETAIL,second])
        self.assertEqual(len(d['facilities']),1)
        self.assertEqual(d['facilities'][0]['source_hash'],self.collect()['facilities'][0]['source_hash'])
        self.assertEqual(d['entries'][0]['reading'],'あきばじんじゃ')
        for url in [second,other,index_next,search_next]:self.assertIn(url,d['collection']['remaining_scope'])
    def test_next_index_fetch_failure_preserves_records_and_stops(self):
        index_next=BASE+'jnjyalist.php?page=2&tcnt=2&keysel='
        listing=idx(readings=('あきばじんじゃ',),total=2,next_url=index_next).replace('<td>7</td>','<td>1</td>')
        c=Client({INDEX:listing,SEARCH:search(),DETAIL:detail()});d=g.collect_gifu(c)
        self.assertEqual(c.calls,[INDEX,SEARCH,DETAIL,index_next])
        self.assertEqual(len(d['facilities']),1)
        self.assertEqual(d['collection']['remaining_scope'],[index_next])
        self.assertEqual(len(d['collection']['failed_pages']),1)
    def test_cf_mitigated_header_stops_before_decode_and_all_further_requests(self):
        for headers in [{'cf-mitigated':'challenge'},{'CF-Mitigated':'ChAlLeNgE'}]:
            pages,second,other,index_next,search_next=self.stop_scope_fixture()
            pages[DETAIL]=Page(DETAIL,200,dict(headers,**{'content-type':'text/html; charset=utf-8'}),b'Just a moment\xff','2026-11-09T00:00:00+00:00')
            c=Client(pages);d=g.collect_gifu(c)
            self.assertEqual(c.calls,[INDEX,SEARCH,DETAIL])
            self.assertEqual(len(d['collection']['failed_pages']),1)
            self.assertIn('challenge',d['collection']['failed_pages'][0]['reason'].lower())
            for url in [DETAIL,second,other,index_next,search_next]:self.assertIn(url,d['collection']['remaining_scope'])
    def test_registry(self):
        from njd.catalog import registry
        self.assertEqual(registry()['gifu']['code'],'21')
