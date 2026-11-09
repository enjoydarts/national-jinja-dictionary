"""Synthetic search HTML only; no acquired page bodies."""
import unittest
from njd.adapters import niigata as n
from njd.http import Page, FetchError
from njd.validation import validate

ORIGIN='https://niigata-jinjacho.jp'
INDEX=ORIGIN+'/shrine_niigata/'
A=INDEX+'search.php?area=15101'
B=INDEX+'search.php?area=15204'
NEXT=INDEX+'search.php?area=15101&keyword=&page=2&num=10'

def page(url,text):return Page(url,200,{'content-type':'text/html; charset=UTF-8'},text.encode(),'2026-11-09T00:00:00+00:00')
def menu(two=False):
    codes=[('15101','新潟市北区')]+([('15204','三条市')] if two else [])
    return '<form method="get" action="search.php"><select name="area"><option value="">―</option>'+''.join(f'<option value="{code}">{name}</option>' for code,name in codes)+'</select><input type="text" name="keyword" value=""></form>'+''.join(f'<a href="search.php?area={code}">{name}</a>' for code,name in codes)
def row(name='石動神社',kana='いするぎじんじゃ',address='新潟市北区白新町1丁目1番11号'):
    return f'<div class="shrine"><dl><dt class="name">神社名</dt><dd class="name">{name}</dd><dt class="furigana">ふりがな</dt><dd class="furigana">{kana}</dd><dt class="place">鎮座地</dt><dd class="place">{address}<span>（<a href="http://maps.google.co.jp/maps?q={address}&t=m&z=14">Google Mapを表示する</a>）</span></dd></dl></div>'
def result(rows,total=1,next_url=None):return '<section id="search_result"><h1>新潟市北区の神社</h1><p class="number"><strong>'+str(total)+'</strong>件</p>'+''.join(rows)+'<div class="navcnt">'+(f'<a class="next" href="{next_url}">次へ &gt;</a>' if next_url else '')+'</div></section>'
class Client:
    def __init__(self,pages):self.pages=pages;self.calls=[]
    def fetch(self,url):
        self.calls.append(url)
        if url not in self.pages:raise FetchError('missing fixture')
        return page(url,self.pages[url])

class NiigataTests(unittest.TestCase):
    def test_literal_fields_and_map_ui_removed_without_changing_address(self):
        rows,more,total=n.parse_results(page(A,result([row()])))
        self.assertEqual((rows[0]['name'],rows[0]['reading_raw'],rows[0]['address']),('石動神社','いするぎじんじゃ','新潟市北区白新町1丁目1番11号'))
        self.assertNotIn('source_id',rows[0]);self.assertEqual((more,total),(None,1))
        self.assertIn('dd.furigana',rows[0]['locator']);self.assertEqual(rows[0]['page_hash'],page(A,result([row()])).sha256)
    def test_menu_uses_actual_links_and_exact_form_options(self):
        urls,options=n.parse_index(page(INDEX,menu(True)))
        self.assertEqual(urls,[A,B]);self.assertEqual(options[0],{'value':'15101','label':'新潟市北区'})
        with self.assertRaises(ValueError):n.parse_index(page(INDEX,menu().replace('search.php?area=15101','search.php?area=15102')))
    def test_pagination_actual_next_only_and_cross_area_rejected(self):
        rows,more,total=n.parse_results(page(A,result([row()],2,NEXT)+'<a href="search.php?area=15101&page=999">unrelated</a>'))
        self.assertEqual((more,total),(NEXT,2))
        for bad in [B,'https://evil.test/shrine_niigata/search.php?area=15101',A+'%26page=2']:
            with self.assertRaises(ValueError):n.parse_results(page(A,result([row()],2,bad)))
    def test_collect_facility_limit_preserves_observed_rows_and_remaining(self):
        pages={INDEX:menu(True),A:result([row(),row(address='新潟市北区木崎3766番地')],3,NEXT)}
        c=Client(pages);d=n.collect_niigata(c,limit=1)
        self.assertEqual(len(d['facilities']),1);self.assertEqual(d['collection']['source_rows_observed'],2)
        self.assertFalse(d['collection']['traversal_complete']);self.assertTrue(d['collection']['remaining_scope'])
        self.assertEqual(c.calls,[INDEX,A]);self.assertEqual(d['collection']['native_totals']['15101'],3)
    def test_full_traversal_same_name_different_address_and_stable_identity(self):
        pages={INDEX:menu(),A:result([row()],2,NEXT),NEXT:result([row(address='新潟市北区木崎3766番地')],2)}
        d=n.collect_niigata(Client(pages));self.assertEqual(len(d['facilities']),2);self.assertTrue(d['collection']['traversal_complete'])
        self.assertTrue(all(f['native_source_id'] is None for f in d['facilities']))
        pages[A]=result([row(address='新潟市北区木崎3766番地'),row()],2);d2=n.collect_niigata(Client(pages))
        self.assertEqual({f['id'] for f in d['facilities']},{f['id'] for f in d2['facilities']})
        self.assertFalse([x for x in validate(d) if x.get('severity')=='error'])
    def test_partial_alias_reading_preserved_hashed_pending_and_explicit_sha(self):
        for kana,name,want in [('いするぎ','石動神社','pending'),('いするぎじんじゃ・せきどうじんじゃ','石動神社','pending'),('すわしゃ','諏訪神社','verified'),('ｽﾜｼｬ','諏訪神社','verified'),('すわじんじゃ','諏訪神社（通称別名）','pending')]:
            d=n.collect_niigata(Client({INDEX:menu(),A:result([row(name,kana)])}))
            e=d['entries'][0];self.assertEqual(e['status'],want);self.assertEqual(e['reading_raw'],kana)
            if want=='pending':self.assertEqual(e['reading'],'')
        a=n.collect_niigata(Client({INDEX:menu(),A:result([row(kana='いするぎ')])}))
        b=n.collect_niigata(Client({INDEX:menu(),A:result([row(kana='せきどう')])}))
        self.assertNotEqual(a['entries'][0]['source_hash'],b['entries'][0]['source_hash'])
    def test_explicit_aidono_full_reading_accepted_without_inference(self):
        for raw,status,reading in [('しんめいしゃすわしゃあいどの','verified','しんめいしゃすわしゃあいどの'),('あいどの','pending',''),('しんめいしゃすわしゃ','pending','')]:
            with self.subTest(raw=raw):
                d=n.collect_niigata(Client({INDEX:menu(),A:result([row('神明社諏訪社合殿',raw)])}))
                self.assertEqual(d['entries'][0]['reading_raw'],raw)
                self.assertEqual(d['entries'][0]['status'],status)
                self.assertEqual(d['entries'][0]['reading'],reading)

    def test_suffix_only_and_parenthetical_alias_do_not_verify(self):
        for name,kana in [('石動神社','じんじゃ'),('石動（別名）神社','いするぎじんじゃ')]:
            d=n.collect_niigata(Client({INDEX:menu(),A:result([row(name,kana)])}))
            self.assertEqual(d['entries'][0]['status'],'pending')
            self.assertEqual(d['entries'][0]['reading'],'')

    def test_unknown_fields_total_mismatch_loop_and_failure_stay_partial(self):
        for html in ['<p>maintenance</p>',result([row()],2),result([row()],2,A),result([row()],2,NEXT)]:
            d=n.collect_niigata(Client({INDEX:menu(),A:html}))
            self.assertFalse(d['collection']['traversal_complete']);self.assertTrue(d['collection']['failed_pages'])
        with self.assertRaises(ValueError):n.parse_results(page(A,result([row().replace('ふりがな','読み')])) )
        with self.assertRaises(ValueError):n.parse_results(page(A,result([row().replace('</dl>','<dd class="name">別名</dd></dl>')])) )
    def test_image_glyph_in_name_is_not_silently_dropped(self):
        d=n.collect_niigata(Client({INDEX:menu(),A:result([row(name='石<img src="glyph.png" alt="異体字">動神社')])}))
        self.assertEqual(d['facilities'][0]['status'],'pending')
        self.assertEqual(d['entries'][0]['status'],'pending')

    def test_glyph_raw_start_tag_and_changed_reference_affect_fingerprint(self):
        names=["石<b>動</b><img ALT='外字甲' src='glyphA.png' />神社", "石<b>動</b><img ALT='外字乙' src='glyphB.png' />神社"]
        datasets=[n.collect_niigata(Client({INDEX:menu(),A:result([row(name=name)])})) for name in names]
        self.assertEqual(datasets[0]['facilities'][0]['name_raw'],"石動<img ALT='外字甲' src='glyphA.png' />神社")
        self.assertEqual(datasets[0]['entries'][0]['name_raw'],"石動<img ALT='外字甲' src='glyphA.png' />神社")
        self.assertNotEqual(datasets[0]['entries'][0]['source_hash'],datasets[1]['entries'][0]['source_hash'])
        for data in datasets:
            self.assertEqual(data['facilities'][0]['reason'],'source name uses an external glyph; Unicode correction requires references')
            self.assertEqual(data['entries'][0]['reason'],'source name uses an external glyph; Unicode correction requires references')
            self.assertEqual(data['entries'][0]['status'],'pending')
            self.assertEqual(data['entries'][0]['reading'],'いするぎじんじゃ')
            self.assertFalse([p for p in validate(data) if p.get('severity')=='error'])

    def test_partial_reading_with_glyph_still_suppressed(self):
        d=n.collect_niigata(Client({INDEX:menu(),A:result([row(name='石<img src="/glyph.png" alt="異体字">動神社',kana='いするぎ')])}))
        self.assertEqual(d['entries'][0]['reading_raw'],'いするぎ')
        self.assertEqual(d['entries'][0]['reading'],'')
        self.assertEqual(d['entries'][0]['status'],'pending')
        self.assertEqual(d['facilities'][0]['reason'],'source name uses an external glyph; Unicode correction requires references')

    def test_duplicate_unknown_name_preserves_review_and_raw_evidence(self):
        glyph='石<img src="glyph.png" alt="異体字">動神社'
        for readings in [('いするぎじんじゃ','せきどうじんじゃ'),('せきどうじんじゃ','いするぎじんじゃ')]:
            d=n.collect_niigata(Client({INDEX:menu(),A:result([row(glyph,kana) for kana in readings],2)}))
            self.assertEqual(len(d['facilities']),1)
            self.assertEqual(d['facilities'][0]['status'],'pending')
            self.assertEqual(d['entries'][0]['status'],'pending')
            self.assertTrue(d['facilities'][0]['review_occurrences'])
            self.assertEqual(d['facilities'][0]['review_occurrences'][0]['name_raw'],glyph)
            self.assertEqual(len(d['facilities'][0]['listing_occurrences']),2)

    def test_identity_conflicting_readings_remain_pending(self):
        d=n.collect_niigata(Client({INDEX:menu(),A:result([row(),row(kana='せきどうじんじゃ')],2)}))
        self.assertEqual(len(d['facilities']),1);self.assertEqual(d['entries'][0]['status'],'pending');self.assertTrue(d['facilities'][0]['source_conflicts'])
    def test_zero_results_valid_but_unknown_empty_body_not_complete(self):
        d=n.collect_niigata(Client({INDEX:menu(),A:result([],0)}));self.assertTrue(d['collection']['traversal_complete']);self.assertEqual(d['facilities'],[])
    def test_search_redirect_scope_change_stops_before_target_policy_or_request(self):
        for target in [B,A+'&page=2',A+'&num=20',INDEX,A+'&keyword=other']:
            with self.subTest(target=target):
                class Redirect:
                    def __init__(self):self.calls=[]
                    def _policy(self,url,**kwargs):self.calls.append(('policy',url))
                    def _raw(self,url,**kwargs):
                        self.calls.append(('raw',url))
                        return Page(url,302,{'location':target},b'','2026-11-09T00:00:00+00:00')
                c=Redirect()
                with self.assertRaises((ValueError,FetchError)):n._fetch(c,A)
                self.assertEqual(c.calls,[('policy',A),('raw',A)])

    def test_equivalent_defaults_query_order_and_index_redirects_are_allowed(self):
        for source,target,body in [(A,INDEX+'search.php?num=10&page=1&keyword=&area=15101',result([row()])),(INDEX,INDEX+'index.php',menu())]:
            class Redirect:
                def _policy(self,url,**kwargs):pass
                def _raw(self,url,**kwargs):
                    return Page(url,302,{'location':target},b'','2026-11-09T00:00:00+00:00') if url==source else page(url,body)
            self.assertEqual(n._fetch(Redirect(),source).url,target)

    def test_changed_final_response_scope_never_completes_requested_area(self):
        for target in [B,A+'&page=2',A+'&num=20',INDEX]:
            with self.subTest(target=target):
                class ChangedFinal(Client):
                    def fetch(self,url):
                        if url==A:return page(target,result([row()],1))
                        return super().fetch(url)
                d=n.collect_niigata(ChangedFinal({INDEX:menu()}))
                self.assertFalse(d['collection']['traversal_complete'])
                self.assertTrue(d['collection']['failed_pages'])
                self.assertEqual(d['facilities'],[])

    def test_cross_host_redirect_stops_before_fetch_and_refresh_intent(self):
        class Redirect:
            refresh_requested=True
            def __init__(self):self.calls=[]
            def _policy(self,url,**kwargs):self.calls.append(('policy',url,kwargs))
            def _raw(self,url,**kwargs):
                self.calls.append(('raw',url,kwargs));return Page(url,302,{'location':'https://evil.test/shrine_niigata/'},b'','2026-11-09T00:00:00+00:00')
        c=Redirect();d=n.collect_niigata(c)
        self.assertEqual(c.calls,[('policy',INDEX,{'refresh':True}),('raw',INDEX,{'refresh':True})]);self.assertFalse(d['collection']['traversal_complete'])

if __name__=='__main__':unittest.main()
