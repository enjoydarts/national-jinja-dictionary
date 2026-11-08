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
    @property
    def sha256(self): return hashlib.sha256(self.body).hexdigest()
    @property
    def text(self):
        match=re.search(r'charset=([^;\s]+)',self.headers.get('content-type',''),re.I)
        encoding=match.group(1).strip('"\'') if match else 'utf-8'
        return self.body.decode(encoding,errors='strict')

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl): return None

def request(url,timeout,user_agent):
    opener=build_opener(NoRedirect())
    try:
        response=opener.open(Request(url,headers={'User-Agent':user_agent}),timeout=timeout)
    except HTTPError as exc: response=exc
    with response:
        body=response.read(8*1024*1024+1)
        if len(body)>8*1024*1024: raise FetchError('page exceeds 8 MiB limit')
        return response.status,{k.lower():v for k,v in response.headers.items()},body

class Client:
    def __init__(self,cache_dir,*,interval=2.0,timeout=30,retries=2,offline=False,transport=None):
        self.cache=Path(cache_dir); self.cache.mkdir(parents=True,exist_ok=True)
        self.interval=max(0,interval); self.timeout=timeout; self.retries=retries
        self.offline=offline; self.transport=transport or request
        self.user_agent='NationalJinjaDictionary/0.1 (+https://github.com/enjoydarts/national-jinja-dictionary)'
        self.delays={}
    def _key(self,url): return hashlib.sha256(url.encode()).hexdigest()
    def _body_path(self,url): return self.cache/(self._key(url)+'.body')
    def _meta_path(self,url): return self.cache/(self._key(url)+'.json')
    def _load(self,url):
        meta=self._meta_path(url)
        if not meta.exists(): return None
        try:
            d=json.loads(meta.read_text()); body=self._body_path(url).read_bytes()
            if hashlib.sha256(body).hexdigest()!=d['sha256'] or d['url']!=url:
                raise FetchError('cache integrity mismatch: '+url)
            return Page(url,d['status'],d['headers'],body,d['fetched_at'])
        except (OSError,ValueError,KeyError) as exc: raise FetchError('invalid cache: '+url) from exc
    def _save(self,page):
        body=self._body_path(page.url); tmp=body.with_suffix('.body.tmp')
        tmp.write_bytes(page.body); tmp.replace(body)
        write_json(self._meta_path(page.url),dict(url=page.url,status=page.status,
            headers=page.headers,sha256=page.sha256,fetched_at=page.fetched_at))
    def _network(self,url):
        # A cross-process lock plus persisted last-request time respects spacing
        # across restarts and parallel collectors, including failed responses.
        lock=self.cache/'request.lock'
        with lock.open('a+b') as stream:
            self._lock(stream)
            state_path=self.cache/'last_requests.json'
            state=json.loads(state_path.read_text()) if state_path.exists() else {}
            origin=self._origin(url)
            gap=max(self.interval,self.delays.get(origin,0))
            wait=state.get(origin,0)+gap-time.time()
            if wait>60: raise FetchError('required host interval exceeds this run; resume later')
            if wait>0: time.sleep(wait)
            try: return self.transport(url,self.timeout,self.user_agent)
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
    def _raw(self,url,*,refresh=False):
        cached=self._load(url)
        if cached and not refresh: return cached
        if self.offline: raise FetchError('offline cache miss: '+url)
        for attempt in range(self.retries+1):
            try: status,headers,body=self._network(url)
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
            page=Page(url,status,headers,body,datetime.now(timezone.utc).isoformat())
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
        if 'text/html' in robot.headers.get('content-type','').lower() or robot.text.lstrip().startswith('<'):
            raise FetchError('robots returned HTML; policy unknown')
        policy=RobotFileParser(); policy.parse(robot.text.splitlines())
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
