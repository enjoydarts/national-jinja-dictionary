"""Synthetic duplicate publication rows; these fixtures are not real shrine evidence."""
import copy
from pathlib import Path
import tempfile
import unittest
from njd.records import build_dataset
from njd import source_aliases as a
from njd.validation import blocking_problems,eligible

DATE='2026-11-10T00:00:00+00:00'
URL='https://www.kochi-jinjyacho.com/%E9%AB%98%E7%9F%A5%E7%9C%8C%E7%A5%9E%E7%A4%BE%E4%B8%80%E8%A6%A7'

def data(reading="れいじんじゃ"):
    rows=[]
    for native,address,context,raw in [('00000000-0000-4000-8000-000000000001','高知県例市例町1','高知県例市','例町1'),('00000000-0000-4000-8000-000000000002','例市例町1','','例市例町1')]:
        rows.append(dict(name='例神社',reading_raw=reading,address=address,address_raw=raw,address_context=context,url=URL,
            source_id=native,fetched_at=DATE,page_hash='a'*64,locator='script#wix-warmup-data/'+native,evidence='例神社 れいじんじゃ '+address))
    return build_dataset('kochi','39','高知県','高知県神社庁',rows)

def document(d):
    p,s=d['facilities'];record=a.make_resolution(p,s,checked_at=DATE,reason='Synthetic exact-name/full-parcel two-schema publication duplicate.')
    return dict(schema_version=1,resolutions={s['id']:record})

class SourceAliasTests(unittest.TestCase):
    def test_resolved_duplicate_keeps_all_raw_records_and_one_physical_facility(self):
        from njd.report import _counts
        d=data();before=copy.deepcopy(d);out=a.apply_source_aliases(d,document(d))
        self.assertEqual(d,before);self.assertFalse(blocking_problems(out))
        self.assertEqual(len(out['facilities']),2);self.assertEqual(len(out['entries']),2)
        self.assertEqual(len(eligible(out)),1)
        self.assertEqual(out['facilities'][1]['source_alias_of'],d['facilities'][0]['id'])
        self.assertEqual(out['facilities'][1]['source_hash'],d['facilities'][1]['source_hash'])
        counts=_counts(out);self.assertEqual(counts['facilities'],1);self.assertEqual(counts['facility_records'],2);self.assertEqual(counts['source_alias_records'],1)
        self.assertEqual(out,a.apply_source_aliases(out,document(d)))
    def test_exact_name_full_parcel_and_opposite_publication_shapes_are_required(self):
        for changes in [dict(address='例市例町2',address_raw='例市例町2'),dict(name_raw='別神社',listed_name='別神社'),dict(address_context='高知県例市'),dict(source_key='other'),dict(address='例市例町',address_raw='例市例町')]:
            d=data();d['facilities'][1].update(changes)
            with self.assertRaises(ValueError):document(d)
    def test_stale_snapshot_holds_both_without_erasing_readings(self):
        d=data();doc=document(d);d['facilities'][1]['address']='例市例町2'
        out=a.apply_source_aliases(d,doc)
        self.assertEqual([f['status'] for f in out['facilities']],['pending','pending'])
        self.assertEqual([e['reading'] for e in out['entries']],['れいじんじゃ','れいじんじゃ'])
        self.assertNotIn('source_alias_of',out['facilities'][1]);self.assertEqual(eligible(out),[])
    def test_conflicting_verified_output_is_held_instead_of_discarded(self):
        d=data();doc=document(d);d['entries'][1]['reading']='べつじんじゃ'
        out=a.apply_source_aliases(d,doc)
        self.assertEqual([e['status'] for e in out['entries']],['pending','pending'])
        self.assertIn('conflict',out['entries'][1]['reason'])
    def test_explicit_prior_exclusion_is_preserved(self):
        d=data();doc=document(d);d['entries'][1].update(status='excluded',reason='Explicit user exclusion')
        out=a.apply_source_aliases(d,doc)
        self.assertEqual(out['entries'][1]['reason'],'Explicit user exclusion')
        self.assertEqual(out['entries'][1]['status'],'excluded')
    def test_forged_alias_metadata_is_a_validation_failure(self):
        d=data();d['facilities'][1]['source_alias_of']=d['facilities'][0]['id']
        self.assertTrue(blocking_problems(d));self.assertEqual(eligible(d),[])
    def test_chained_or_repeated_members_cannot_silently_merge_groups(self):
        d=data();doc=document(d);r=copy.deepcopy(next(iter(doc['resolutions'].values())));r['primary_id']=r['duplicate_id']
        doc['resolutions'][r['duplicate_id']]=r
        with self.assertRaises(ValueError):a.apply_source_aliases(d,doc)
    def test_missing_alias_is_not_a_reason_to_suppress_remaining_primary(self):
        d=data();doc=document(d);d['facilities']=d['facilities'][:1];d['entries']=d['entries'][:1]
        out=a.apply_source_aliases(d,doc)
        self.assertEqual(len(eligible(out)),1)

class SourceAliasIntegrationTests(unittest.TestCase):
    def test_cli_and_release_apply_saved_aliases_offline_and_preserve_management_rows(self):
        import json,zipfile
        from njd.storage import write_json
        from njd.nationwide import save_collection
        from njd.__main__ import _effective
        from legacy_release import create_release
        from njd.report import _counts
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);d=data();save_collection(root/'data','kochi',d);write_json(root/'data/source_aliases.json',document(d))
            self.assertEqual(_counts(_effective(root/'data', legacy=True))['facilities'],1)
            released=create_release(root/'data',root/'out','v-synthetic','a'*40)
            with zipfile.ZipFile(released['archive']) as z:
                self.assertIn('source_aliases.json',z.namelist())
                report=json.loads(z.read('report.json'));self.assertEqual(report['totals']['facilities'],1)
                self.assertEqual(report['totals']['facility_records'],2)
                self.assertIn('source_aliases.json',json.loads(z.read('SOURCE.json'))['data_files'])
                self.assertEqual(len(json.loads(z.read('national/json.json'))['entries']),2)
    def test_malformed_alias_markers_return_problems_instead_of_raising(self):
        for value in [{},[],7]:
            d=data();d['facilities'][1]['source_alias_of']=value
            self.assertTrue(blocking_problems(d))
    def test_orphan_entry_alias_cannot_suppress_or_relabel_a_facility(self):
        d=data();d['entries'][1]['source_alias_entry_of']='not-an-entry'
        self.assertTrue(blocking_problems(d))

class SourceAliasConsumerTests(unittest.TestCase):
    def test_import_sample_keeps_required_alias_context_without_adding_ime_words(self):
        from njd.report import samples
        from njd.exporters import render
        d=data();out=a.apply_source_aliases(d,document(d));sample=samples(out,maximum=1)
        self.assertFalse(blocking_problems(sample));self.assertEqual(render(sample,'mozc').rows,1)
        self.assertEqual(len(sample['entries']),2)
    def test_reading_research_skips_valid_resolved_duplicate_observations(self):
        from njd.wikipedia import pending_targets
        from njd.nationwide import save_collection
        from njd.storage import write_json
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);d=data('');save_collection(root,'kochi',d);write_json(root/'source_aliases.json',document(d))
            self.assertEqual(len(pending_targets(root,['39'])),1)
    def test_collection_manifest_counts_representatives_and_retains_raw_source(self):
        from njd.nationwide import save_collection,run_collections
        from njd.storage import write_json,load_dataset
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);canonical=root/'data';d=data();save_collection(canonical,'kochi',d);write_json(canonical/'source_aliases.json',document(d))
            states=run_collections(canonical,dict(kochi=dict(code='39',collect=lambda client,limit=None:d)),['kochi'],cache_dir=root/'cache')
            self.assertEqual(states['39']['facilities'],1);self.assertEqual(states['39']['facility_records'],2)
            self.assertEqual(len(load_dataset(canonical/'sources/kochi.json')['facilities']),2)

class SourceAliasOutputPreservationTests(unittest.TestCase):
    def test_source_aliases_do_not_change_ime_word_bytes(self):
        from njd.exporters import render
        d=data();out=a.apply_source_aliases(d,document(d))
        for format_name in ['mozc','macos']:
            self.assertEqual(render(d,format_name).content,render(out,format_name).content)
    def test_primary_user_exclusion_is_not_revived_by_duplicate_observation(self):
        d=data();doc=document(d);d['entries'][0].update(status='excluded',reason='Explicit primary user exclusion')
        out=a.apply_source_aliases(d,doc)
        self.assertEqual(out['entries'][0]['status'],'excluded');self.assertEqual(out['entries'][0]['reason'],'Explicit primary user exclusion')
        self.assertEqual(out['entries'][1]['status'],'pending');self.assertEqual(eligible(out),[])

class SourceAliasCliCountTests(unittest.TestCase):
    def test_validate_distinguishes_facilities_from_original_management_records(self):
        import contextlib,io,json
        from njd.__main__ import main
        from njd.nationwide import save_collection
        from njd.storage import write_json
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);d=data();save_collection(root/'data','kochi',d);write_json(root/'data/source_aliases.json',document(d));output=io.StringIO()
            from njd.canonical import migrate
            migrate(root/'data', root/'canonical')
            with contextlib.redirect_stdout(output):rc=main(['--data-dir',str(root/'canonical'),'--output-dir',str(root/'out'),'validate'])
            result=json.loads(output.getvalue());self.assertEqual(rc,0)
            self.assertEqual(result['facilities'],1);self.assertEqual(result['facility_records'],2)

class SourceAliasReviewRegressionTests(unittest.TestCase):
    def test_explicit_pending_decision_keeps_its_reason_and_holds_representative(self):
        from njd.storage import apply_decisions
        d=data();doc=document(d);e=d['entries'][1]
        decided=apply_decisions(d,{e['id']:dict(expected_source_hash=e['source_hash'],status='pending',reason='Human: identity must be checked')})
        out=a.apply_source_aliases(decided,doc)
        self.assertEqual(out['entries'][1]['status'],'pending')
        self.assertEqual(out['entries'][1]['reason'],'Human: identity must be checked')
        self.assertEqual(out['entries'][0]['status'],'pending');self.assertEqual(eligible(out),[])
    def test_same_text_as_default_still_preserves_explicit_pending_file_decision(self):
        from njd.storage import write_json
        from njd.nationwide import save_collection
        from njd.__main__ import _effective
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);d=data('');save_collection(root,'kochi',d);write_json(root/'source_aliases.json',document(d));e=d['entries'][1]
            write_json(root/'decisions.json',{e['id']:dict(expected_source_hash=e['source_hash'],status='pending',reason='missing agency reading')})
            out=_effective(root, legacy=True)
            by_id={x['id']:x for x in out['entries']};facilities={x['id']:x for x in out['facilities']}
            self.assertEqual(by_id[e['id']]['status'],'pending');self.assertNotIn('source_alias_of',facilities[e['facility_id']])
    def test_each_source_witness_field_is_bound_to_the_inspected_observation(self):
        for field,value in [('url',URL+'?comp-ljqfjyd6_page=999'),('locator','arbitrary/'+data()['facilities'][0]['native_source_id']),('page_hash','0'*64),('fetched_at','2026-01-01T00:00:00+00:00')]:
            d=data();doc=document(d);record=next(iter(doc['resolutions'].values()));record['evidence'][0][field]=value
            out=a.apply_source_aliases(d,doc)
            self.assertEqual([f['status'] for f in out['facilities']],['pending','pending'])
            self.assertNotIn('source_alias_of',out['facilities'][1])
    def test_missing_required_ids_produce_validation_errors_without_crashing(self):
        for kind,field in [('facilities','id'),('entries','id'),('entries','facility_id')]:
            d=data();bad_id=d[kind][0].get('id');d[kind][0].pop(field)
            self.assertTrue(blocking_problems(d))
            accepted=eligible(d)
            if field=='facility_id':
                self.assertEqual(len(accepted),1);self.assertNotIn(bad_id,{e['id'] for e in accepted})
            else:self.assertEqual(accepted,[])
