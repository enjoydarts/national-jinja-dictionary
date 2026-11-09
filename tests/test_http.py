import tempfile
import unittest
from pathlib import Path
from njd.http import Client, FetchError, Page

class FakeNetwork:
    def __init__(self, routes): self.routes=routes; self.calls=[]
    def __call__(self,url,timeout,user_agent):
        self.calls.append(url)
        result=self.routes[url]
        if isinstance(result,list): return result.pop(0)
        return result

class FetchTest(unittest.TestCase):
    def test_reviewed_html_does_not_accept_explicit_login_or_challenge(self):
        origin='https://example.invalid'
        for headers,body in [({'content-type':'text/html'},b'<html><input type="password"></html>'),
                             ({'content-type':'text/html','cf-mitigated':'challenge'},b'<html>Checking browser</html>')]:
            with self.subTest(headers=headers),tempfile.TemporaryDirectory() as td:
                net=FakeNetwork({origin+'/robots.txt':(200,headers,body),origin+'/page':(200,{},b'facts')})
                c=Client(Path(td),interval=0,transport=net,reviewed_html_robots=[origin])
                with self.assertRaises(FetchError):c.fetch(origin+'/page')
                self.assertEqual(net.calls,[origin+'/robots.txt'])
    def test_reviewed_origin_parses_successful_html_robots_line_by_line(self):
        origin='https://example.invalid'
        with tempfile.TemporaryDirectory() as td:
            net=FakeNetwork({origin+'/robots.txt':(302,{'location':origin+'/'},b''),
                             origin+'/':(200,{'content-type':'text/html'},b'<html>Public home</html>'),
                             origin+'/page':(200,{},b'facts')})
            c=Client(Path(td),interval=0,transport=net,reviewed_html_robots=[origin])
            self.assertEqual(c.fetch(origin+'/page').body,b'facts')
            c.offline=True
            self.assertEqual(c.fetch(origin+'/page').body,b'facts')
            self.assertEqual(net.calls.count(origin+'/page'),1)

    def test_reviewed_html_preserves_disallow_and_stops_unparsed_directives(self):
        origin='https://example.invalid'
        for body in (b'<html>\nUser-agent: *\nDisallow: /private\n</html>',
                     b'<html>\nUser-agent: *<br>\nDisallow: /private<br>\n</html>',
                     b'<html><p>User-agent: *</p><p>Disallow: /private</p></html>'):
            with self.subTest(body=body),tempfile.TemporaryDirectory() as td:
                net=FakeNetwork({origin+'/robots.txt':(200,{'content-type':'text/html'},body),origin+'/private':(200,{},b'facts')})
                c=Client(Path(td),interval=0,transport=net,reviewed_html_robots=[origin])
                with self.assertRaises(FetchError):c.fetch(origin+'/private')
                self.assertEqual(net.calls,[origin+'/robots.txt'])

    def test_html_review_is_origin_scoped_and_does_not_allow_failed_policies(self):
        origin='https://example.invalid'
        for status in (401,403,429,503):
            with self.subTest(status=status),tempfile.TemporaryDirectory() as td:
                net=FakeNetwork({origin+'/robots.txt':(status,{},b'')})
                c=Client(Path(td),interval=0,retries=0,transport=net,reviewed_html_robots=[origin])
                with self.assertRaises(FetchError):c.fetch(origin+'/page')
                self.assertEqual(net.calls,[origin+'/robots.txt'])
        with tempfile.TemporaryDirectory() as td:
            net=FakeNetwork({origin+'/robots.txt':(302,{'location':'https://other.invalid/'},b''),
                             'https://other.invalid/':(200,{'content-type':'text/html'},b'<html>Other site</html>')})
            c=Client(Path(td),interval=0,transport=net,reviewed_html_robots=[origin])
            with self.assertRaises(FetchError):c.fetch(origin+'/page')
            self.assertNotIn(origin+'/page',net.calls)

    def test_html_review_configuration_requires_bare_origins(self):
        with tempfile.TemporaryDirectory() as td:
            for value in ('https://example.invalid/path','https://example.invalid/','https://user:secret@example.invalid'):
                with self.subTest(value=value),self.assertRaises(ValueError):
                    Client(Path(td),reviewed_html_robots=[value])
    def client(self,td,routes):
        net=FakeNetwork(routes)
        return Client(Path(td),interval=0,retries=1,transport=net),net
    def test_cache_and_offline_resume(self):
        with tempfile.TemporaryDirectory() as td:
            c,n=self.client(td,{'https://example.invalid/robots.txt':(404,{},b''),'https://example.invalid/page':(200,{'content-type':'text/html; charset=utf-8'},'根拠'.encode())})
            first=c.fetch('https://example.invalid/page'); second=c.fetch('https://example.invalid/page')
            self.assertEqual(first,second); self.assertEqual(len(n.calls),2)
            c.offline=True
            self.assertEqual(c.fetch('https://example.invalid/page').text,'根拠')
            with self.assertRaises(FetchError): c.fetch('https://example.invalid/missing')
    def test_robots_disallow_no_bypass(self):
        with tempfile.TemporaryDirectory() as td:
            c,n=self.client(td,{'https://example.invalid/robots.txt':(200,{},b'User-agent: *\nDisallow: /private')})
            with self.assertRaises(FetchError): c.fetch('https://example.invalid/private')
            self.assertEqual(len(n.calls),1)
    def test_html_robots_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            c,n=self.client(td,{'https://example.invalid/robots.txt':(200,{'content-type':'text/html'},b'<html>not rules</html>')})
            with self.assertRaises(FetchError): c.fetch('https://example.invalid/page')
    def test_transient_retry_but_not_access_denied(self):
        with tempfile.TemporaryDirectory() as td:
            c,n=self.client(td,{'https://example.invalid/robots.txt':(404,{},b''),'https://example.invalid/page':[(503,{'retry-after':'0'},b''),(200,{},b'ok')]})
            self.assertEqual(c.fetch('https://example.invalid/page').body,b'ok')
            self.assertEqual(n.calls.count('https://example.invalid/page'),2)
        with tempfile.TemporaryDirectory() as td:
            c,n=self.client(td,{'https://example.invalid/robots.txt':(404,{},b''),'https://example.invalid/page':(403,{},b'')})
            with self.assertRaises(FetchError): c.fetch('https://example.invalid/page')
            self.assertEqual(n.calls.count('https://example.invalid/page'),1)
    def test_redirect_target_robots_checked(self):
        with tempfile.TemporaryDirectory() as td:
            c,n=self.client(td,{'https://example.invalid/robots.txt':(404,{},b''),'https://example.invalid/page':(302,{'location':'https://other.invalid/private'},b''),'https://other.invalid/robots.txt':(200,{},b'User-agent: *\nDisallow: /')})
            with self.assertRaises(FetchError): c.fetch('https://example.invalid/page')
            self.assertNotIn('https://other.invalid/private',n.calls)
    def test_corrupt_cache_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            c,n=self.client(td,{'https://example.invalid/robots.txt':(404,{},b''),'https://example.invalid/page':(200,{},b'ok')})
            c.fetch('https://example.invalid/page')
            c._body_path('https://example.invalid/page').write_bytes(b'changed')
            c.offline=True
            with self.assertRaises(FetchError): c.fetch('https://example.invalid/page')

    def test_online_refreshes_expired_robots_before_cached_content(self):
        with tempfile.TemporaryDirectory() as td:
            c,n=self.client(td,{'https://example.invalid/robots.txt':(200,{},b'User-agent: *\nDisallow: /')})
            c._save(Page('https://example.invalid/robots.txt',404,{},b'','2020-01-01T00:00:00+00:00'))
            c._save(Page('https://example.invalid/page',200,{},b'old page','2020-01-01T00:00:00+00:00'))
            with self.assertRaises(FetchError): c.fetch('https://example.invalid/page')
            self.assertEqual(n.calls,['https://example.invalid/robots.txt'])

    def test_html_declared_charset_is_used_when_http_has_none(self):
        page=Page('https://example.invalid/',200,{'content-type':'text/html'},'<meta charset="shift_jis"><p>神社</p>'.encode('shift_jis'),'2026-11-08T00:00:00+00:00')
        self.assertIn('神社',page.text)

    def test_independent_hosts_do_not_share_network_lock(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Event
        entered_a=Event(); entered_b=Event(); release_a=Event()
        def transport(url,timeout,user_agent):
            if 'first.invalid' in url:
                entered_a.set();release_a.wait(3)
            else: entered_b.set()
            return 200,{},b'ok'
        with tempfile.TemporaryDirectory() as td:
            c=Client(Path(td),interval=0,transport=transport)
            with ThreadPoolExecutor(max_workers=2) as pool:
                first=pool.submit(c._network,'https://first.invalid/page')
                self.assertTrue(entered_a.wait(1))
                second=pool.submit(c._network,'https://second.invalid/page')
                try: independent=entered_b.wait(1)
                finally: release_a.set()
                first.result();second.result()
            self.assertTrue(independent,'one host must not hold the lock of another host')

    def test_readonly_json_post_has_body_specific_cache_and_obeys_robots(self):
        calls=[]
        def transport(url,timeout,user_agent,**kwargs):
            calls.append((url,kwargs))
            if url.endswith('/robots.txt'):return 404,{},b''
            return 200,{'content-type':'application/json'},kwargs['data']
        with tempfile.TemporaryDirectory() as td:
            c=Client(Path(td),interval=0,transport=transport)
            a=c.post_json('https://example.invalid/search',{'limit':-1})
            again=c.post_json('https://example.invalid/search',{'limit':-1})
            b=c.post_json('https://example.invalid/search',{'limit':10})
            self.assertEqual(a,again);self.assertNotEqual(a.body,b.body)
            self.assertEqual(a.url,'https://example.invalid/search')
            self.assertEqual(len(calls),3)
            c.offline=True
            self.assertEqual(c.post_json('https://example.invalid/search',{'limit':-1}),a)
            with self.assertRaises(FetchError):c.post_json('https://example.invalid/search',{'limit':1})
        with tempfile.TemporaryDirectory() as td:
            c,n=self.client(td,{'https://example.invalid/robots.txt':(200,{},b'User-agent: *\nDisallow: /search')})
            with self.assertRaises(FetchError):c.post_json('https://example.invalid/search',{})
            self.assertEqual(len(n.calls),1)

    def test_declared_web_shift_jis_preserves_cp932_extension_bytes(self):
        body='<meta charset="Shift_JIS"><p>神社まで1㎞</p>'.encode('cp932')
        page=Page('https://example.invalid/',200,{'content-type':'text/html'},body,'2026-11-09T00:00:00+09:00')
        self.assertIn('1㎞',page.text)
        self.assertEqual(page.body,body)
