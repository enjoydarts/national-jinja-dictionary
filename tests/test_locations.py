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

    def test_kumamoto_residential_area_requires_independent_shrine_site(self):
        d, doc, s = fixture()
        f = d['facilities'][0]
        f.update(source_key='kumamoto', prefecture_code='43', prefecture='熊本県',
                 address='上益城郡大野712', listing_url='https://kumamotokenjinjacho.jp/patron-god/page/2/',
                 native_source_id='https://kumamotokenjinjacho.jp/patron-god/example/',
                 official_site_url=None)
        s.update(supplement_kind='kumamoto_documented_shrine_site',
                 original={k:f.get(k) for k in s['original']},
                 changes=dict(address='上益城郡山都町大野712', municipality='上益城郡山都町'))
        s['agency_link'].update(url=f['listing_url'], href_raw=f['native_source_id'],
                                address_label='お住まいの地域', area_raw=f['address'])
        observed = '2026-11-20T01:00:00+00:00'
        s['reference'].update(url='https://www.pref.kumamoto.jp/uploaded/attachment/299762.pdf',
                              name_raw='架空神宮', address_raw=s['changes']['address'],
                              source_kind='prefectural_shrine_tourism', fetched_at=observed,
                              excerpt='架空神宮 上益城郡山都町大野712')
        s['alias_reference'] = dict(url='https://www.env.go.jp/example.pdf', page_hash='c'*64,
                                   checked_at=observed, locator='観光資源の名称',
                                   name_raw='架空神社', alias_raw='架空神宮', excerpt='架空神宮(架空神社)')
        corporate = '1330005004004'
        fields = dict(name='架空神社', corporateNumber=corporate, prefectureCode='43', prefectureName='熊本県',
                      cityName='上益城郡山都町', kind='399', latest='1', hihyoji='0', process='01',
                      streetNumber='大野７１２番地', closeDate='', nameImageId='', addressImageId='')
        s['registry_reference'] = dict(
            url='https://www.houjin-bangou.nta.go.jp/download/zenken/index.html',
            checked_at=observed, page_hash='d'*64, csv_row=44, corporate_number=corporate,
            address_raw='熊本県上益城郡山都町大野７１２番地', source_fields=fields,
            registry_state_proof=dict(unique_active_corporate_number=corporate, full_address_active_corporations=1))
        self.assertEqual(self.api.location_problems(s, f, d['collection']), [])
        out = self.api.apply_locations(d, doc)
        self.assertEqual(out['facilities'][0]['address'], '上益城郡山都町大野712')
        self.assertEqual(self.api.raw_address(out['facilities'][0]), '上益城郡大野712')
        self.assertEqual(out['entries'][0]['status'], 'pending')
        self.assertEqual(self.api.apply_locations(out, doc), out)
        for key, mutation in (
            ('office', lambda s: s['reference'].update(location_role='office')),
            ('alias', lambda s: s['alias_reference'].update(excerpt='別神社(架空神社)')),
            ('parcel', lambda s: s['registry_reference']['source_fields'].update(streetNumber='大野７１２番地の１')),
        ):
            with self.subTest(key=key):
                invalid = copy.deepcopy(s)
                mutation(invalid)
                self.assertTrue(self.api.location_problems(invalid, f, d['collection']))

    def test_kumamoto_municipal_source_must_match_the_registered_municipality(self):
        takamori = 'https://www.town.kumamoto-takamori.lg.jp/site/kanko/example.html'
        minamiaso = 'https://www.vill.minamiaso.lg.jp/dynamic/info/pub/detail.aspx?c_id=29&id=133'
        oguni = 'https://www.town.kumamoto-oguni.lg.jp/kankojyoho/example.html'
        ubuyama = 'https://www.ubuyama-v.jp/section/iju/ubuyama_guide.pdf'
        for municipality, source_url, other_url, parcel_gap in (
            ('阿蘇郡高森町', takamori, oguni, ''),
            ('阿蘇郡南阿蘇村', minamiaso, takamori, ''),
            ('阿蘇郡産山村', ubuyama, minamiaso, ' '),
        ):
            with self.subTest(municipality=municipality):
                d, doc, s = fixture()
                f = d['facilities'][0]
                address = municipality + '架空' + parcel_gap + '712'
                f.update(source_key='kumamoto', prefecture_code='43', prefecture='熊本県',
                         address='阿蘇郡架空712', listing_url='https://kumamotokenjinjacho.jp/patron-god/page/2/',
                         native_source_id='https://kumamotokenjinjacho.jp/patron-god/example/',
                         official_site_url=None)
                s.update(supplement_kind='kumamoto_documented_shrine_site',
                         original={k:f.get(k) for k in s['original']},
                         changes=dict(address=address, municipality=municipality))
                s['agency_link'].update(url=f['listing_url'], href_raw=f['native_source_id'],
                                        address_label='お住まいの地域', area_raw=f['address'])
                s['reference'].update(url=source_url,
                                      address_raw=address, source_kind='municipal_shrine_tourism',
                                      excerpt='架空神社 ' + address)
                corporate = '1330005004004'
                street = '大字架空７１２番地'
                fields = dict(name='架空神社', corporateNumber=corporate, prefectureCode='43', prefectureName='熊本県',
                              cityName=municipality, kind='399', latest='1', hihyoji='0', process='01',
                              streetNumber=street, closeDate='', nameImageId='', addressImageId='')
                s['registry_reference'] = dict(
                    url='https://www.houjin-bangou.nta.go.jp/download/zenken/index.html',
                    checked_at=f['fetched_at'], page_hash='d'*64, csv_row=44, corporate_number=corporate,
                    address_raw='熊本県' + municipality + street, source_fields=fields,
                    registry_state_proof=dict(unique_active_corporate_number=corporate, full_address_active_corporations=1))
                self.assertEqual(self.api.location_problems(s, f, d['collection']), [])
                out = self.api.apply_locations(d, doc)
                self.assertEqual(out['facilities'][0]['address'], address)
                self.assertEqual(self.api.raw_address(out['facilities'][0]), '阿蘇郡架空712')
                wrong_parcel = copy.deepcopy(s)
                wrong_parcel['changes']['address'] = address + '-1'
                wrong_parcel['reference'].update(address_raw=address + '-1', excerpt='架空神社 ' + address + '-1')
                self.assertTrue(self.api.location_problems(wrong_parcel, f, d['collection']))
                s['reference']['url'] = other_url
                self.assertTrue(self.api.location_problems(s, f, d['collection']))

    def test_nishihara_affiliated_shrine_keeps_the_short_printed_address(self):
        d, doc, s = nishihara_fixture('小森神社')
        self.assertEqual(self.api.location_problems(s, d['facilities'][0], d['collection']), [])
        out = self.api.apply_locations(d, doc)
        site = out['facilities'][0]
        self.assertEqual((site['address'], site['municipality']), ('西原村小森386番地', '阿蘇郡西原村'))
        self.assertEqual(self.api.raw_address(site), '阿蘇郡小森386')
        self.assertEqual(out['entries'][0]['reason'], 'missing agency reading')
        self.assertEqual(self.api.apply_locations(out, doc), out)

    def test_nishihara_affiliate_requires_publisher_scope_and_shrine_row(self):
        for incompatible in ('missing scope', 'office', 'other row', 'fabricated prefecture prefix',
                             'changed agency area', 'changed registry parcel', 'rewritten official office fields'):
            with self.subTest(incompatible=incompatible):
                d, _, s = nishihara_fixture('小森神社')
                if incompatible == 'missing scope':
                    del s['reference']['scope_reference']
                elif incompatible == 'office':
                    s['reference']['location_role'] = 'principal_office'
                elif incompatible == 'other row':
                    s['reference']['locator'] = '西原村内の兼務神社表 tr[3] 神社名・鎮座地セル'
                elif incompatible == 'fabricated prefecture prefix':
                    address = '熊本県阿蘇郡西原村小森386番地'
                    s['reference']['address_raw'] = s['changes']['address'] = address
                    s['reference']['excerpt'] = '小森神社 ／ ' + address
                elif incompatible == 'changed agency area':
                    s['agency_recheck']['area_raw'] = '阿蘇郡小森386-1'
                elif incompatible == 'changed registry parcel':
                    s['current_registry_reference']['address_raw'] += 'の１'
                else:
                    register = s['registry_reference']
                    register['source_fields']['streetNumber'] = '小森386'
                    register['address_raw'] = '熊本県阿蘇郡西原村小森386'
                    s['current_registry_reference']['address_raw'] = register['address_raw']
                self.assertTrue(self.api.location_problems(s, d['facilities'][0], d['collection']))

    def test_hakusan_requires_village_cadastral_relationship_for_live_koaza(self):
        d, _, s = nishihara_fixture('白山姫神社')
        self.assertEqual(self.api.location_problems(s, d['facilities'][0], d['collection']), [])
        for change in ('missing neighborhood', 'different neighborhood', 'other parcel proposed'):
            with self.subTest(change=change):
                invalid = copy.deepcopy(s)
                if change == 'missing neighborhood':
                    del invalid['locality_reference']
                elif change == 'different neighborhood':
                    invalid['locality_reference']['koaza_raw'] = '古閑'
                else:
                    invalid['changes']['address'] = invalid['locality_reference']['address_raw']
                self.assertTrue(self.api.location_problems(invalid, d['facilities'][0], d['collection']))

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




_NISHIHARA_CASES = {'小森神社': ('b0b7d762-7f68-56c3-802d-54e65e528558',
          '0c7889a7-7c2f-5a5d-8ac0-68ce5d9e808b',
          '3f2010d69dd363de508adf1b052c892547366e47757db440176a921d308ce54a',
          '阿蘇郡小森386',
          'https://kumamotokenjinjacho.jp/patron-god/%e5%b0%8f%e6%a3%ae%e7%a5%9e%e7%a4%be/',
          '西原村小森386番地',
          '西原村内の兼務神社表 tr[2] 神社名・鎮座地セル',
          '2330005002601',
          '大字小森３８６番地',
          15187,
          '566991bcb74e8391224aed6a4dd532f6b2aaa14d68ba341275c0d3f1f8ffaec9',
          '40b056c61d27ce67963ddb425d6eed66fe83e43c56fb92459dda448d3d447bd6'),
 '白山姫神社': ('205f8e8f-c4ba-5767-987d-c5d8584f0a77',
           'eff3a564-4539-5b47-8a6a-7e53c5d9bcfb',
           'f52164800910b5d9f987119cbd8cbf2271e7d94866cfcb6aef7ab7cc4c8f90aa',
           '阿蘇郡河原750',
           'https://kumamotokenjinjacho.jp/patron-god/%e7%99%bd%e5%b1%b1%e5%a7%ab%e7%a5%9e%e7%a4%be/',
           '熊本県阿蘇郡西原村大字河原字門出750番地',
           'h1#cc-m-header-12245966891 と「鎮座地」の実欄',
           '4330005002608',
           '大字河原字門出７５０番地',
           31171,
           'f89bb7204c2ac6579a738e400b197cac6ab10a1d5ccb417a4025146a078dba14',
           'e60675c97eebfc2af71ec45036ff1f4e66ce20192bd1617cdec42d662c7c9b36')}


def nishihara_fixture(name):
    (facility_id, entry_id, source_hash, area, native, address, locator, corporate, street, csv_row,
     agency_hash, registry_detail_hash) = _NISHIHARA_CASES[name]
    d, _, s = fixture()
    f, e = d['facilities'][0], d['entries'][0]
    office = '熊本県阿蘇郡西原村' + street
    observed = '2026-11-27T01:50:00+00:00'
    listing = 'https://kumamotokenjinjacho.jp/patron-god/page/9/'
    official = 'https://shirayamahime.jimdofree.com/'
    official_hash = 'b7e36f19a7acfe84ee42f24ad4b0409f9349806787d42b6a8f620cb271bd5468'
    f.update(id=facility_id, source_hash=source_hash, source_key='kumamoto', prefecture_code='43',
             prefecture='熊本県', name_raw=name, listed_name=name, address=area, listing_url=listing,
             native_source_id=native, official_site_url=None, source_locator=f'table.c-table tr a[href="{native}"]',
             page_hash='68837e930862c15c709cf01bee8c9b8249b355fa5309f8368f0ddba2cbe34a7f')
    e.update(id=entry_id, facility_id=facility_id, source_hash=source_hash, name_raw=name)
    s.update(
        facility_id=facility_id, entry_id=entry_id, expected_source_hash=source_hash,
        supplement_kind='kumamoto_documented_shrine_site',
        original={key: f.get(key) for key in s['original']},
        changes=dict(address=address, municipality='阿蘇郡西原村'),
        agency_link=dict(url=listing, href_raw=native, name_raw=name, locator=f['source_locator'],
                         page_hash=f['page_hash'], fetched_at=f['fetched_at'],
                         address_label='お住まいの地域', area_raw=area),
        agency_recheck=dict(url=native, name_raw=name, locator='氏神詳細の社名見出し・お住まいの地域欄',
                            role='agency_search_area',
                            fetched_at=observed, page_hash=agency_hash,
                            address_label='お住まいの地域', area_raw=area),
        current_registry_reference=dict(
            url='https://www.houjin-bangou.nta.go.jp/henkorireki-johoto.html?selHouzinNo=' + corporate,
            locator='最新情報の商号又は名称／本店又は主たる事務所の所在地',
            fetched_at=observed, page_hash=registry_detail_hash, name_raw=name, corporate_number=corporate,
            address_role='corporation_principal_office', location_role='principal_office', address_raw=office,
            address_column_raw='本店又は主たる事務所の所在地'),
        registry_reference=dict(
            url='https://www.houjin-bangou.nta.go.jp/download/zenken/index.html', checked_at=observed,
            page_hash='303c65d1a53566dadb68bcab585e11f61e4a975bdda1b764b58e73f911a08f5c',
            csv_row=csv_row, corporate_number=corporate, address_raw=office, location_role='principal_office',
            source_fields=dict(name=name, corporateNumber=corporate, prefectureCode='43', prefectureName='熊本県',
                               cityName='阿蘇郡西原村', kind='399', latest='1', hihyoji='0', process='01',
                               streetNumber=street, closeDate='', nameImageId='', addressImageId=''),
            registry_state_proof=dict(unique_active_corporate_number=corporate, full_address_active_corporations=1)),
        reference=dict(
            url=official, page_hash=official_hash, fetched_at=observed, locator=locator, name_raw=name,
            address_raw=address, address_field='鎮座地', excerpt=name + ' ／ 鎮座地 ' + address,
            source_kind='nishihara_shrine_site', source_publisher='白山姫神社', location_role='shrine'),
    )
    if name == '小森神社':
        s['reference'].update(
            url=official + '%E5%85%BC%E5%8B%99%E7%A5%9E%E7%A4%BE-%E6%9D%91%E5%86%85/',
            page_hash='466ef624a6c4c76a3007e30f7ad28a36a5e6ed62f3cb8a78daea160f190550c5',
            source_kind='nishihara_affiliated_shrine_table', name_cell_raw='小森神社　',
            scope_reference=dict(url=official, page_hash=official_hash, fetched_at=observed,
                                 locator='h1#cc-m-header-12245966891 と「鎮座地」の実欄', name_raw='白山姫神社',
                                 municipality_raw='熊本県阿蘇郡西原村',
                                 excerpt='鎮座地　熊本県阿蘇郡西原村大字河原字門出750番地'))
    else:
        locality = '熊本県阿蘇郡西原村大字河原字門出９１８番４'
        s['locality_reference'] = dict(
            url='https://www.vill.nishihara.kumamoto.jp/kiji0031018/3_1018_1033_up_kzkb3zs0.pdf',
            fetched_at=observed, locator='物件番号2の売払物件・地番欄', oaza_raw='河原', koaza_raw='門出',
            page_hash='95bb337e3ec58905054dff5922c5c00a705eb1978ac00ba2c72ed355e1ad0333',
            address_raw=locality, excerpt=locality + ' 門出', pdf_page=1,
            role='independent_hierarchy_other_parcel')
        s['cadastral_hierarchy_reference'] = dict(
            url='https://www.vill.nishihara.kumamoto.jp/kiji003204/index.html',
            fetched_at=observed, locator='調査地区の概要、平成13年度行の大字・小字列',
            page_hash='3ae2c201922421004eeb1b25c369702bf85fa402a73ce21630d1d60de52cfaae',
            oaza_raw='河原', koaza_raw='門出', koaza_cell_raw='門出・古閑・平の一部',
            role='municipal_cadastral_hierarchy', excerpt='平成13年度 ／ 河原 ／ 門出・古閑・平の一部')
    return d, dict(schema_version=1, facilities={facility_id: s}), s

if __name__=='__main__':unittest.main()
