"""Synthetic association pages; none of these fixtures are real shrine evidence."""
import tempfile
import unittest
from pathlib import Path
from njd.http import Page,FetchError
from njd import association_sources as a

DATE='2026-11-10T00:00:00+00:00'
def card(name='例﨑神社',reading='れいざきじんじゃ',address='例市例町1',slug='example'):
    return ('<li><h2>'+name+'（'+reading+'）</h2><div class="shrine_list_top">歴史は保存しない</div>'
      '<div class="shrine_list_data"><div class="data_list"><div class="data_ttl post">郵便番号</div><div class="data">880-0000</div></div>'
      '<div class="data_list"><div class="data_ttl address">住所</div><div class="data">'+address+'</div></div></div>'
      '<a href="'+a.BASE+'/m_shrine/'+slug+'/">詳細はこちら</a></li>')
def page(cards=None,next_url=None,url=None):
    body='<h1>宮崎県の神社</h1><ul class="shrine_list">'+(cards if cards is not None else card())+'</ul>'
    if next_url:body+='<a class="nextpostslink" rel="next" href="'+next_url+'">次</a>'
    return Page(url or a.INDEX,200,{'content-type':'text/html'},body.encode(),DATE)

class AssociationTests(unittest.TestCase):
    def test_card_preserves_glyph_and_full_literal_reading_and_locator(self):
        result=a.inspect_index(page())
        row=result['observations'][0]
        self.assertEqual((row['name_raw'],row['reading_raw'],row['address_raw']),('例﨑神社','れいざきじんじゃ','例市例町1'))
        self.assertEqual(row['header_raw'],'例﨑神社（れいざきじんじゃ）')
        self.assertEqual(row['profile_url'],a.BASE+'/m_shrine/example/')
        self.assertEqual(row['page_hash'],page().sha256)
        self.assertNotIn('歴史',str(row))
        self.assertEqual(row['source_kind'],'shinto_association')
    def test_ambiguous_name_or_address_is_held_without_kana_guess(self):
        for contents in [card(reading='れい'),card(reading='れい じんじゃ'),card(address=''),card().replace('例市例町1','例市例町1<br>別市2')]:
            result=a.inspect_index(page(contents))
            self.assertEqual(len(result['reviews']),1)
            self.assertEqual(result['observations'],[])
    def test_only_actual_next_page_in_source_scope_is_followed(self):
        self.assertEqual(a.inspect_index(page(next_url=a.BASE+'/shrine/page/2/'))['next_url'],a.BASE+'/shrine/page/2/')
        for url in ['https://other.example/shrine/page/2/',a.BASE+'/shrine/page/2/?x=1',a.BASE+'/m_shrine/example/']:
            with self.assertRaises(ValueError):a.inspect_index(page(next_url=url))
    def test_same_name_with_distinct_address_remains_two_observations(self):
        result=a.inspect_index(page(card()+card(address='別市2',slug='other')))
        self.assertEqual(len(result['observations']),2)
    def test_research_checkpoints_limit_and_resumes_without_refetch(self):
        second=a.BASE+'/shrine/page/2/'
        pages={a.INDEX:page(next_url=second),second:page(card(address='別市2',slug='other'),url=second)}
        class Source:
            def __init__(self):self.calls=[]
            def fetch(self,url,**kwargs):self.calls.append(url);return pages[url]
        source=Source()
        with tempfile.TemporaryDirectory() as tmp:
            first=a.research(tmp,source,limit=1)
            self.assertFalse(first['complete']);self.assertEqual(first['observations'],1)
            result=a.research(tmp,source)
            self.assertTrue(result['complete']);self.assertEqual(result['observations'],2)
            self.assertEqual(source.calls,[a.INDEX,second])
    def test_fetch_failure_is_checkpointed_and_not_complete(self):
        class Source:
            def fetch(self,url,**kwargs):raise FetchError('not public diagnostic')
        with tempfile.TemporaryDirectory() as tmp:
            result=a.research(tmp,Source())
            self.assertFalse(result['complete'])
            text=(Path(tmp)/'state.json').read_text()
            self.assertNotIn('not public diagnostic',text)
            self.assertIn('fetch_failed',text)

class AssociationCanonicalTests(unittest.TestCase):
    def collection(self):
        return dict(source_key='miyazaki_youth',prefecture_code='45',source_publisher=a.PUBLISHER,
            official_agency_listing_verified=False,observations=a.inspect_index(page())['observations'],reviews=[],
            pages=[dict(url=a.INDEX,page_hash=page().sha256,fetched_at=DATE)],collection_complete=True,remaining_url=None,
            authority_reference=dict(url=a.BASE+'/aboutus/',excerpt='宮崎県神道青年会とは',page_hash='a'*64,checked_at=DATE))
    def test_canonical_basis_preserves_publisher_and_does_not_claim_agency_or_wiki_license(self):
        from njd.validation import blocking_problems,eligible
        d=a.dataset_from_observations(self.collection(),existing=None)
        self.assertFalse(blocking_problems(d));self.assertEqual(len(eligible(d)),1)
        f=d['facilities'][0];e=d['entries'][0]
        self.assertEqual(f['listing_basis'],'association_reference');self.assertNotIn('agency',f)
        self.assertEqual(e['reading_source_kind'],'association')
        self.assertNotIn('license_url',f['source_reference'])
        self.assertEqual(d['collection']['redistribution_status'],'unconfirmed')
    def test_same_name_or_exact_location_in_existing_data_is_held_not_merged(self):
        from njd.records import build_dataset
        existing=build_dataset('other','45','宮崎県','例神社庁',[dict(name='例﨑神社',address='宮崎県別市1',reading_raw='れいざきじんじゃ',url='https://example.org/1',fetched_at=DATE,page_hash='b'*64,locator='row',evidence='source')])
        d=a.dataset_from_observations(self.collection(),existing=existing)
        self.assertEqual(d['facilities'],[])
        held=d['collection']['identity_reviews'][0]
        self.assertEqual(held['existing_facility_ids'],[existing['facilities'][0]['id']])
        self.assertEqual(held['observation']['address_raw'],'例市例町1')
    def test_unverified_publisher_missing_scope_and_tampering_block_output(self):
        import copy
        from njd.validation import eligible,blocking_problems
        for mutate in [lambda d:d['facilities'][0].update(listing_basis='agency'),
                       lambda d:d['facilities'][0]['source_reference'].update(address_raw='別市2'),
                       lambda d:d['collection'].update(official_agency_listing_verified=True),
                       lambda d:d['entries'][0].update(reading_source_kind='agency'),
                       lambda d:d['collection'].pop('authority_reference')]:
            d=a.dataset_from_observations(self.collection(),existing=None);mutate(d)
            self.assertTrue(blocking_problems(d));self.assertEqual(eligible(d),[])
        for mutate in [lambda d:d['observations'][0].update(profile_url='https://example.org/x'),
                       lambda d:d['observations'][0].update(reading_raw='れい'),
                       lambda d:d['authority_reference'].update(excerpt='別団体')]:
            c=copy.deepcopy(self.collection());mutate(c)
            with self.assertRaises(ValueError):a.dataset_from_observations(c,existing=None)
    def test_duplicate_profile_is_one_facility_with_source_occurrences(self):
        import copy
        c=self.collection();extra=copy.deepcopy(c['observations'][0]);extra['locator']='ul.shrine_list > li:nth-child(2)';c['observations'].append(extra)
        d=a.dataset_from_observations(c,existing=None)
        self.assertEqual(len(d['facilities']),1)
        self.assertEqual(len(d['facilities'][0]['listing_occurrences']),2)

class AssociationLayoutTests(unittest.TestCase):
    def test_location_suffix_requires_literal_address_support_and_is_not_word_surface(self):
        p=page(card(address='例郡例町大字上原1').replace('例﨑神社（れいざきじんじゃ）','例﨑神社（れいざきじんじゃ）例町上原'))
        result=a.inspect_index(p)
        self.assertEqual(len(result['observations']),1)
        self.assertEqual(result['observations'][0]['name_raw'],'例﨑神社')
        self.assertEqual(result['observations'][0]['header_location_suffix_raw'],'例町上原')
        for suffix in ['別町','別神社','（別称神社）']:
            self.assertEqual(a.inspect_index(page(card().replace('（れいざきじんじゃ）','（れいざきじんじゃ）'+suffix)))['observations'],[])
    def test_postal_is_optional_source_metadata_and_never_repaired(self):
        for postal in ['', '8800000','880－0000']:
            result=a.inspect_index(page(card().replace('880-0000',postal)))
            self.assertEqual(len(result['observations']),1)
            self.assertEqual(result['observations'][0]['postal_code_raw'],postal)
        result=a.inspect_index(page(card(address='火産霊神（ほむすびのかみ）').replace('880-0000','例市1')))
        self.assertEqual(result['observations'],[])

class AssociationLocalityCharactersTests(unittest.TestCase):
    def test_literal_localities_allow_hiragana_and_internal_miya_character(self):
        for locality,address in [('えびの市','えびの市大字例1'),('宮崎市','宮崎市大字例1'),('例市宮丸','例市宮丸1')]:
            p=page(card(address=address).replace('（れいざきじんじゃ）','（れいざきじんじゃ）'+locality))
            self.assertEqual(len(a.inspect_index(p)['observations']),1)

class AssociationIdentitySafetyTests(unittest.TestCase):
    collection=AssociationCanonicalTests.collection
    def test_different_names_at_same_parcel_are_held_across_address_notation(self):
        from njd.records import build_dataset
        c=self.collection();r=c['observations'][0];r['address_raw']='例市例町二丁目4番1号';r['excerpt']=r['header_raw']+' / 住所 '+r['address_raw']
        existing=build_dataset('other','45','宮崎県','例神社庁',[dict(name='別表記神社',address='宮崎県例市例町二丁目4-1',reading_raw='べつひょうきじんじゃ',url='https://example.org/1',fetched_at=DATE,page_hash='b'*64,locator='row',evidence='source')])
        self.assertEqual(a.dataset_from_observations(c,existing=existing)['facilities'],[])
    def test_composed_duplicate_profile_identity_is_globally_blocked(self):
        import copy
        from njd.validation import blocking_problems,eligible
        d=a.dataset_from_observations(self.collection(),existing=None);f=copy.deepcopy(d['facilities'][0]);e=copy.deepcopy(d['entries'][0])
        f['id']='different-id';e.update(id='different-entry-id',facility_id=f['id']);d['facilities'].append(f);d['entries'].append(e)
        self.assertTrue(any('duplicate association profile' in p['reason'] for p in blocking_problems(d)))
        self.assertEqual(eligible(d),[])
    def test_release_source_notice_separates_association_from_wikipedia_and_agency(self):
        import json,zipfile
        from njd.nationwide import save_collection
        from njd.release import create_release
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);save_collection(root/'data','miyazaki_youth',a.dataset_from_observations(self.collection(),existing=None))
            result=create_release(root/'data',root/'out','v-test','a'*40)
            with zipfile.ZipFile(result['archive']) as z:
                notice=z.read('README.md').decode();credits=json.loads(z.read('ATTRIBUTION.json'))
                self.assertIn(a.PUBLISHER,notice)
                self.assertIn('未確認',notice)
                self.assertEqual(credits['association'][0]['publisher'],a.PUBLISHER)
                self.assertEqual(credits['association'][0]['redistribution_status'],'unconfirmed')
                self.assertEqual(credits['wikipedia'],[])

class AssociationProfileAuditTests(unittest.TestCase):
    def test_audit_compares_actual_profile_fields_and_keeps_its_own_fingerprint(self):
        r=a.inspect_index(page())['observations'][0]
        profile=Page(r['profile_url'],200,{'content-type':'text/html'},('<h2>'+r['header_raw']+'</h2><div class="data_list"><div class="data_ttl address">住所</div><div class="data">'+r['address_raw']+'</div></div>').encode(),DATE)
        result=a.audit_profile(profile,r)
        self.assertEqual(result['status'],'matched');self.assertEqual(result['page_hash'],profile.sha256)
        wrong=Page(profile.url,200,profile.headers,profile.body.replace('例市例町1'.encode(),'例市例町2'.encode()),DATE)
        self.assertEqual(a.audit_profile(wrong,r)['status'],'mismatch')

class AssociationAuditResumeTests(unittest.TestCase):
    def test_audit_sample_records_failures_with_public_reason_and_can_be_resumed(self):
        class Source:
            def fetch(self,url,**kwargs):raise FetchError('private transport context')
        with tempfile.TemporaryDirectory() as tmp:
            report=a.audit_sample(a.inspect_index(page())['observations'],tmp,Source(),maximum=50)
            self.assertEqual(report['failed'],1)
            self.assertNotIn('private transport context',(Path(tmp)/'profile-audit.json').read_text())

class AssociationRefreshIdentityTests(unittest.TestCase):
    collection=AssociationCanonicalTests.collection
    def test_regeneration_does_not_hold_its_own_existing_source(self):
        d=a.dataset_from_observations(self.collection(),existing=None)
        again=a.dataset_from_observations(self.collection(),existing=d)
        self.assertEqual(again['facilities'],d['facilities'])
        self.assertEqual(again['collection']['identity_reviews'],[])

class AssociationAuthorityTests(unittest.TestCase):
    def test_authority_is_based_on_opened_self_identification_page(self):
        p=Page(a.BASE+'/aboutus/',200,{'content-type':'text/html'},'<h1>宮崎県神道青年会とは</h1>'.encode(),DATE)
        proof=a.inspect_authority(p)
        self.assertEqual(proof['page_hash'],p.sha256)
        self.assertIn(a.PUBLISHER,proof['excerpt'])
        with self.assertRaises(ValueError):a.inspect_authority(Page(p.url,200,p.headers,b'<h1>Other publisher</h1>',DATE))

class AssociationHumanReviewTests(unittest.TestCase):
    collection=AssociationCanonicalTests.collection
    def test_explicit_user_reading_stays_separate_from_source_literal(self):
        from njd.reviews import apply_reviews
        from njd.validation import eligible,blocking_problems
        d=a.dataset_from_observations(self.collection(),existing=None);f=d['facilities'][0];e=d['entries'][0]
        item=dict(case_id='synthetic-association-review',facility_id=f['id'],expected_source_hash=e['source_hash'],
            original=dict(name_raw=f['name_raw'],reading_raw=e['reading_raw'],address=f['address'],listing_url=f['listing_url']),
            confirmation='user_confirmation',recorded_at=DATE,reason='Explicit synthetic user judgment',
            outputs=[dict(surface=e['surface'],reading='れいさきじんじゃ',basis='user_confirmation',reading_url='')])
        reviewed=apply_reviews(d,dict(schema_version=1,entries={e['id']:item}))
        self.assertFalse(blocking_problems(reviewed));self.assertEqual(eligible(reviewed)[0]['reading'],'れいさきじんじゃ')
        self.assertEqual(reviewed['entries'][0]['reading_raw'],'れいざきじんじゃ')
    def test_pending_source_observations_have_a_separate_actionable_release_list(self):
        import json
        from njd.__main__ import _review_lists
        d=a.dataset_from_observations(self.collection(),existing=None)
        d['collection']['observation_reviews']=[dict(status='needs_review',header_raw='例不明神社',url=a.INDEX,reason='reading absent')]
        with tempfile.TemporaryDirectory() as tmp:
            _review_lists(d,Path(tmp))
            entries=json.loads((Path(tmp)/'source-reviews.json').read_text())['sources']
            self.assertEqual(entries[0]['source_key'],'miyazaki_youth')
            self.assertEqual(entries[0]['observation_reviews'][0]['reason'],'reading absent')

class AssociationPrefectureScopeTests(unittest.TestCase):
    def test_explicit_other_prefecture_is_held_even_under_miyazaki_heading(self):
        result=a.inspect_index(page(card(address='福岡県例市例町1')))
        self.assertEqual(result['observations'],[])
        self.assertEqual(len(result['reviews']),1)

class AssociationReviewRegressionTests(unittest.TestCase):
    collection=AssociationCanonicalTests.collection
    def test_malformed_nested_urls_are_rejected_without_aborting_validation_or_render(self):
        from njd.validation import blocking_problems,eligible
        from njd.exporters import render
        for field in ['url','profile_url']:
            d=a.dataset_from_observations(self.collection(),existing=None)
            d['facilities'][0]['source_reference'][field]='https://['
            self.assertTrue(blocking_problems(d));self.assertEqual(eligible(d),[])
            self.assertEqual(render(d,'mozc').rows,0)
    def test_per_observation_unconfirmed_license_cannot_become_mit_or_wikipedia(self):
        from njd.validation import blocking_problems,eligible
        for license_url in ['https://opensource.org/license/mit','https://creativecommons.org/licenses/by-sa/4.0/deed.ja']:
            c=self.collection();c['observations'][0]['license_url']=license_url
            with self.assertRaises(ValueError):a.dataset_from_observations(c,existing=None)
            d=a.dataset_from_observations(self.collection(),existing=None)
            for ref in [d['facilities'][0]['source_reference'],*d['facilities'][0]['source_observations']]:ref['license_url']=license_url
            self.assertTrue(blocking_problems(d));self.assertEqual(eligible(d),[])
    def test_name_with_nontext_glyph_is_held_with_rendering_evidence(self):
        p=page(card().replace('例﨑神社','例<img src="/gaiji.png" alt="外字">﨑神社'))
        result=a.inspect_index(p)
        self.assertEqual(result['observations'],[])
        self.assertEqual(result['reviews'][0]['name_rendering_status'],'external_glyph')
        self.assertEqual(result['reviews'][0]['rendering_nodes'][0]['attributes']['src'],'/gaiji.png')
