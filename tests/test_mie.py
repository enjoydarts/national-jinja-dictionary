"""Synthetic independent committee HTML fixtures; no acquired content/images."""
import unittest
from njd.adapters import mie as m
from njd.http import Page,FetchError

BASE='https://kyoka.mie-jinjacho.or.jp'
INDEX='http://kyoka.mie-jinjacho.or.jp/shrine/'

def page(url,text):return Page(url,200,{'content-type':'text/html; charset=utf-8'},text.encode(),'2026-11-09T00:00:00+00:00')
def detail(name='一宮神社',kana='いっきゅうじんじゃ',code='4220032',address='名張市夏見字坊垣 3375-1'):
    return f'<div class="shrine_detail"><h2>{name}<span class="furigana"> – {kana} –</span></h2><table class="table_03"><tr><th>神社コード</th><td>{code}</td></tr><tr><th>鎮座地</th><td>{address}</td></tr></table></div>'
def index(items,next_url=None):
    return ''.join(f'<div class="post"><h2><a href="{url}">{name}</a></h2></div>' for name,url in items)+(f'<a href="{next_url}">« 古い記事</a>' if next_url else '')
class Client:
    def __init__(self,pages):self.pages=pages;self.calls=[]
    def fetch(self,url):
        self.calls.append(url)
        if url not in self.pages:raise FetchError('missing fixture')
        return self.pages[url] if isinstance(self.pages[url],Page) else page(url,self.pages[url])

class MieTests(unittest.TestCase):
    def test_literal_full_name_kana_address_native_and_provenance(self):
        r=m.parse_detail(page(BASE+'/shrine/one/',detail()))
        self.assertEqual((r['name'],r['reading_raw'],r['address'],r['source_id']),('一宮神社','いっきゅうじんじゃ','名張市夏見字坊垣 3375-1','4220032'))
        self.assertIn('3375-1',r['evidence']);self.assertEqual(r['url'],BASE+'/shrine/one/')
    def test_layout_break_inside_identity_label_is_not_missing_code(self):
        r=m.parse_detail(page(BASE+'/shrine/one/',detail().replace('神社コード','神社<br>コード')))
        self.assertEqual(r['source_id'],'4220032')
    def test_partial_kana_and_parenthetical_label_not_inferred(self):
        for kana,name in [('いっきゅう','一宮神社'),('くにつじんじゃ','國津神社（上比奈知）'),('','一宮神社')]:
            r=m.parse_detail(page(BASE+'/shrine/one/',detail(name=name,kana=kana)))
            self.assertEqual(r['reading_raw'],'');self.assertEqual(r['source_reading_raw'],kana)
    def test_unknown_duplicate_fields_and_missing_identity_fail(self):
        for body in ['<p>maintenance</p>',detail(code=''),detail().replace('</table>','<tr><th>鎮座地</th><td>別町1</td></tr></table>')]:
            with self.assertRaises(ValueError):m.parse_detail(page(BASE+'/shrine/one/',body))
    def test_actual_posts_pagination_only_and_host_confinement(self):
        p=page(BASE+'/shrine/',index([('一宮神社','/shrine/one/')],'/shrine/page/2/')+'<a href="/shrine/side/">sidebar</a>')
        links,next_page=m.index_links(p);self.assertEqual(links,[(BASE+'/shrine/one/','一宮神社')]);self.assertEqual(next_page,BASE+'/shrine/page/2/')
        with self.assertRaises(ValueError):m.index_links(page(INDEX,index([('bad','https://evil.test/shrine/one/')])) )
    def test_traversal_limit_failure_and_loops_are_partial(self):
        a=BASE+'/shrine/one/';b=BASE+'/shrine/two/';n=BASE+'/shrine/page/2/'
        pages={INDEX:index([('一宮神社',a)],n),a:detail(),n:index([('相楽神社',b)]),b:detail('相楽神社','さがらじんじゃ','4220031','名張市赤目町相楽 361-1')}
        client=Client(pages);d=m.collect_mie(client,limit=1)
        self.assertEqual(len(d['facilities']),1);self.assertFalse(d['collection']['traversal_complete']);self.assertNotIn(n,client.calls)
        d=m.collect_mie(Client(pages));self.assertTrue(d['collection']['traversal_complete']);self.assertEqual(len(d['entries']),2)
        pages[n]=index([('相楽神社',b)],INDEX);self.assertFalse(m.collect_mie(Client(pages))['collection']['traversal_complete'])
        del pages[b];d=m.collect_mie(Client(pages));self.assertTrue(d['collection']['failed_pages'])
    def test_native_identity_collision_and_same_name_different_codes(self):
        a=BASE+'/shrine/one/';b=BASE+'/shrine/two/'
        pages={INDEX:index([('一宮神社',a),('一宮神社',b)]),a:detail(),b:detail(code='4220033',address='名張市夏見字坊垣 999')}
        self.assertEqual(len(m.collect_mie(Client(pages))['facilities']),2)
        pages[b]=detail(code='4220032',address='名張市夏見字坊垣 999')
        d=m.collect_mie(Client(pages));self.assertEqual(len(d['facilities']),1);self.assertEqual(d['entries'][0]['status'],'pending')
    def test_cross_host_redirect_stops_before_target_request(self):
        class RedirectClient:
            def __init__(self):self.calls=[]
            def _policy(self,url,**kwargs):self.calls.append(('policy',url))
            def _raw(self,url,**kwargs):
                self.calls.append(('request',url))
                return Page(url,302,{'location':'https://evil.test/shrine/'},b'', '2026-11-09T00:00:00+00:00')
        client=RedirectClient();d=m.collect_mie(client)
        self.assertFalse(d['collection']['traversal_complete'])
        self.assertEqual(client.calls,[('policy',INDEX),('request',INDEX)])
        self.assertTrue(d['collection']['failed_pages'])
    def test_partial_raw_collision_same_code_is_pending(self):
        a=BASE+'/shrine/one/';b=BASE+'/shrine/two/'
        d=m.collect_mie(Client({INDEX:index([('一宮神社',a),('一宮神社',b)]),a:detail(kana='いっきゅう'),b:detail(kana='いちのみや')}))
        self.assertEqual(d['entries'][0]['status'],'pending')
        self.assertEqual(len(d['facilities'][0]['source_reading_conflicts']),2)

    def test_refresh_intent_reaches_policy_and_raw_requests(self):
        class RefreshClient:
            def __init__(self,flag):self.refresh_requested=flag;self.flags=[]
            def _policy(self,url,**kwargs):self.flags.append(('policy',kwargs.get('refresh')))
            def _raw(self,url,**kwargs):
                self.flags.append(('raw',kwargs.get('refresh')))
                return page(url,index([('一宮神社','/shrine/one/')]))
        for flag in [False,True]:
            client=RefreshClient(flag);m._fetch(client,INDEX)
            self.assertEqual(client.flags,[('policy',flag),('raw',flag)])

    def test_actual_percent_escape_spelling_and_http_start_are_preserved(self):
        url=BASE+'/shrine/%e4%b8%80%e5%ae%ae/'
        links,_=m.index_links(page(INDEX,index([('一宮神社',url)])))
        self.assertEqual(links[0][0],url)
        client=Client({'http://kyoka.mie-jinjacho.or.jp/shrine/':index([('一宮神社',url)]),url:detail()})
        d=m.collect_mie(client)
        self.assertEqual(client.calls[0],'http://kyoka.mie-jinjacho.or.jp/shrine/')
        self.assertEqual(d['facilities'][0]['listing_url'],url)

    def test_explicit_sha_endings_and_halfwidth_kana_are_mechanical(self):
        for name,raw,want in [('山神社','やまがみしゃ','やまがみしゃ'),('諏訪神社','すわしゃ','すわしゃ'),('一宮神社','ｲｯｷｭｳｼﾞﾝｼﾞｬ','いっきゅうじんじゃ')]:
            url=BASE+'/shrine/one/'
            d=m.collect_mie(Client({INDEX:index([(name,url)]),url:detail(name=name,kana=raw)}))
            self.assertEqual(d['entries'][0]['reading'],want)
            self.assertEqual(d['entries'][0]['reading_raw'],raw)
        for raw in ['いっきゅう じんじゃ','いっきゅうじんじゃ（通称）']:
            self.assertEqual(m.parse_detail(page(BASE+'/shrine/one/',detail(kana=raw)))['reading_raw'],'')

    def test_partial_source_reading_changes_fingerprint_without_enabling_output(self):
        from njd.validation import validate
        datasets=[];url=BASE+'/shrine/one/'
        for raw in ['いっきゅう','いちのみや']:
            d=m.collect_mie(Client({INDEX:index([('一宮神社',url)]),url:detail(kana=raw)}))
            e=d['entries'][0]
            self.assertEqual(e['reading_raw'],raw)
            self.assertEqual((e['status'],e['reading']),('pending',''))
            self.assertEqual(d['facilities'][0]['status'],'verified')
            self.assertEqual([p for p in validate(d) if p.get('severity')=='error'],[])
            datasets.append(d)
        self.assertEqual(datasets[0]['facilities'][0]['id'],datasets[1]['facilities'][0]['id'])
        self.assertNotEqual(datasets[0]['entries'][0]['source_hash'],datasets[1]['entries'][0]['source_hash'])

    def test_any_index_name_mismatch_remains_pending_in_both_orders(self):
        from njd.validation import validate
        a=BASE+'/shrine/one/';b=BASE+'/shrine/two/'
        for items in [[('一宮神社',a),('別名神社',b)],[('別名神社',b),('一宮神社',a)],[('一宮神社',a),('別名神社',a)],[('別名神社',a),('一宮神社',a)]]:
            with self.subTest(items=items):
                d=m.collect_mie(Client({INDEX:index(items),a:detail(),b:detail()}))
                f=d['facilities'][0];e=d['entries'][0]
                self.assertEqual((f['status'],e['status']),('pending','pending'))
                self.assertIn('index',f['review_reason'])
                self.assertEqual({r['name_raw'] for r in f['index_occurrences']},{'一宮神社','別名神社'})
                self.assertEqual(len(f['index_occurrences']),2)
                for r in f['index_occurrences']:
                    self.assertEqual(r['url'],INDEX);self.assertEqual(len(r['page_hash']),64)
                    self.assertEqual(r['fetched_at'],'2026-11-09T00:00:00+00:00')
                    self.assertIn(r['href'],[a,b])
                self.assertEqual([p for p in validate(d) if p.get('severity')=='error'],[])

    def test_http_scheme_not_silently_rewritten_and_partial_raw_survives(self):
        u='http://kyoka.mie-jinjacho.or.jp/shrine/one/'
        pages={INDEX:index([('一宮神社',u)]),u:page(BASE+'/shrine/one/',detail(kana='いっきゅう'))}
        client=Client(pages);d=m.collect_mie(client)
        self.assertIn(u,client.calls);self.assertEqual(d['entries'][0]['reading_raw'],'いっきゅう');self.assertEqual(d['entries'][0]['source_reading_raw'],'いっきゅう');self.assertEqual(d['entries'][0]['status'],'pending')

if __name__=='__main__':unittest.main()
