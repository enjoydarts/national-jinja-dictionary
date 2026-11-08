import tempfile
import unittest
from pathlib import Path
from njd.http import Client, FetchError

class FakeNetwork:
    def __init__(self, routes): self.routes=routes; self.calls=[]
    def __call__(self,url,timeout,user_agent):
        self.calls.append(url)
        result=self.routes[url]
        if isinstance(result,list): return result.pop(0)
        return result

class FetchTest(unittest.TestCase):
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
