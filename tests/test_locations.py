"""Location evidence must bind an unchanged, addressless agency record."""
import copy
import importlib
import importlib.util
import unittest

from njd.records import build_dataset


def fixture(reading=''):
    url='https://shrine.example.invalid/'
    d=build_dataset('synthetic','42','長崎県','Synthetic agency',[
        dict(name='架空神社',reading_raw=reading,address='',url='https://agency.example.invalid/link.html',
             fetched_at='2026-11-09T00:00:00+00:00',page_hash='a'*64,locator='div#links a[href="'+url+'"]',
             evidence='official agency anchor',source_id=url,official_url=url)])
    f=d['facilities'][0]
    s=dict(status='verified',facility_id=f['id'],expected_source_hash=f['source_hash'],
        original={k:f.get(k) for k in ('name_raw','address','municipality','listing_url','official_site_url','native_source_id')},
        changes=dict(address='長崎県諫早市久山町二二七五-二',municipality='諫早市'),
        agency_link=dict(url=f['listing_url'],name_raw='架空神社',href_raw=url,locator=f['source_locator'],page_hash='a'*64,fetched_at=f['fetched_at']),
        reference=dict(url=url+'access.html',name_raw='架空神社',address_raw='長崎県諫早市久山町二二七五-二',
            excerpt='架空神社 所在地 長崎県諫早市久山町二二七五-二',page_hash='b'*64,fetched_at=f['fetched_at'],
            source_kind='official_shrine',location_role='shrine',locator='access section'),reason='Actual shrine location inspected')
    return d,dict(schema_version=1,facilities={f['id']:s}),s


class LocationTest(unittest.TestCase):
    def setUp(self):
        # Removing the implementation must fail before any evidence can be applied.
        self.assertIsNotNone(importlib.util.find_spec('njd.locations'),'location overlay module is missing')
        self.api=importlib.import_module('njd.locations')

    def test_valid_location_keeps_blank_acquired_address_and_reading(self):
        d,doc,s=fixture();s['reference']['fetched_at']='2026-11-10T01:00:00+00:00';before=copy.deepcopy(d)
        self.assertEqual(self.api.location_problems(s,d['facilities'][0],d['collection']),[])
        out=self.api.apply_locations(d,doc);f=out['facilities'][0];e=out['entries'][0]
        self.assertEqual(d,before)
        self.assertEqual((f['address'],f['municipality'],f['status'],f['reason']),('長崎県諫早市久山町二二七五-二','諫早市','verified',''))
        self.assertEqual(self.api.raw_address(f),'')
        self.assertEqual(f['location_supplement']['original']['address'],'')
        self.assertEqual(f['location_supplement']['original']['municipality'],'')
        self.assertTrue(f['location_supplement']['applied'])
        self.assertEqual(f['checked_at'],'2026-11-10T01:00:00+00:00')
        self.assertEqual(f['fetched_at'],before['facilities'][0]['fetched_at'])
        self.assertEqual((e['reading_raw'],e['reading'],e['status'],e['reason']),('','','pending','missing agency reading'))
        for key in ('id','source_hash','name_raw','listed_name','native_source_id','listing_url'):
            self.assertEqual(f[key],before['facilities'][0][key])
        self.assertEqual(self.api.apply_locations(out,doc),out)
        self.assertEqual(self.api.apply_locations(d,doc),out)

    def test_valid_original_reading_recovers_only_missing_location_pending(self):
        d,doc,s=fixture('カクウジンジャ');out=self.api.apply_locations(d,doc)
        self.assertEqual((out['entries'][0]['status'],out['entries'][0]['reading_raw']),('verified','カクウジンジャ'))
        self.assertEqual(out['entries'][0]['reading'],'かくうじんじゃ')

    def test_unrelated_pending_and_quarantine_are_never_cleared(self):
        for update in [dict(status='excluded',reason='manual exclusion'),dict(status='pending',reason='another unresolved condition'),
                       dict(status='pending',identity_review_required=True,reason='identity review')]:
            with self.subTest(update=update):
                d,doc,s=fixture('かくうじんじゃ');d['entries'][0].update(update)
                out=self.api.apply_locations(d,doc);e=out['entries'][0]
                self.assertNotEqual(e['status'],'verified')
                if update['status']=='excluded':self.assertEqual(e['status'],'excluded')
                if update.get('identity_review_required'):self.assertTrue(e['identity_review_required'])

    def test_invalid_evidence_cannot_supply_location(self):
        mutations=[
            ('wrongname',lambda s:s['reference'].update(name_raw='別神社')),
            ('foreignhost',lambda s:s['reference'].update(url='https://other.example.invalid/')),
            ('office',lambda s:s['reference'].update(location_role='office')),
            ('foreignpref',lambda s:s['changes'].update(address='佐賀県諫早市久山町二二七五-二')),
            ('wrongmunicipality',lambda s:s['changes'].update(municipality='長崎市')),
            ('control',lambda s:s['changes'].update(address='長崎県諫早市\n久山町二二七五-二')),
            ('missingref',lambda s:s.pop('reference')),
            ('hashbad',lambda s:s['reference'].update(page_hash='x')),
            ('datebad',lambda s:s['reference'].update(fetched_at='yesterday')),
            ('stale',lambda s:s.update(expected_source_hash='c'*64)),
            ('native mismatch',lambda s:s['original'].update(native_source_id='other')),
            ('otherfacility',lambda s:s.update(facility_id='different')),
            ('name absent from excerpt',lambda s:s['reference'].update(excerpt='長崎県諫早市久山町二二七五-二')),
            ('wrong parcel',lambda s:s['reference'].update(address_raw='長崎県諫早市久山町二二七五-三')),
            ('not official',lambda s:s['reference'].update(source_kind='directory')),
            ('anchor href',lambda s:s['agency_link'].update(href_raw='https://other.example.invalid/')),
            ('anchor name',lambda s:s['agency_link'].update(name_raw='別神社')),
            ('anchor url',lambda s:s['agency_link'].update(url='https://other.example.invalid/link.html')),
            ('anchor locator',lambda s:s['agency_link'].update(locator='different row')),
            ('anchor hash',lambda s:s['agency_link'].update(page_hash='c'*64)),
            ('missing reason',lambda s:s.update(reason='')),
            ('extra change',lambda s:s['changes'].update(name='別神社')),
            ('discovery',lambda s:s['reference'].update(url='https://www.jinja-net.jp./shrine')),
        ]
        for label,mutate in mutations:
            with self.subTest(label=label):
                d,doc,s=fixture();mutate(s)
                self.assertTrue(self.api.location_problems(s,d['facilities'][0],d['collection']))
                out=self.api.apply_locations(d,doc);f=out['facilities'][0]
                self.assertEqual((f['address'],f['municipality'],f['status']),('','','pending'))
                self.assertFalse(f['location_supplement']['applied'])
                self.assertTrue(f['reason']);self.assertEqual(out['entries'][0]['status'],'pending')

    def test_control_characters_in_evidence_urls_are_rejected(self):
        d,doc,s=fixture()
        s['reference']['url']='https://shrine.example.invalid/\naccess.html'
        self.assertTrue(self.api.location_problems(s,d['facilities'][0],d['collection']))
        self.assertEqual(self.api.apply_locations(d,doc)['facilities'][0]['address'],'')

    def test_shared_host_does_not_prove_same_account(self):
        d,doc,s=fixture();f=d['facilities'][0]
        f['native_source_id']=f['official_site_url']='https://shared.example/shrine-a/'
        s['original'].update(native_source_id=f['native_source_id'],official_site_url=f['official_site_url'])
        s['agency_link']['href_raw']=f['native_source_id']
        s['reference']['url']='https://shared.example/shrine-b/'
        self.assertTrue(self.api.location_problems(s,f,d['collection']))
        self.assertEqual(self.api.apply_locations(d,doc)['facilities'][0]['address'],'')

    def test_reference_scope_accepts_only_same_site_directory_or_exact_query_identity(self):
        examples=[
            ('https://shared.example/shrine-a/','https://shared.example/shrine-a/access.html',True),
            ('https://shared.example/shrine-a','https://shared.example/shrine-a/access.html',True),
            ('https://shared.example/shrine-a/','https://shared.example/shrine-ab/access.html',False),
            ('https://shared.example/shrine-a/index.html','https://shared.example/shrine-a/access.html',True),
            ('https://shared.example/shrine-a/index.htm','https://shared.example/shrine-a/access.html',True),
            ('https://shared.example/index.html','https://shared.example/access.html',True),
            ('https://shared.example/','https://shared.example/access.html',True),
            ('https://shared.example/shrine-a/','https://shared.example/shrine-a/../shrine-b/access.html',False),
            ('https://shared.example/shrine-a/','https://shared.example/shrine-a/%2e%2e/shrine-b/access.html',False),
            ('https://shared.example/%e7%a5%9e/','https://shared.example/%E7%A5%9E/access.html',True),
            ('https://shared.example/detail?id=1','https://shared.example/detail?id=1',True),
            ('https://shared.example/detail?id=1','https://shared.example/detail?id=2',False),
            ('https://shared.example/detail?id=1','https://shared.example/detail/access.html?id=1',False),
            ('https://shared.example/detail?id=1','https://shared.example/detail',False),
        ]
        for native,url,allowed in examples:
            with self.subTest(native=native,url=url):
                d,doc,s=fixture();f=d['facilities'][0]
                f['native_source_id']=f['official_site_url']=native
                s['original'].update(native_source_id=native,official_site_url=native)
                s['agency_link']['href_raw']=native;s['reference']['url']=url
                problems=self.api.location_problems(s,f,d['collection'])
                self.assertEqual(not problems,allowed,problems)

    def test_observed_redirect_chain_can_authorize_a_new_host_without_rewriting_native_identity(self):
        d,doc,s=fixture();f=d['facilities'][0]
        s['reference']['url']='https://www.shrine.example.invalid/canonical/about.html'
        self.assertTrue(self.api.location_problems(s,f,d['collection']))
        s['redirects']=[dict(from_url=f['native_source_id'],to_url='https://www.shrine.example.invalid/canonical/',
            status=301,page_hash='c'*64,fetched_at='2026-11-09T00:00:00+00:00')]
        self.assertEqual(self.api.location_problems(s,f,d['collection']),[])
        out=self.api.apply_locations(d,doc);actual=out['facilities'][0]
        self.assertEqual(actual['native_source_id'],'https://shrine.example.invalid/')
        self.assertEqual(actual['official_site_url'],'https://shrine.example.invalid/')
        self.assertEqual(actual['location_supplement']['redirects'],s['redirects'])
        self.assertEqual(self.api.apply_locations(out,doc),out)

    def test_redirect_records_must_be_complete_contiguous_loop_free_http_responses(self):
        def append_gap(s):
            s['redirects'].append(dict(s['redirects'][0],from_url='https://shrine.example.invalid/unrelated/',
                to_url='https://shrine.example.invalid/final/'))
        def append_loop(s):
            s['redirects'].append(dict(s['redirects'][0],from_url=s['redirects'][0]['to_url'],
                to_url='https://shrine.example.invalid/'))
        def long_chain(s):
            s['redirects']=[dict(s['redirects'][0],from_url='https://shrine.example.invalid/'+(str(i)+'/' if i else ''),
                to_url='https://shrine.example.invalid/'+str(i+1)+'/') for i in range(7)]
        mutations=[
            ('different origin',lambda s:s['redirects'][0].update(from_url='https://other.example.invalid/')),
            ('gap',append_gap),('loop',append_loop),('too long',long_chain),
            ('not redirect status',lambda s:s['redirects'][0].update(status=200)),
            ('bad hash',lambda s:s['redirects'][0].update(page_hash='bad')),
            ('missing date',lambda s:s['redirects'][0].pop('fetched_at')),
            ('invalid url',lambda s:s['redirects'][0].update(to_url='file:///tmp/shrine')),
            ('discovery host',lambda s:s['redirects'][0].update(to_url='https://www.jinja-net.jp./shrine/')),
            ('empty records',lambda s:s.update(redirects=[])),
            ('wrong type',lambda s:s.update(redirects='redirected')),
            ('wrong step type',lambda s:s.update(redirects=[None])),
        ]
        for label,mutate in mutations:
            with self.subTest(label=label):
                d,doc,s=fixture();s['redirects']=[dict(from_url=s['original']['native_source_id'],
                    to_url='https://shrine.example.invalid/canonical/',status=302,page_hash='c'*64,
                    fetched_at='2026-11-09T00:00:00+00:00')]
                mutate(s)
                self.assertTrue(self.api.location_problems(s,d['facilities'][0],d['collection']))
                self.assertFalse(self.api.apply_locations(d,doc)['facilities'][0]['location_supplement']['applied'])

    def test_redirect_destination_retains_existing_account_and_query_scope(self):
        examples=[
            ('https://new.example/shrine-a/','https://new.example/shrine-a/about.html',True),
            ('https://new.example/shrine-a/','https://new.example/shrine-b/about.html',False),
            ('https://new.example/shrine-a/','https://third.example/shrine-a/about.html',False),
            ('https://new.example/detail?id=1','https://new.example/detail?id=1',True),
            ('https://new.example/detail?id=1','https://new.example/detail?id=2',False),
        ]
        for status in (301,302,303,307,308):
            for destination,url,allowed in examples:
                with self.subTest(status=status,destination=destination,url=url):
                    d,doc,s=fixture();s['reference']['url']=url
                    s['redirects']=[dict(from_url=s['original']['native_source_id'],to_url='https://middle.example/old/',
                        status=status,page_hash='c'*64,fetched_at='2026-11-09T00:00:00+00:00'),
                        dict(from_url='https://middle.example/old/',to_url=destination,status=status,
                        page_hash='d'*64,fetched_at='2026-11-09T00:00:01+00:00')]
                    self.assertEqual(not self.api.location_problems(s,d['facilities'][0],d['collection']),allowed)

    def test_malformed_supplement_never_crashes_or_becomes_applied(self):
        for value in (None, [], 'untrusted'):
            d,doc,s=fixture();fid=d['facilities'][0]['id'];doc['facilities'][fid]=value
            self.assertTrue(self.api.location_problems(value,d['facilities'][0]))
            out=self.api.apply_locations(d,doc)
            self.assertEqual(out['facilities'][0]['address'],'')
            self.assertFalse(out['facilities'][0]['location_supplement']['applied'])

    def test_source_location_or_unresolved_facility_identity_is_not_overwritten(self):
        changes=[dict(address='長崎県諫早市既存1'),dict(municipality='諫早市'),dict(name_raw=''),
                 dict(review_reason='identity conflict'),dict(identity_review_required=True),dict(source_conflicts=[{}]),
                 dict(reason='external glyph requires review'),dict(status='excluded',reason='excluded')]
        for update in changes:
            with self.subTest(update=update):
                d,doc,s=fixture();f=d['facilities'][0];f.update(update)
                # Even a freshly matching snapshot cannot authorize replacing an acquired address.
                s['original']={k:f.get(k) for k in s['original']}
                self.assertTrue(self.api.location_problems(s,f,d['collection']))
                out=self.api.apply_locations(d,doc)
                self.assertEqual(out['facilities'][0]['address'],f['address'])

    def test_unconfirmed_agency_cannot_be_replaced_by_official_shrine(self):
        for status in ('pending','unconfirmed'):
            d,doc,s=fixture();d['collection']['authority_status']=status
            self.assertTrue(self.api.location_problems(s,d['facilities'][0],d['collection']))
            self.assertEqual(self.api.apply_locations(d,doc)['facilities'][0]['address'],'')

    def test_reacquired_changed_hash_invalidates_previous_evidence(self):
        d,doc,s=fixture();applied=self.api.apply_locations(d,doc)
        applied['facilities'][0]['source_hash']='d'*64;applied['entries'][0]['source_hash']='d'*64
        out=self.api.apply_locations(applied,doc)
        self.assertEqual(out['facilities'][0]['address'],'')
        self.assertEqual(out['facilities'][0]['status'],'pending')
        self.assertFalse(out['facilities'][0]['location_supplement']['applied'])
        self.assertEqual(out['entries'][0]['status'],'pending')

    def test_research_only_metadata_does_not_change_acquired_location_or_status(self):
        d,doc,s=fixture();before=copy.deepcopy(d);fid=d['facilities'][0]['id']
        record=dict(status='inspected_unresolved',reason='official link requires login',references=[dict(url='https://shrine.example.invalid/')])
        document=dict(schema_version=1,facilities={},research=dict(facilities={fid:record,'unknown':dict(status='unmatched')}))
        out=self.api.apply_locations(d,document)
        self.assertEqual(d,before)
        actual=out['facilities'][0]
        for key,value in before['facilities'][0].items():self.assertEqual(actual[key],value)
        self.assertEqual(out['entries'],before['entries'])
        self.assertEqual(actual['location_research'],record)
        self.assertEqual(out['collection']['location_supplements']['research_unmatched'],['unknown'])
        self.assertEqual(self.api.apply_locations(out,document),out)
        record['references'].append(dict(url='https://different.example/'))
        self.assertEqual(len(actual['location_research']['references']),1)

    def test_research_records_require_dictionary_shapes(self):
        for research in (None,[],{},dict(facilities=[]),dict(facilities={'id':None}),dict(facilities={'id':[]})):
            with self.subTest(research=research):
                d,doc,s=fixture();doc.update(facilities={},research=research)
                with self.assertRaises(ValueError):self.api.apply_locations(d,doc)

    def test_location_and_research_metadata_can_coexist(self):
        d,doc,s=fixture();fid=d['facilities'][0]['id']
        doc['research']=dict(facilities={fid:dict(status='confirmed_location')})
        out=self.api.apply_locations(d,doc)
        self.assertTrue(out['facilities'][0]['location_supplement']['applied'])
        self.assertEqual(out['facilities'][0]['location_research'],dict(status='confirmed_location'))

    def test_unmatched_ids_and_empty_document_are_pure_and_deterministic(self):
        d,doc,s=fixture();doc['facilities']['unknown']=copy.deepcopy(s)
        out=self.api.apply_locations(d,doc)
        self.assertEqual(out['collection']['location_supplements']['unmatched'],['unknown'])
        self.assertEqual(self.api.raw_address(d['facilities'][0]),'')
        empty=self.api.apply_locations(d,dict(schema_version=1,facilities={}))
        self.assertEqual(empty,d);self.assertIsNot(empty,d)
        for invalid in ({},{'schema_version':2,'facilities':{}},{'schema_version':1,'facilities':[]}):
            with self.assertRaises(ValueError):self.api.apply_locations(d,invalid)


if __name__=='__main__':unittest.main()
