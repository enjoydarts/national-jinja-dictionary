"""Reference-only eligibility is explicit and cannot masquerade as agency evidence."""
import copy
import unittest
from urllib.parse import quote
from njd import reference_sources as r
from njd.exporters import render
from njd.validation import eligible,blocking_problems


def reference(name='例神社',reading='れいじんじゃ',address='広島県例市例町1',article_id=10):
    from njd.wikipedia import wiki_url
    url=wiki_url(name+' (例市)')
    return dict(url=url,title=name+' (例市)',name_raw=name,reading_raw=reading,address_raw=address,
        excerpt=name+'（'+reading+'） / '+address,source_kind='encyclopedia',
        article_id=article_id,revision_id=1234,permalink='https://ja.wikipedia.org/w/index.php?title='+quote(name+' (例市)')+'&oldid=1234',
        page_hash='a'*64,checked_at='2026-11-10T00:00:00+00:00',license_url=r.LICENSE,
        shrine_type_label_raw='主祭神',locator='lead paragraph and shrine infobox')


class ReferenceSourceTests(unittest.TestCase):
    def test_explicit_reference_basis_preserves_source_and_is_not_agency_claim(self):
        ref=reference();d=r.dataset_from_references('34',[ref]);f=d['facilities'][0];e=d['entries'][0]
        self.assertEqual(f['listing_basis'],'wikipedia_reference')
        self.assertNotIn('agency',f)
        self.assertEqual(e['reading_source_kind'],'encyclopedia')
        self.assertEqual(f['source_reference'],ref)
        self.assertEqual((e['surface'],e['reading']),('例神社','れいじんじゃ'))
        self.assertFalse(d['collection']['official_agency_listing_verified'])
        self.assertEqual(len(eligible(d)),1);self.assertFalse(blocking_problems(d))

    def test_missing_evidence_wrong_prefecture_and_non_shrine_are_rejected(self):
        variants=[]
        for key in ['revision_id','article_id','license_url','permalink','page_hash','shrine_type_label_raw']:
            v=reference();v.pop(key);variants.append(v)
        for changes in [dict(address_raw='山口県例市例町1'),dict(source_kind='agency'),
                        dict(shrine_type_label_raw='本尊'),dict(reading_raw='れい'),
                        dict(url='https://other.example/wiki/例神社'),dict(revision_id=True)]:
            v=reference();v.update(changes);variants.append(v)
        for v in variants:
            with self.subTest(value=v),self.assertRaises(ValueError):r.dataset_from_references('34',[v])
        with self.assertRaises(ValueError):r.dataset_from_references('01',[reference()])

    def test_reference_fallback_supports_the_remaining_four_unavailable_agency_regions(self):
        for code,prefecture in [('30','和歌山県'),('36','徳島県'),('44','大分県'),('45','宮崎県')]:
            with self.subTest(code=code):
                d=r.dataset_from_references(code,[reference(address=prefecture+'例市例町1')])
                self.assertEqual(len(eligible(d)),1)
                self.assertEqual(d['facilities'][0]['prefecture_code'],code)
                self.assertFalse(d['collection']['official_agency_listing_verified'])

    def test_missing_prefecture_in_infobox_requires_matching_primary_lead_location(self):
        from njd.http import Page
        def page(prefecture='広島県',city='例市',clause='にある神社'):
            body=('<script>{"wgRevisionId":1234,"wgArticleId":10}</script>'
                  '<div class="mw-parser-output"><section data-mw-section-id="0">'
                  '<table class="infobox"><tr><th>例神社</th></tr><tr><th>主祭神</th><td>例</td></tr>'
                  '<tr><th>所在地</th><td>例市例町1</td></tr></table>'
                  '<p><b>例神社</b>（れいじんじゃ）は、'+prefecture+city+clause+'。</p></section></div>')
            return Page(reference()['url'],200,{'content-type':'text/html'},body.encode(),'2026-11-10T00:00:00+00:00')
        ref=r.inspect_article(page(),'34');d=r.dataset_from_references('34',[ref])
        self.assertEqual(d['facilities'][0]['address'],'例市例町1')
        self.assertEqual(ref['address_raw'],'例市例町1')
        self.assertEqual(ref['prefecture_context_raw'],'広島県')
        self.assertEqual(ref['municipality_context_raw'],'例市')
        self.assertEqual(len(eligible(d)),1)
        original=page();annotated=Page(original.url,200,original.headers,original.text.replace('（れいじんじゃ）','（れいじんじゃ、別神社）').encode(),original.fetched_at)
        self.assertEqual(r.inspect_article(annotated,'34')['reading_raw'],'れいじんじゃ')
        ruby=r.inspect_article(page(city='例市例町（れいまち）'),'34')
        self.assertIn('例町（れいまち）',ruby['location_context_excerpt'])
        for wrong in [page('山口県'),page(city='別市'),
                      page(clause='ではなく山口県別市にある神社'),page(clause='ではなく同県別市にある神社'),
                      page(clause='から離れた別市にある神社'),page(clause='（ではなく）にある神社'),
                      page(clause='にあるのではなく山口県別市にある神社'),
                      page(clause='にある神社ではなく山口県別市にある神社')]:
            with self.assertRaises(ValueError):r.inspect_article(wrong,'34')
        bad=copy.deepcopy(d);bad['facilities'][0]['source_reference'].pop('prefecture_context_raw')
        self.assertTrue(blocking_problems(bad))

    def test_explicit_shrine_template_can_establish_type_without_a_deity_row(self):
        import json
        from html import escape
        from njd.http import Page
        for template,expected in [('神社',True),('寺院',False),('公園',False),('神社の一覧',False)]:
            metadata=json.dumps({'parts':[{'template':{'target':{'wt':template+'\n','href':'./Template:'+template},'params':{}}}]},ensure_ascii=False)
            html=('<script>{"wgRevisionId":1234,"wgArticleId":10}</script><div class="mw-parser-output"><section data-mw-section-id="0">'
                  '<table class="infobox" data-mw="'+escape(metadata,quote=True)+'"><tr><th>例神社</th></tr>'
                  '<tr><th>所在地</th><td>広島県例市例町1</td></tr></table><p><b>例神社</b>（れいじんじゃ）は広島県例市にある神社。</p></section></div>')
            page=Page(reference()['url'],200,{'content-type':'text/html'},html.encode(),'2026-11-10T00:00:00+00:00')
            if expected:
                ref=r.inspect_article(page,'34');self.assertEqual(ref['shrine_type_template_raw'],'神社')
                self.assertNotIn('shrine_type_label_raw',ref)
                self.assertEqual(len(eligible(r.dataset_from_references('34',[ref]))),1)
            else:
                with self.assertRaises(ValueError):r.inspect_article(page,'34')

    def test_postal_prefix_preserves_address_and_parses_municipality(self):
        v=reference(address='〒730-0000 広島県例市例町1')
        d=r.dataset_from_references('34',[v])
        self.assertEqual(d['facilities'][0]['address'],v['address_raw'])
        self.assertEqual(d['facilities'][0]['municipality'],'例市')
        self.assertEqual(len(eligible(d)),1)
        for wrong in ['〒730-0000 山口県例市例町1','〒730-000 広島県例市例町1']:
            with self.subTest(address=wrong),self.assertRaises(ValueError):r.dataset_from_references('34',[reference(address=wrong)])

    def test_source_explicit_sha_and_guu_endings_are_not_replaced_by_standard_suffix_guesses(self):
        for name,reading in [('例大神社','れいおおみわしゃ'),('例神宮','れいぜんぐう')]:
            d=r.dataset_from_references('34',[reference(name=name,reading=reading)])
            self.assertEqual(d['entries'][0]['reading'],reading)
            self.assertEqual(len(eligible(d)),1)
        for name,reading in [('例大神社','れいおおみわ'),('例神宮','れいぜん')]:
            with self.assertRaises(ValueError):r.dataset_from_references('34',[reference(name=name,reading=reading)])

    def test_individually_reviewed_facilities_in_one_article_are_not_merged(self):
        a=reference();b=reference(address='広島県例市別町2')
        for v in [a,b]:v.update(acquisition_method='individual_source_review',facility_scope='individual_facility',section_locator='individual shrine section and its own infobox')
        d=r.dataset_from_references('34',[a,b]);self.assertEqual(len(d['facilities']),2)
        self.assertEqual(len({f['native_source_id'] for f in d['facilities']}),2)
        self.assertTrue(all(f['curated_source_record'] for f in d['facilities']))
        corrupted=copy.deepcopy(d);corrupted['facilities'][0]['curated_source_record']=False
        self.assertTrue(blocking_problems(corrupted))
        self.assertEqual(render(d,'mozc').rows,1)
        old=r.dataset_from_references('34',[reference()])
        self.assertEqual(old['facilities'][0]['native_source_id'],'wikipedia:pageid:10')
        for key in ['acquisition_method','section_locator']:
            v=copy.deepcopy(a);v.pop(key)
            with self.assertRaises(ValueError):r.dataset_from_references('34',[v])

    def test_individual_scope_cannot_duplicate_an_article_wide_record_or_crash_on_missing_raw_fields(self):
        a=reference();a.update(acquisition_method='individual_source_review',facility_scope='individual_facility',section_locator='own source infobox')
        with self.assertRaises(ValueError):r.dataset_from_references('34',[a,reference()])
        d=r.dataset_from_references('34',[a]);d['facilities'][0]['source_reference'].pop('name_raw')
        self.assertTrue(blocking_problems(d))

    def test_assembled_candidates_cannot_save_the_same_article_facility_under_two_scopes(self):
        import tempfile
        from pathlib import Path
        from njd.nationwide import save_collection
        a=r.dataset_from_references('34',[reference()])
        ref=reference();ref.update(acquisition_method='individual_source_review',facility_scope='individual_facility',section_locator='own source infobox')
        b=r.dataset_from_references('34',[ref]);mixed=copy.deepcopy(a)
        mixed['facilities']+=b['facilities'];mixed['entries']+=b['entries']
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);save_collection(root,'hiroshima',a);path=root/'sources/hiroshima.json';before=path.read_bytes()
            with self.assertRaises(ValueError):save_collection(root,'hiroshima',mixed)
            self.assertEqual(path.read_bytes(),before)
        self.assertTrue(blocking_problems(mixed))
        self.assertIsNone(render(mixed,'mozc').content)

    def test_individual_body_review_requires_the_exact_affirmative_shrine_location_statement(self):
        v=reference();v.pop('shrine_type_label_raw');v['acquisition_method']='individual_source_review'
        statement='例神社（れいじんじゃ）は、広島県例市例町にある神社。'
        v.update(shrine_type_statement_raw=statement,excerpt=v['excerpt']+' / '+statement)
        d=r.dataset_from_references('34',[v]);self.assertEqual(len(eligible(d)),1)
        for text in ['例神社（れいじんじゃ）は、広島県別市にある神社。',
                     '例神社（れいじんじゃ）は、広島県例市にある神社の鳥居。',
                     '例神社（れいじんじゃ）は、広島県例市にあった神社。',
                     '例神社（れいじんじゃ）は、広島県例市にあるのではなく山口県別市にある神社。']:
            bad=copy.deepcopy(v);bad.update(shrine_type_statement_raw=text,excerpt=v['excerpt']+' / '+text)
            with self.subTest(text=text),self.assertRaises(ValueError):r.dataset_from_references('34',[bad])

    def test_same_name_different_article_and_address_retains_two_facilities(self):
        d=r.dataset_from_references('34',[reference(),reference(address='広島県例市別町2',article_id=11)])
        self.assertEqual(len(d['facilities']),2)
        self.assertEqual(len({f['id'] for f in d['facilities']}),2)
        out=render(d,'mozc');self.assertEqual(out.rows,1);self.assertEqual(out.deduplicated,1)

    def test_redirect_aliases_of_the_same_article_keep_one_facility_and_both_sources(self):
        a=reference();b=reference();b.update(url='https://ja.wikipedia.org/wiki/別題',title='別題',
            permalink='https://ja.wikipedia.org/w/index.php?title='+quote('別題')+'&oldid=1234',page_hash='b'*64)
        d=r.dataset_from_references('34',[a,b])
        self.assertEqual(len(d['facilities']),1);self.assertEqual(len(d['entries']),1)
        f=d['facilities'][0];self.assertEqual(f['source_reference'],a)
        self.assertEqual(f['additional_source_references'],[b])
        self.assertEqual(len(f['listing_occurrences']),2)
        self.assertEqual(render(d,'mozc').rows,1);self.assertFalse(blocking_problems(d))
        f['additional_source_references'][0]['address_raw']='広島県別市1'
        self.assertTrue(blocking_problems(d))

    def test_corrupt_redirect_observation_metadata_is_rejected_without_type_errors(self):
        a=reference();b=reference();b.update(url='https://ja.wikipedia.org/wiki/別題',title='別題',
            permalink='https://ja.wikipedia.org/w/index.php?title='+quote('別題')+'&oldid=1234',page_hash='b'*64)
        for field,value in [('page_hash',[]),('checked_at',{}),('url',[])]:
            d=r.dataset_from_references('34',[a,b]);d['facilities'][0]['additional_source_references'][0][field]=value
            with self.subTest(field=field):self.assertTrue(blocking_problems(d))
        d=r.dataset_from_references('34',[a,b]);d['facilities'][0]['listing_occurrences'][0]['page_hash']=[]
        self.assertTrue(blocking_problems(d))

    def test_id_survives_revision_changes_and_raw_reading_is_mechanically_normalized(self):
        v=reference(reading='レイジンジャ');d=r.dataset_from_references('34',[v])
        other=reference(reading='レイジンジャ');other.update(revision_id=1235,permalink=v['permalink'].replace('1234','1235'))
        b=r.dataset_from_references('34',[other])
        self.assertEqual(d['facilities'][0]['id'],b['facilities'][0]['id'])
        self.assertEqual(d['entries'][0]['reading_raw'],'レイジンジャ')
        self.assertEqual(d['entries'][0]['reading'],'れいじんじゃ')

    def test_missing_license_revision_and_mislabelled_basis_cannot_enter_ime(self):
        for change in ['license','revision','basis','agency','raw']:
            d=r.dataset_from_references('34',[reference()]);f=d['facilities'][0]
            if change=='license':f['source_reference'].pop('license_url')
            if change=='revision':f['source_reference']['revision_id']=0
            if change=='basis':d['collection']['listing_basis']='agency'
            if change=='agency':f['agency']='広島県神社庁'
            if change=='raw':f['source_reference']['reading_raw']='べつじんじゃ'
            with self.subTest(change=change):
                self.assertTrue(blocking_problems(d));self.assertEqual(render(d,'mozc').rows,0)

    def test_corrupt_nested_evidence_is_rejected_without_crashing_validation(self):
        for value in ['broken',17,[],None]:
            d=r.dataset_from_references('34',[reference()]);d['facilities'][0]['source_reference']=value
            with self.subTest(value=value):
                self.assertTrue(blocking_problems(d));self.assertEqual(render(d,'mozc').rows,0)
        for changes in [dict(url='https://['),dict(url=17),dict(address_raw=None),dict(page_hash=[]),dict(permalink='https://[')]:
            ref=reference();ref.update(changes)
            with self.subTest(changes=changes),self.assertRaises(ValueError):r.dataset_from_references('34',[ref])

    def test_offline_release_distinguishes_basis_and_ships_wikipedia_attribution(self):
        import json,tempfile,zipfile
        from pathlib import Path
        from unittest.mock import patch
        from njd.nationwide import save_collection
        from legacy_release import create_release
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);save_collection(root/'data','hiroshima',r.dataset_from_references('34',[reference()]))
            with patch('njd.http.request',side_effect=AssertionError('offline release')):
                result=create_release(root/'data',root/'out','v0.2.0','a'*40)
            with zipfile.ZipFile(result['archive']) as z:
                report=json.loads(z.read('report.json'))
                self.assertEqual(report['totals']['source_basis_counts']['wikipedia_reference']['facilities'],1)
                notes=z.read('README.md').decode()
                self.assertIn('Wikipedia',notes);self.assertIn('参考資料',notes)
                self.assertIn('reference',report['prefectures'][33]['reason'])
                self.assertNotIn('official listing records',report['prefectures'][33]['reason'])
                credits=json.loads(z.read('ATTRIBUTION.json'))['wikipedia']
                self.assertEqual(len(credits),1);self.assertEqual(credits[0]['revision_id'],1234)
                self.assertEqual(credits[0]['license_url'],r.LICENSE)
                self.assertEqual(credits[0]['permalink'],reference()['permalink'])

    def test_collection_checkpoints_and_resumes_without_refetch_or_canonical_writes(self):
        import tempfile,json
        from pathlib import Path
        from njd.http import Page,FetchError
        from njd.wikipedia import wiki_url
        root_url=wiki_url('Category:広島県の神社');a=reference()['url'];b=wiki_url('別例神社 (例市)')
        def body(name,address,article_id):
            return ('<script>{"wgRevisionId":1234,"wgArticleId":'+str(article_id)+'}</script>'
                    '<div class="mw-parser-output"><section data-mw-section-id="0">'
                    '<table class="infobox"><tr><th>'+name+'</th></tr><tr><th>主祭神</th><td>例</td></tr>'
                    '<tr><th>所在地</th><td>'+address+'</td></tr></table><p><b>'+name+'</b>（れいじんじゃ）は神社。</p></section></div>')
        pages={root_url:'<div id="mw-pages"><a href="'+a+'">例神社</a><a href="'+b+'">別例神社</a></div>',
               a:body('例神社','広島県例市例町1',10),b:body('別例神社','広島県例市別町2',11)}
        class Client:
            def __init__(self):self.calls=[]
            def fetch(self,url,**kwargs):
                self.calls.append(url)
                if url not in pages:raise FetchError('fixture unavailable')
                return Page(url,200,{'content-type':'text/html'},pages[url].encode(),'2026-11-10T00:00:00+00:00')
        with tempfile.TemporaryDirectory() as tmp:
            client=Client();state=Path(tmp)/'research'
            first=r.research('34',state,client,limit=1)
            self.assertFalse(first['complete']);self.assertEqual(first['unvisited'],1)
            second=r.research('34',state,client)
            self.assertTrue(second['complete']);self.assertEqual(second['facilities'],2)
            calls=list(client.calls);r.research('34',state,client);self.assertEqual(client.calls,calls)
            candidate=json.loads((state/'candidate.json').read_text())
            self.assertEqual(len(candidate['facilities']),2)
            self.assertFalse((state/'sources').exists())
            with self.assertRaises(ValueError):r.research('35',state,client)

    def test_fetch_failure_stops_and_private_paths_stay_out_of_public_candidate(self):
        import tempfile,json
        from pathlib import Path
        from njd.http import Page,FetchError
        from njd.wikipedia import wiki_url
        from njd.nationwide import ensure_public_metadata
        root_url=wiki_url('Category:広島県の神社');a=reference()['url'];b=wiki_url('別例神社')
        class Client:
            def __init__(self):self.calls=[]
            def fetch(self,url,**kwargs):
                self.calls.append(url)
                if url!=root_url:raise FetchError('failed at /private/tmp/private-cache/file')
                body='<div id="mw-pages"><a href="'+a+'">a</a><a href="'+b+'">b</a></div>'
                return Page(url,200,{'content-type':'text/html'},body.encode(),'2026-11-10T00:00:00+00:00')
        with tempfile.TemporaryDirectory() as tmp:
            client=Client();result=r.research('34',Path(tmp)/'research',client)
            self.assertFalse(result['complete']);self.assertEqual(result['fetch_errors'],1)
            self.assertEqual(result['unvisited'],2)
            self.assertEqual(len(client.calls),2)
            candidate=json.loads((Path(tmp)/'research/candidate.json').read_text())
            self.assertEqual(candidate['collection']['articles_inspected'],0)
            self.assertEqual(set(candidate['collection']['remaining_scope']),{a,b})
            self.assertNotIn('/private/tmp/private-cache',json.dumps(candidate))
            ensure_public_metadata(candidate)

    def test_relabelling_every_basis_flag_cannot_hide_wikipedia_provenance(self):
        d=r.dataset_from_references('34',[reference()]);f=d['facilities'][0];e=d['entries'][0]
        d['collection'].update(listing_basis='agency',official_agency_listing_verified=True)
        f.update(listing_basis='agency',agency='広島県神社庁');e['reading_source_kind']='agency'
        self.assertTrue(blocking_problems(d));self.assertEqual(render(d,'mozc').rows,0)

    def test_reading_url_must_identify_the_inspected_article_or_its_revision(self):
        d=r.dataset_from_references('34',[reference()]);e=d['entries'][0]
        e['reading_url']='https://uninspected.example/article'
        self.assertTrue(blocking_problems(d));self.assertEqual(render(d,'mozc').rows,0)
        e['reading_url']=reference()['permalink']
        self.assertFalse(blocking_problems(d));self.assertEqual(render(d,'mozc').rows,1)

    def test_sha_stem_and_combined_shrine_names_require_individual_review(self):
        for ref in [reference(name='例社',reading='れい'),reference(name='例神社・別宮',reading='れいべつみや')]:
            with self.subTest(name=ref['name_raw']),self.assertRaises(ValueError):r.dataset_from_references('34',[ref])
        d=r.dataset_from_references('34',[reference(name='例社',reading='れいしゃ')])
        self.assertEqual(len(eligible(d)),1)

    def test_repeated_render_is_deterministic_and_keeps_attribution_in_management_data(self):
        d=r.dataset_from_references('34',[reference()]);before=copy.deepcopy(d)
        for fmt in ['mozc','macos','json','csv']:
            self.assertEqual(render(d,fmt).content,render(d,fmt).content)
        self.assertIn(r.LICENSE.encode(),render(d,'json').content)
        self.assertNotIn(b'wikipedia',render(d,'mozc').content)
        self.assertEqual(before,d)
