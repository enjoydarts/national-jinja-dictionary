"""Synthetic government download fixtures; no network or unrelated real records."""
import csv
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from njd import corporate as c
from njd.http import Page
from njd.storage import write_json, load_dataset


def row(**changes):
    r=['1','1234567890123','01','0','2026-10-30','2015-10-05','前田神社','','399','鳥取県','鳥取市','大覚寺７６番地','','31','201','6800000','','','','','','','2015-10-05','1','','','','','マエダジンジャ','0']
    for k,v in changes.items():r[c.FIELDS.index(k)]=v
    return r


def archive(rows,member='31_tottori_all_20261030.csv'):
    text=io.StringIO();csv.writer(text).writerows(rows);b=io.BytesIO()
    with zipfile.ZipFile(b,'w') as z:z.writestr(member,text.getvalue().encode());z.writestr('31_tottori_all_20261030.csv.asc','signature')
    return b.getvalue()


def target():
    return dict(facility=dict(id='f',listed_name='前田神社',name_raw='前田神社',address='鳥取市大覚寺76',prefecture='鳥取県',prefecture_code='31',status='verified',listing_url='https://agency.example/list'),entry=dict(id='e',facility_id='f',surface='前田神社',reading_raw='',reading='',status='pending',source_hash='hash'),source=dict(prefecture_code='31',authority_status='confirmed'))

META=dict(url='https://www.houjin-bangou.nta.go.jp/download/zenken/index.html',file_id='123',snapshot='20261030',checked_at='2026-11-09T00:00:00+00:00',page_hash='a'*64)
LANDING='<script>doDownload</script><form id="appForm" action="/download/zenken/index.html" method="post"><input name="event" value="download"><input name="jp.go.nta.houjin_bangou.framework.web.common.CNSFWTokenProcessor.request.token" value="SECRET"></form><h2>CSV形式・Unicode</h2><p>令和8年10月30日更新</p><dl><dt>鳥取県</dt><dd><a onclick="return doDownload(123);">zip 878KB</a></dd></dl><h2>XML形式・Unicode</h2>'

class CorporateTests(unittest.TestCase):
    def test_headerless_fields_and_raw_reference(self):
        proposals,pending=c.proposals_for_archive(archive([row()]),[target()],META)
        p=proposals['e'];ref=p['references'][0]
        self.assertEqual(p['changes'],{'reading':'まえだじんじゃ'})
        self.assertEqual(ref['reading_raw'],'マエダジンジャ');self.assertEqual(ref['address_raw'],'鳥取県鳥取市大覚寺７６番地')
        self.assertEqual(ref['source_fields']['corporateNumber'],'1234567890123');self.assertEqual(ref['csv_row'],1)
        self.assertEqual(pending,{})
        self.assertNotIn('SECRET',json.dumps(p))

    def test_unsafe_records_do_not_become_proposals(self):
        for change in [dict(furigana=''),dict(closeDate='2026-01-01'),dict(latest='0'),dict(process='99'),dict(hihyoji='1'),dict(name='宗教法人宗教法人前田神社'),dict(streetNumber='大覚寺７６０番地'),dict(furigana='マエダ'),dict(furigana='マエダジンジヤ')]:
            with self.subTest(change=change):
                proposals,pending=c.proposals_for_archive(archive([row(**change)]),[target()],META)
                self.assertEqual(proposals,{});self.assertIn('e',pending)

    def test_missing_parcel_and_duplicate_identity_rejected(self):
        t=target();t['facility']['address']='鳥取市大覚寺'
        self.assertFalse(c.proposals_for_archive(archive([row()]),[t],META)[0])
        for rows in [[row(),row()],[row(),row(corporateNumber='9876543210123')],[row(),row(furigana='マエタジンジャ')]]:
            self.assertFalse(c.proposals_for_archive(archive(rows),[target()],META)[0])

    def test_malformed_csv_and_archive_limits(self):
        for rows in [[row()[:-1]],[['sequenceNumber']*30]]:
            with self.assertRaises(ValueError):c.proposals_for_archive(archive(rows),[target()],META)
        with self.assertRaises(ValueError):c.proposals_for_archive(archive([row()]),[target()],META,max_uncompressed=10)

    def test_discovery_uses_unicode_section_and_official_post(self):
        result=c.discover(LANDING,['31'])
        self.assertEqual(result['31']['file_id'],'123');self.assertEqual(result['31']['snapshot'],'20261030')
        self.assertEqual(result['31']['url'],META['url'])
        with self.assertRaises(ValueError):c.discover(LANDING.replace('/download/zenken/index.html','https://evil.test/download'),['31'])

    def test_offline_cached_resume_and_private_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);t=target();write_json(root/'data/sources/test.json',dict(collection=t['source'],facilities=[t['facility']],entries=[t['entry']]))
            state=root/'state';cache=root/'cache';client=c.CorporateClient(cache,offline=True)
            client._save(Page(c.BASE+'/robots.txt',404,{},b'',META['checked_at']))
            page=Page(c.LANDING,200,{'content-type':'text/html; charset=utf-8'},LANDING.encode(),META['checked_at']);client._save(page)
            client.store_download(dict(META),Page(META['url'],200,{},archive([row()]),META['checked_at']))
            result=c.research(root/'data',state,['31'],client)
            self.assertEqual(result['proposals'],1)
            text=(state/'proposals.json').read_text();self.assertNotIn('SECRET',text);self.assertNotIn('token',text)
            self.assertEqual(c.research(root/'data',state,['31'],client)['proposals'],1)
            write_json(root/'data/reviews.json',{'entries':{'e':{}}})
            self.assertEqual(c.research(root/'data',state,['31'],client)['proposals'],0)

    def test_split_archives_cannot_hide_conflicting_corporate_identity(self):
        html=LANDING.replace('鳥取県','東京都').replace('zip 878KB</a>','分割1 zip 36MB</a><a onclick="return doDownload(124);">分割2 zip 24MB</a>')
        self.assertEqual([x['file_id'] for x in c.discover(html,['13'])['13']['files']],['123','124'])
        parts=[(archive([row()]),META),(archive([row(corporateNumber='9876543210123')]),META)]
        self.assertEqual(c.proposals_for_archives(parts,[target()])[0],{})

    def test_public_form_download_is_cached_without_session_secret(self):
        class FormClient(c.CorporateClient):
            def __init__(self,path):super().__init__(path);self.posts=0
            def fetch(self,url,**kwargs):return Page(c.LANDING,200,{},LANDING.encode(),META['checked_at'])
            def _policy(self,url,**kwargs):pass
            def _raw(self,url,**kwargs):
                self.posts+=1
                self.asserted_body=kwargs['request_data']
                return Page(url,200,{},archive([row()]),META['checked_at'],'POST','b'*64)
        with tempfile.TemporaryDirectory() as tmp:
            client=FormClient(Path(tmp));meta=dict(META,prefecture_code='31')
            first=client.download(meta);second=client.download(meta)
            self.assertEqual(first.sha256,second.sha256);self.assertEqual(client.posts,1)
            self.assertIn(b'selDlFileNo=123',client.asserted_body)
            manifests=list((Path(tmp)/'corporate-downloads').glob('*.json'))
            self.assertNotIn('SECRET',manifests[0].read_text())
            with self.assertRaises(ValueError):client.download(dict(meta,prefecture_code='00'))

    def test_limited_resume_advances_past_zero_proposal_prefecture(self):
        import copy
        class PrefClient:
            def __init__(self):self.calls=[];self.fail=False
            def fetch(self,url,**kwargs):
                html=LANDING.replace('<h2>XML', '<dl><dt>島根県</dt><dd><a onclick="return doDownload(124);">zip 1MB</a></dd></dl><h2>XML')
                return Page(c.LANDING,200,{},html.encode(),META['checked_at'])
            def download(self,meta,**kwargs):
                code=meta['prefecture_code'];self.calls.append(code)
                if self.fail:raise c.FetchError('temporary error')
                rows=[row(furigana='')] if code=='31' else [row(prefectureName='島根県',prefectureCode='32',cityName='松江市',streetNumber='大覚寺７６番地')]
                member=code+('_tottori' if code=='31' else '_shimane')+'_all_20261030.csv'
                return Page(META['url'],200,{},archive(rows,member),META['checked_at'])
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);client=PrefClient()
            for code in ['31','32']:
                t=copy.deepcopy(target());t['facility'].update(id='f'+code,prefecture_code=code)
                t['entry'].update(id='e'+code,facility_id='f'+code);t['source']['prefecture_code']=code
                if code=='32':t['facility'].update(prefecture='島根県',address='松江市大覚寺76')
                write_json(root/('data/sources/'+code+'.json'),dict(collection=t['source'],facilities=[t['facility']],entries=[t['entry']]))
            first=c.research(root/'data',root/'state',['31','32'],client,limit=1)
            self.assertEqual(first['proposals'],0);self.assertEqual(client.calls,['31'])
            client.fail=True
            self.assertIn('32',c.research(root/'data',root/'state',['31','32'],client,limit=1)['errors'])
            client.fail=False
            final=c.research(root/'data',root/'state',['31','32'],client,limit=1)
            self.assertEqual(final['proposals'],1);self.assertEqual(client.calls,['31','32','32'])
            self.assertEqual(c.research(root/'data',root/'state',['31','32'],client,limit=1)['prefectures_attempted'],0)
            path=root/'data/sources/31.json';d=load_dataset(path);d['entries'][0]['source_hash']='changed';write_json(path,d)
            self.assertEqual(c.research(root/'data',root/'state',['31','32'],client,limit=1)['prefectures_attempted'],1)
            self.assertEqual(client.calls[-1],'31')

    def test_explicit_nonstandard_full_shrine_endings_are_preserved(self):
        for raw,want in [('マエダジンシャ','まえだじんしゃ'),('マエダシンジャ','まえだしんじゃ'),('マエダシンシャ','まえだしんしゃ')]:
            proposals,_=c.proposals_for_archive(archive([row(furigana=raw)]),[target()],META)
            self.assertEqual(proposals['e']['changes']['reading'],want)

    def test_external_path_guard(self):
        with self.assertRaises(ValueError):c.external_directory(Path(__file__).resolve().parents[1]/'research/corporate')

if __name__=='__main__':unittest.main()
