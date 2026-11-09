"""Low-rate cached HTTP with robots enforcement; no access-control bypass."""
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import hashlib
import json
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.robotparser import RobotFileParser
from njd.storage import write_json

class FetchError(RuntimeError): pass

@dataclass(frozen=True)
class Page:
    url: str
    status: int
    headers: dict
    body: bytes
    fetched_at: str
    request_method: str='GET'
    request_body_hash: str | None=None
    @property
    def cache_identity(self):
        return self.url if self.request_method=='GET' else self.request_method+'\n'+self.url+'\n'+(self.request_body_hash or '')
    @property
    def sha256(self): return hashlib.sha256(self.body).hexdigest()
    @property
    def text(self):
        match=re.search(r'charset=([^;\s]+)',self.headers.get('content-type',''),re.I)
        if match:
            encoding=match.group(1).strip('"\'')
        elif self.body.startswith(b'\xef\xbb\xbf'):
            encoding='utf-8-sig'
        elif self.body.startswith((b'\xff\xfe',b'\xfe\xff')):
            encoding='utf-16'
        else:
            # Use explicit HTML declarations, never a guessed Japanese codec.
            meta=re.search(br'<meta\b[^>]*\bcharset\s*=\s*[\x22\x27]?\s*([a-zA-Z0-9_.-]+)',self.body[:8192],re.I)
            encoding=meta.group(1).decode('ascii') if meta else 'utf-8'
        # WHATWG Encoding names/labels use the Windows-compatible Shift_JIS
        # repertoire on the web; preserve extension bytes instead of replacing.
        # https://encoding.spec.whatwg.org/#names-and-labels
        if encoding.strip().lower().replace('_','-') in ('shift-jis','windows-31j','ms932','x-sjis','csshiftjis','sjis','ms-kanji'):
            encoding='cp932'
        return self.body.decode(encoding,errors='strict')

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl): return None

def request(url,timeout,user_agent,*,method='GET',data=None,content_type=None):
    opener=build_opener(NoRedirect())
    try:
        headers={'User-Agent':user_agent}
        if content_type:headers['Content-Type']=content_type
        response=opener.open(Request(url,headers=headers,data=data,method=method),timeout=timeout)
    except HTTPError as exc: response=exc
    with response:
        body=response.read(8*1024*1024+1)
        if len(body)>8*1024*1024: raise FetchError('page exceeds 8 MiB limit')
        return response.status,{k.lower():v for k,v in response.headers.items()},body

class Client:
    def __init__(self,cache_dir,*,interval=2.0,timeout=30,retries=2,offline=False,transport=None,reviewed_html_robots=()):
        self.cache=Path(cache_dir); self.cache.mkdir(parents=True,exist_ok=True)
        self.interval=max(0,interval); self.timeout=timeout; self.retries=retries
        self.offline=offline; self.transport=transport or request
        self.user_agent='NationalJinjaDictionary/0.1 (+https://github.com/enjoydarts/national-jinja-dictionary)'
        self.delays={}
        origins=set()
        for origin in reviewed_html_robots:
            try:valid=isinstance(origin,str) and self._origin(origin)==origin
            except FetchError:valid=False
            if not valid:raise ValueError('reviewed HTML robots configuration requires bare origins')
            origins.add(origin)
        self.reviewed_html_robots=frozenset(origins)
    def _key(self,url): return hashlib.sha256(url.encode()).hexdigest()
    def _body_path(self,url,cache_identity=None): return self.cache/(self._key(cache_identity or url)+'.body')
    def _meta_path(self,url,cache_identity=None): return self.cache/(self._key(cache_identity or url)+'.json')
    def _load(self,url,cache_identity=None):
        meta=self._meta_path(url,cache_identity)
        if not meta.exists(): return None
        try:
            d=json.loads(meta.read_text()); body=self._body_path(url,cache_identity).read_bytes()
            if hashlib.sha256(body).hexdigest()!=d['sha256'] or d['url']!=url:
                raise FetchError('cache integrity mismatch: '+url)
            return Page(url,d['status'],d['headers'],body,d['fetched_at'],d.get('request_method','GET'),d.get('request_body_hash'))
        except (OSError,ValueError,KeyError) as exc: raise FetchError('invalid cache: '+url) from exc
    def _save(self,page):
        body=self._body_path(page.url,page.cache_identity); tmp=body.with_suffix('.body.tmp')
        tmp.write_bytes(page.body); tmp.replace(body)
        write_json(self._meta_path(page.url,page.cache_identity),dict(url=page.url,status=page.status,
            headers=page.headers,sha256=page.sha256,fetched_at=page.fetched_at,request_method=page.request_method,request_body_hash=page.request_body_hash))
    def _network(self,url,*,method='GET',data=None,content_type=None):
        # A cross-process lock plus persisted last-request time respects spacing
        # across restarts and parallel collectors, including failed responses.
        origin=self._origin(url)
        host_key=self._key(origin)
        lock=self.cache/('host-'+host_key+'.lock')
        with lock.open('a+b') as stream:
            self._lock(stream)
            state_path=self.cache/'hosts'/(host_key+'.json')
            if state_path.exists(): state=json.loads(state_path.read_text())
            else:
                legacy=self.cache/'last_requests.json'
                state=json.loads(legacy.read_text()) if legacy.exists() else {}
            gap=max(self.interval,self.delays.get(origin,0))
            wait=state.get(origin,0)+gap-time.time()
            if wait>60: raise FetchError('required host interval exceeds this run; resume later')
            if wait>0: time.sleep(wait)
            try:
                if method=='GET':return self.transport(url,self.timeout,self.user_agent)
                return self.transport(url,self.timeout,self.user_agent,method=method,data=data,content_type=content_type)
            finally:
                state[origin]=time.time(); write_json(state_path,state)
    @staticmethod
    def _lock(stream):
        try:
            import fcntl
            fcntl.flock(stream.fileno(),fcntl.LOCK_EX)
        except ImportError as exc:
            raise FetchError('collection requires POSIX file locking; offline build remains portable') from exc
    @staticmethod
    def _origin(url):
        parsed=urlsplit(url)
        if parsed.scheme not in ('http','https') or not parsed.hostname or parsed.username or parsed.password:
            raise FetchError('invalid public HTTP URL')
        return parsed.scheme+'://'+parsed.netloc
    def _raw(self,url,*,refresh=False,method='GET',request_data=None,content_type=None):
        body_hash=hashlib.sha256(request_data or b'').hexdigest() if method!='GET' else None
        cache_identity=url if method=='GET' else method+'\n'+url+'\n'+body_hash
        cached=self._load(url,cache_identity)
        if cached and not refresh: return cached
        if self.offline: raise FetchError('offline cache miss: '+url)
        for attempt in range(self.retries+1):
            try:
                if method=='GET':status,headers,body=self._network(url)
                else:status,headers,body=self._network(url,method=method,data=request_data,content_type=content_type)
            except (URLError,TimeoutError,ConnectionError) as exc:
                if attempt==self.retries: raise FetchError(str(exc)) from exc
                time.sleep(2**attempt); continue
            if status==429 or 500<=status<=599:
                if attempt==self.retries: raise FetchError(f'HTTP {status}: {url}')
                retry=headers.get('retry-after','')
                if retry:
                    try: delay=float(retry)
                    except ValueError:
                        try: delay=parsedate_to_datetime(retry).timestamp()-time.time()
                        except (ValueError,TypeError,OverflowError): raise FetchError('invalid Retry-After')
                else: delay=2**attempt
                if delay>60: raise FetchError('Retry-After requires later resume')
                time.sleep(max(0,delay)); continue
            page=Page(url,status,headers,body,datetime.now(timezone.utc).isoformat(),method,body_hash)
            # Do not cache denied/error responses as successful content.
            if status in (200,301,302,303,307,308,404,410): self._save(page)
            return page
        raise FetchError('retry exhausted')
    def _policy(self,url,refresh=False):
        origin=self._origin(url); robot_url=origin+'/robots.txt'
        cached=self._load(robot_url)
        if cached and not self.offline:
            try: age=time.time()-datetime.fromisoformat(cached.fetched_at).timestamp()
            except (ValueError,TypeError): raise FetchError('invalid robots cache timestamp')
            refresh=refresh or age>=86400
        robot=self._raw(robot_url,refresh=refresh)
        for _ in range(5):
            if robot.status not in (301,302,303,307,308): break
            target=urljoin(robot.url,robot.headers.get('location',''))
            self._origin(target)
            robot=self._raw(target,refresh=refresh)
        if robot.status in (404,410): return
        if robot.status!=200: raise FetchError(f'robots status unknown: {robot.status}')
        text=robot.text
        if robot.headers.get('cf-mitigated','').lower()=='challenge':
            raise FetchError('robots response requires a browser challenge')
        if 'text/html' in robot.headers.get('content-type','').lower() or text.lstrip().startswith('<'):
            if origin not in self.reviewed_html_robots or self._origin(robot.url) not in self.reviewed_html_robots:
                raise FetchError('robots returned HTML; policy unknown')
            if re.search(r'<input\b[^>]*\btype\s*=\s*[\"\']?password\b',text,re.I):
                raise FetchError('robots response contains an authentication form')
            directive=r'(?:user-agent|allow|disallow|crawl-delay|request-rate)\s*:'
            for line in text.splitlines():
                candidate=line.split('#',1)[0]
                if re.search(r'\b'+directive,candidate,re.I):
                    if not re.match(r'^\s*'+directive,candidate,re.I) or '<' in candidate or '>' in candidate:
                        raise FetchError('HTML robots directives are not line-parseable')
        policy=RobotFileParser(); policy.parse(text.splitlines())
        if not policy.can_fetch(self.user_agent,url): raise FetchError('robots disallows: '+url)
        crawl=policy.crawl_delay(self.user_agent)
        rate=policy.request_rate(self.user_agent)
        self.delays[origin]=max(crawl or 0,(rate.seconds/rate.requests) if rate else 0)
    def fetch(self,url,*,refresh=False):
        self._origin(url)
        for _ in range(6):
            self._policy(url,refresh=refresh)
            page=self._raw(url,refresh=refresh)
            if page.status in (301,302,303,307,308):
                target=page.headers.get('location')
                if not target: raise FetchError('redirect without location')
                url=urljoin(url,target); continue
            if page.status!=200: raise FetchError(f'HTTP {page.status}: {url}')
            return page
        raise FetchError('too many redirects')

    def post_json(self,url,payload,*,refresh=False):
        """Only for documented read-only JSON search endpoints used by the UI.

        Responses are keyed by URL, method and body hash. Source URLs remain
        real URLs; no synthetic query strings are invented for cache keys.
        Redirects are not followed with a POST body.
        """
        self._origin(url);self._policy(url,refresh=refresh)
        body=json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
        page=self._raw(url,refresh=refresh,method='POST',request_data=body,content_type='application/json')
        if page.status!=200:raise FetchError(f'HTTP {page.status}: {url}; JSON search POST not redirected')
        return page
