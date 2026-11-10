"""Recorded official-detail URLs and synthetic table fixtures; no network."""
import copy
from pathlib import Path
import tempfile
import unittest
from njd import agency_details as a
from njd.http import Page, FetchError
from njd.storage import load_dataset, write_json

URL='https://www.shimane-jinjacho.or.jp/matsue/a4fa34bf6aebd1e95ea2b7af1b9506a93f411fef.html'
def html(name='加賀神社',reading='かがじんじゃ',address='松江市島根町加賀1490番地'):
    return '<table class="address-detail"><tr><td>神社コード</td><td>02029</td></tr><tr><td>神社名（正称)</td><td>'+name+'</td></tr><tr><td>ふりがな</td><td>'+reading+'</td></tr><tr><td>神社名（別称)</td><td>別称</td></tr><tr><td>ふりがな</td><td>べっしょう</td></tr><tr><td>主祭神</td><td>支佐加比売命</td></tr><tr><td>ふりがな</td><td>きさかひめのみこと</td></tr><tr><td>鎮座地</td><td>'+address+'</td></tr></table>'
def page(body,url=URL):return Page(url,200,{'content-type':'text/html'},body.encode(),'2026-11-09T00:00:00+00:00')
class FixtureClient:
    def __init__(self,pages):self.pages=pages;self.calls=[];self.refreshes=[]
    def fetch(self,url,refresh=False):
        self.calls.append(url);self.refreshes.append(refresh)
        if url not in self.pages:raise FetchError('unavailable')
        return page(self.pages[url],url)

class AgencyDetailsTests(unittest.TestCase):
    def setup_data(self,root,count=1):
        fs=[];es=[]
        for i in range(count):
            fs.append(dict(id='f'+str(i),listed_name='加賀神社',name_raw='加賀神社',address='松江市島根町加賀1490番地',prefecture='島根県',prefecture_code='32',status='verified',listing_url='https://www.shimane-jinjacho.or.jp/matsue/index.html',native_source_id=URL if i==0 else URL.replace('/matsue/a','/matsue/'+str(i))))
            es.append(dict(id='e'+str(i),facility_id='f'+str(i),reading_raw='',source_hash='hash'+str(i),status='pending',surface='加賀神社'))
        value=dict(collection=dict(source_key='shimane',authority_status='confirmed'),facilities=fs,entries=es)
        write_json(root/'sources/shimane.json',value);return value
    def test_primary_name_reading_address_and_code_are_literal(self):
        ref=a.parse_detail(page(html()),'加賀神社')
        self.assertEqual(ref['reading_raw'],'かがじんじゃ');self.assertEqual(ref['agency_code'],'02029')
        self.assertEqual(ref['address_raw'],'松江市島根町加賀1490番地');self.assertEqual(ref['source_kind'],'agency')
        self.assertIn('正称',ref['locator']);self.assertIn('かがじんじゃ',ref['excerpt'])
    def test_malformed_duplicate_and_alias_deity_readings_cannot_substitute(self):
        bodies=[html(reading=''),html(reading='かが'),html(name='別神社'),html(reading='かがじんじゃ、かかじんじゃ'),html().replace('<td>ふりがな</td><td>かがじんじゃ</td>','<td>主祭神</td><td>かがじんじゃ</td>'),html()+html(),html().replace('<td>02029</td>','<td></td>'),html().replace('<td>鎮座地</td>','<td>所在地</td>')]
        for body in bodies:
            with self.subTest(body=body),self.assertRaises(ValueError):a.parse_detail(page(body),'加賀神社')
    def test_batch_progresses_resume_hash_drift_and_preserves_canonical(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);d=self.setup_data(root/'data',2);before=(root/'data/sources/shimane.json').read_bytes()
            write_json(root/'data/corrections.json',{'entries':{'e0':{'status':'verified','references':[{'source_kind':'encyclopedia'}]}}})
            client=FixtureClient({f['native_source_id']:html() for f in d['facilities']})
            first=a.research(root/'data',root/'state',client,limit=1)
            self.assertEqual(first['unvisited'],1);self.assertFalse(first['complete'])
            self.assertIn('e0',load_dataset(root/'state/proposals.json')['entries'])
            second=a.research(root/'data',root/'state',client,limit=1)
            self.assertTrue(second['complete']);self.assertEqual(second['proposals'],2)
            self.assertEqual((root/'data/sources/shimane.json').read_bytes(),before)
            client.calls.clear();a.research(root/'data',root/'state',client);self.assertEqual(client.calls,[])
            d['entries'][0]['source_hash']='changed';write_json(root/'data/sources/shimane.json',d)
            a.research(root/'data',root/'state',client);self.assertEqual(client.calls,[URL])
    def test_failed_retried_address_conflicts_pending_and_foreign_url_not_fetched(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);d=self.setup_data(root/'data');client=FixtureClient({})
            self.assertFalse(a.research(root/'data',root/'state',client)['complete'])
            client.pages[URL]=html(address='松江市島根町加賀1491番地')
            result=a.research(root/'data',root/'state',client)
            self.assertEqual(result['pending'],1);self.assertEqual(result['proposals'],0)
            d['facilities'][0]['native_source_id']='https://evil.example/detail';write_json(root/'data/sources/shimane.json',d)
            client.calls.clear();result=a.research(root/'data',root/'state',client)
            self.assertEqual(client.calls,[]);self.assertEqual(result['pending'],1)
    def test_reviews_decisions_and_quarantine_excluded_but_corrections_retained(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);d=self.setup_data(root/'data',4)
            write_json(root/'data/reviews.json',{'entries':{'e0':{}}});write_json(root/'data/decisions.json',{'e1':{}})
            d['entries'][2]['identity_review_required']=True;write_json(root/'data/sources/shimane.json',d)
            write_json(root/'data/corrections.json',{'entries':{'e3':{}}})
            self.assertEqual([t['entry']['id'] for t in a.targets(root/'data')],['e3'])
    def test_recheck_uses_cache_contract_not_forced_refresh(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.setup_data(root/'data');client=FixtureClient({URL:html()})
            a.research(root/'data',root/'state',client);client.calls.clear();client.refreshes.clear()
            self.assertEqual(a.research(root/'data',root/'state',client,recheck=True)['proposals'],1)
            self.assertEqual(client.calls,[URL]);self.assertEqual(client.refreshes,[False])
    def test_unvisited_advances_before_retrying_persistent_failure_with_small_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);d=self.setup_data(root/'data',2);second=d['facilities'][1]['native_source_id']
            client=FixtureClient({second:html()})
            self.assertEqual(a.research(root/'data',root/'state',client,limit=1)['errors'],1)
            result=a.research(root/'data',root/'state',client,limit=1)
            self.assertEqual(result['unvisited'],0);self.assertEqual(result['proposals'],1)
            self.assertEqual(client.calls,[URL,second])
    def test_first_proposal_is_written_before_second_record_is_fetched(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);d=self.setup_data(root/'data',2);second=d['facilities'][1]['native_source_id']
            class ObservingClient(FixtureClient):
                def fetch(inner,url,**kwargs):
                    if url==second:self.assertIn('e0',load_dataset(root/'state/proposals.json')['entries'])
                    return super().fetch(url,**kwargs)
            self.assertEqual(a.research(root/'data',root/'state',ObservingClient({URL:html(),second:html()}))['proposals'],2)

SINDEX='https://www.shiga-jinjacho.jp/ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-search.html?mode:search=1&view:term=100'
SDETAIL='https://www.shiga-jinjacho.jp/ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-detail.html?mode:view=1&view:oid=7'
def shiga_index(href='ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-detail.html?mode:view=1&amp;view:oid=7'):
    return '<base href="https://www.shiga-jinjacho.jp/"><a class="news_title" href="'+href+'">〔大津〕 例神社</a><br><span>〒5200000 大津市例町</span>'
def shiga_detail(reading='レイジンジャ'):
    return '<div class="j_title">例神社 （'+reading+'） ～（例の宮）</div><table><tr><td>鎮座地</td><td>滋賀県大津市例町１</td></tr></table>'

class ShigaAgencyTests(unittest.TestCase):
    def setup_data(self,root):
        f=dict(id='f0',listed_name='例神社',name_raw='例神社',address='大津市例町',prefecture='滋賀県',prefecture_code='25',status='verified',listing_url=SINDEX,native_source_id='7')
        e=dict(id='e0',facility_id='f0',reading_raw='',source_hash='hash0',status='pending',surface='例神社')
        write_json(root/'sources/shiga.json',dict(collection=dict(source_key='shiga',authority_status='confirmed'),facilities=[f],entries=[e]))

    def test_actual_base_href_native_and_literal_full_reading(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.setup_data(root/'data');before=(root/'data/sources/shiga.json').read_bytes()
            result=a.research(root/'data',root/'state',FixtureClient({SINDEX:shiga_index(),SDETAIL:shiga_detail()}),source='shiga')
            self.assertEqual(result['proposals'],1)
            c=load_dataset(root/'state/proposals.json')['entries']['e0'];ref=c['references'][0]
            self.assertEqual(c['changes'],{'reading':'れいじんじゃ'})
            self.assertEqual((ref['name_raw'],ref['reading_raw'],ref['alias_display_raw']),('例神社','レイジンジャ','例の宮'))
            self.assertEqual(ref['index_proof']['source_id'],'7')
            self.assertEqual((root/'data/sources/shiga.json').read_bytes(),before)

    def test_stem_is_preserved_as_reference_but_never_completed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.setup_data(root/'data');client=FixtureClient({SINDEX:shiga_index(),SDETAIL:shiga_detail('レイ')})
            result=a.research(root/'data',root/'state',client,source='shiga')
            self.assertEqual((result['proposals'],result['pending']),(0,1))
            saved=load_dataset(root/'state/state/progress.json')['entries']['e0']
            self.assertEqual(saved['reference']['reading_raw'],'レイ')
            client.calls.clear();a.research(root/'data',root/'state',client,source='shiga');self.assertEqual(client.calls,[])

    def test_combined_names_cannot_be_verified_by_the_final_suffix_alone(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.setup_data(root/'data')
            data=load_dataset(root/'data/sources/shiga.json')
            name='例天神社・若宮八幡宮'
            data['facilities'][0].update(listed_name=name,name_raw=name)
            data['entries'][0]['surface']=name
            write_json(root/'data/sources/shiga.json',data)
            client=FixtureClient({SINDEX:shiga_index().replace('例神社',name),
                                  SDETAIL:shiga_detail('レイテンワカミヤ').replace('例神社',name)})
            result=a.research(root/'data',root/'state',client,source='shiga')
            self.assertEqual((result['proposals'],result['pending']),(0,1))
            saved=load_dataset(root/'state/state/progress.json')['entries']['e0']
            self.assertEqual(saved['reference']['reading_raw'],'レイテンワカミヤ')
            self.assertEqual(saved['reference']['reading_scope'],'partial_or_absent')

    def test_unknown_link_host_native_and_index_address_cannot_bind(self):
        for index in [shiga_index(SDETAIL.replace('www.shiga-jinjacho.jp','example.test')),
                      shiga_index(SDETAIL.replace('oid=7','oid=8')),
                      shiga_index().replace('大津市例町','大津市別町')]:
            with self.subTest(index=index),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);self.setup_data(root/'data');client=FixtureClient({SINDEX:index,SDETAIL:shiga_detail()})
                result=a.research(root/'data',root/'state',client,source='shiga')
                self.assertEqual(result['proposals'],0);self.assertEqual(client.calls,[SINDEX])

    def test_fetch_failure_stops_the_prefecture_and_retains_unvisited(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.setup_data(root/'data');d=load_dataset(root/'data/sources/shiga.json')
            f=copy.deepcopy(d['facilities'][0]);f.update(id='f1',native_source_id='8');d['facilities'].append(f)
            e=copy.deepcopy(d['entries'][0]);e.update(id='e1',facility_id='f1');d['entries'].append(e);write_json(root/'data/sources/shiga.json',d)
            client=FixtureClient({});result=a.research(root/'data',root/'state',client,source='shiga')
            self.assertEqual((result['errors'],result['unvisited']),(1,1));self.assertEqual(client.calls,[SINDEX])

    def test_ambiguous_base_duplicate_native_links_and_untrusted_queries_fail_closed(self):
        with self.assertRaises(ValueError):a.shiga_links(page(shiga_index()+'<base href="https://example.test/">',SINDEX))
        self.assertEqual(a.shiga_links(page(shiga_index()+shiga_index().split('>',1)[1],SINDEX)),[])
        for url in [SDETAIL+'&view:oid=8',SDETAIL.replace('mode:view=1','mode:view=2'),SDETAIL+'&admin=1']:
            self.assertFalse(a.detail_url(url,source='shiga'))

    def test_detached_trusted_anchor_cannot_supply_another_rows_href(self):
        hostile=shiga_index(SDETAIL.replace('www.shiga-jinjacho.jp','example.test'))
        detached='<a href="'+SDETAIL+'">例神社</a>'
        self.assertEqual(a.shiga_links(page(hostile+detached,SINDEX)),[])

    def test_full_row_href_is_checked_without_truncating_trailing_parameters(self):
        for suffix in ['&amp;admin=1','&amp;view:oid=8','#another-facility']:
            with self.subTest(suffix=suffix):
                self.assertEqual(a.shiga_links(page(shiga_index(SDETAIL+suffix),SINDEX)),[])

NINDEX='https://www.nagano-jinjacho.jp/shibu/hani.htm'
NDETAIL='https://www.nagano-jinjacho.jp/shibu/04nansin/03hani/6088.htm'
def nagano_index(href=NDETAIL,address='下伊那郡阿智村伍和5664番地1イ号'):
    return '<table><tr><td>outer<table><tr><td>神社名</td><td>〒</td><td>住所</td></tr><tr><td><a href="'+href+'">若宮社</a></td><td>395</td><td>'+address+'</td></tr></table></td></tr></table>'
def nagano_detail(name='若宮社(わかみやしゃ)　(通称)法力社',address='下伊那郡阿智村伍和5664番地1イ号'):
    return '<table><tr><td>宮司名</td><td>人名</td></tr><tr><td>神社名</td><td>'+name+'</td></tr><tr><td>鎮座地</td><td>'+address+'</td></tr><tr><td>本社祭神名</td><td>祭神(まつりがみ)</td></tr></table>'

class NaganoDetailTests(unittest.TestCase):
    def setup_data(self,root):
        data=AgencyDetailsTests().setup_data(root)
        f=data['facilities'][0];f.update(name_raw='若宮社',listed_name='若宮社',prefecture='長野県',prefecture_code='20',native_source_id=None,listing_url=NINDEX,address='下伊那郡阿智村伍和5664番地1イ号')
        data['entries'][0]['surface']='若宮社';data['collection']['source_key']='nagano'
        write_json(root/'sources/nagano.json',data);return data
    def test_nested_index_exact_name_address_yields_actual_link_and_proof(self):
        records=a.nagano_links(page(nagano_index(),NINDEX))
        self.assertEqual(len(records),1);self.assertEqual(records[0]['url'],NDETAIL)
        self.assertEqual(records[0]['name_raw'],'若宮社');self.assertEqual(records[0]['index_page_hash'],page(nagano_index(),NINDEX).sha256)
    def test_detail_uses_leading_full_name_reading_and_preserves_alias_field(self):
        ref=a.parse_detail(page(nagano_detail(),NDETAIL),'若宮社',source='nagano')
        self.assertEqual(ref['name_raw'],'若宮社');self.assertEqual(ref['reading_raw'],'わかみやしゃ')
        self.assertEqual(ref['name_field_raw'],'若宮社(わかみやしゃ)　(通称)法力社')
        for body in [nagano_detail(name='法力社(ほうりきしゃ)'),nagano_detail(name='若宮社'),nagano_detail(name='若宮社(わかみや)'),nagano_detail().replace('鎮座地','宮司住所'),nagano_detail()+nagano_detail(),nagano_detail(address='前宮 住所1 奥宮2')]:
            with self.subTest(body=body),self.assertRaises(ValueError):a.parse_detail(page(body,NDETAIL),'若宮社',source='nagano')
    def test_run_binds_index_tuple_caches_index_and_keeps_raw_source_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);d=self.setup_data(root/'data');before=(root/'data/sources/nagano.json').read_bytes()
            client=FixtureClient({NINDEX:nagano_index(),NDETAIL:nagano_detail()})
            result=a.research(root/'data',root/'state',client,source='nagano')
            self.assertEqual(result['proposals'],1);self.assertEqual(client.calls,[NINDEX,NDETAIL])
            ref=load_dataset(root/'state/proposals.json')['entries']['e0']['references'][0]
            self.assertEqual(ref['index_url'],NINDEX);self.assertEqual(ref['url'],NDETAIL)
            self.assertEqual((root/'data/sources/nagano.json').read_bytes(),before)
    def test_foreign_link_and_different_index_address_never_fetch_detail(self):
        for body in [nagano_index(href='https://evil.example/6088.htm'),nagano_index(address='下伊那郡阿智村伍和5665番地1イ号')]:
            with tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);self.setup_data(root/'data');client=FixtureClient({NINDEX:body,NDETAIL:nagano_detail()})
                result=a.research(root/'data',root/'state',client,source='nagano')
                self.assertEqual(result['proposals'],0);self.assertEqual(result['pending'],1);self.assertEqual(client.calls,[NINDEX])
    def test_detail_address_difference_remains_pending_without_repair(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.setup_data(root/'data')
            client=FixtureClient({NINDEX:nagano_index(),NDETAIL:nagano_detail(address='下伊那郡阿智村字伍和5664番地1イ号')})
            self.assertEqual(a.research(root/'data',root/'state',client,source='nagano')['proposals'],0)
    def test_shared_index_fetched_once_and_pending_preserves_observed_reference(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);d=self.setup_data(root/'data')
            second=NDETAIL.replace('6088','6089');f=copy.deepcopy(d['facilities'][0]);f.update(id='f1',name_raw='別神社',listed_name='別神社',address='下伊那郡阿智村伍和1234')
            e=copy.deepcopy(d['entries'][0]);e.update(id='e1',facility_id='f1',surface='別神社');d['facilities'].append(f);d['entries'].append(e);write_json(root/'data/sources/nagano.json',d)
            index=nagano_index().replace('</table></td>', '<tr><td><a href="'+second+'">別神社</a></td><td>395</td><td>下伊那郡阿智村伍和1234</td></tr></table></td>')
            client=FixtureClient({NINDEX:index,NDETAIL:nagano_detail(address='違う住所'),second:nagano_detail(name='別神社(べつじんじゃ)',address='下伊那郡阿智村伍和1234')})
            result=a.research(root/'data',root/'state',client,source='nagano')
            self.assertEqual(result['proposals'],1);self.assertEqual(client.calls.count(NINDEX),1)
            record=load_dataset(root/'state/state/progress.json')['entries']['e0']
            self.assertEqual(record['reference']['reading_raw'],'わかみやしゃ')
            self.assertEqual(record['reference']['index_url'],NINDEX)
    def test_state_source_guard_and_duplicate_index_identity_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.setup_data(root/'data');client=FixtureClient({NINDEX:nagano_index()+nagano_index(),NDETAIL:nagano_detail()})
            self.assertEqual(a.research(root/'data',root/'state',client,source='nagano')['pending'],1)
            self.assertEqual(client.calls,[NINDEX])
            with self.assertRaises(ValueError):a.research(root/'data',root/'state',client,source='shimane')
