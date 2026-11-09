import copy
import unittest
from test_records import build, row
from njd import reviews
from njd.validation import eligible, blocking_problems
from njd.storage import apply_decisions


def decision(data, outputs, **extra):
    f=data['facilities'][0];e=data['entries'][0]
    item=dict(case_id='synthetic-review',facility_id=f['id'],expected_source_hash=e['source_hash'],
        original={k:v for k,v in dict(name_raw=f['name_raw'],reading_raw=e['reading_raw'],address=f['address'],listing_url=f['listing_url']).items()},
        confirmation='user_confirmation',recorded_at='2026-11-09T12:00:00+09:00',
        reason='Explicit synthetic user judgment',outputs=outputs,**extra)
    return dict(schema_version=1,entries={e['id']:item})


class ReviewsTest(unittest.TestCase):
    def test_user_reading_has_no_fabricated_page_and_preserves_raw(self):
        d=build([row(reading_raw='')]);before=copy.deepcopy(d)
        doc=decision(d,[dict(surface='架空神社',reading='かくうじんじゃ',basis='user_confirmation',reading_url='')])
        out=reviews.apply_reviews(d,doc)
        self.assertEqual(d,before)
        self.assertEqual(blocking_problems(out),[])
        self.assertEqual(len(eligible(out)),1)
        e=eligible(out)[0]
        self.assertEqual((e['reading_raw'],e['reading_url'],e['reading_source_kind']),('','','user_review'))
        e['reading']='べつのよみ'
        self.assertEqual(eligible(out),[])

    def test_split_retains_one_facility_and_stable_entries(self):
        d=build([row(name='架空神社 別神社',reading_raw='かくうじんじゃ べつじんじゃ')])
        outputs=[dict(surface=s,reading=r,basis='agency_component',reading_url=d['facilities'][0]['listing_url']) for s,r in [('架空神社','かくうじんじゃ'),('別神社','べつじんじゃ')]]
        doc=decision(d,outputs,split=True,excluded_name_prefix='',excluded_reading_prefix='')
        out=reviews.apply_reviews(d,doc)
        self.assertEqual(blocking_problems(out),[])
        self.assertEqual(len(out['facilities']),1)
        self.assertEqual(len(eligible(out)),2)
        self.assertEqual(out['entries'][0]['status'],'excluded')
        self.assertTrue(all(e['reading_raw']==d['entries'][0]['reading_raw'] for e in out['entries']))
        self.assertEqual(out,reviews.apply_reviews(d,doc))
        eid=eligible(out)[0]['id']
        self.assertEqual(len(eligible(apply_decisions(out,{eid:dict(expected_source_hash=d['entries'][0]['source_hash'],status='excluded',reason='manual exclusion')}))),1)
        doc['entries'][d['entries'][0]['id']]['outputs'][0]['reading']='かくう'
        self.assertEqual(eligible(reviews.apply_reviews(d,doc)),[])

    def test_stale_source_and_unconfirmed_authority_remain_pending(self):
        d=build([row(reading_raw='')])
        doc=decision(d,[dict(surface='架空神社',reading='かくうじんじゃ',basis='user_confirmation',reading_url='')])
        changed=build([row(reading_raw='不明')])
        self.assertEqual(eligible(reviews.apply_reviews(changed,doc)),[])
        d['collection']['authority_status']='pending'
        self.assertEqual(eligible(reviews.apply_reviews(d,doc)),[])

    def test_user_reading_does_not_resolve_identity_or_multiline_address(self):
        for source_row in [row(reading_raw='',review_reason='source identity conflict'),row(reading_raw='',address='架空市1\n架空市2')]:
            d=build([source_row]);doc=decision(d,[dict(surface='架空神社',reading='かくうじんじゃ',basis='user_confirmation',reading_url='')])
            self.assertEqual(eligible(reviews.apply_reviews(d,doc)),[])

    def test_reference_reading_must_be_literal_and_identity_bound(self):
        d=build([row(reading_raw='')]);f=d['facilities'][0]
        ref=dict(url='https://example.invalid/reference',name_raw='架空神社',reading_raw='カクウジンジャ',address_raw=f['address'],title='Synthetic reference',source_kind='reference',checked_at='2026-11-09T12:00:00+09:00',excerpt='架空神社 カクウジンジャ '+f['address'])
        doc=decision(d,[dict(surface='架空神社',reading='かくうじんじゃ',basis='reference',reading_url=ref['url'])],references=[ref])
        self.assertEqual(len(eligible(reviews.apply_reviews(d,doc))),1)
        ref['reading_raw']='カクウ';doc['entries'][d['entries'][0]['id']]['references']=[ref]
        self.assertEqual(eligible(reviews.apply_reviews(d,doc)),[])

    def test_explicit_orthography_edit_preserves_reference_literal(self):
        d=build([row(reading_raw='')]);f=d['facilities'][0]
        ref=dict(url='https://example.invalid/reference',name_raw='架空神社',reading_raw='カクウジンジヤ',address_raw=f['address'],title='Synthetic reference',source_kind='reference',checked_at='2026-11-09T12:00:00+09:00',excerpt='架空神社 カクウジンジヤ '+f['address'])
        output=dict(surface='架空神社',reading='かくうじんじゃ',basis='editorial_normalization',reading_url=ref['url'],source_reading_raw='カクウジンジヤ',edits=[dict(index=6,old='や',new='ゃ')])
        doc=decision(d,[output],references=[ref])
        out=reviews.apply_reviews(d,doc)
        self.assertEqual(len(eligible(out)),1)
        self.assertEqual(eligible(out)[0]['human_review']['references'][0]['reading_raw'],'カクウジンジヤ')
        output['edits'][0]['index']=4
        self.assertEqual(eligible(reviews.apply_reviews(d,doc)),[])

    def test_reading_conflict_resolution_cannot_resolve_other_name_or_address(self):
        d=build([row(),row(reading_raw='ベツヨミ')]);f=d['facilities'][0]
        doc=decision(d,[dict(surface='架空神社',reading='かくうじんじゃ',basis='agency_selected',reading_url=f['listing_url'])],resolved_reading_conflicts=copy.deepcopy(f['source_conflicts']))
        out=reviews.apply_reviews(d,doc)
        self.assertEqual(len(eligible(out)),1)
        self.assertEqual(out['facilities'][0]['source_conflicts'],f['source_conflicts'])
        f['source_conflicts'][0]['address']='架空市別町2'
        doc['entries'][d['entries'][0]['id']]['resolved_reading_conflicts']=copy.deepcopy(f['source_conflicts'])
        self.assertEqual(eligible(reviews.apply_reviews(d,doc)),[])

    def test_release_bundles_human_decisions_and_tracks_their_content(self):
        import tempfile
        import zipfile
        import json
        import hashlib
        from pathlib import Path
        from njd.nationwide import save_collection
        from njd.storage import write_json
        from njd.release import create_release
        with tempfile.TemporaryDirectory() as td:
            data=Path(td)/'data';d=build([row(reading_raw='')]);save_collection(data,'example',d)
            doc=decision(d,[dict(surface='架空神社',reading='かくうじんじゃ',basis='user_confirmation',reading_url='')])
            write_json(data/'reviews.json',doc)
            result=create_release(data,Path(td)/'dist','review-test','a'*40)
            with zipfile.ZipFile(result['archive']) as z:
                self.assertEqual(z.read('national/mozc.txt').decode(),'かくうじんじゃ\t架空神社\t固有名詞\n')
                self.assertEqual(json.loads(z.read('reviews.json')),doc)
                self.assertEqual(json.loads(z.read('SOURCE.json'))['data_files']['reviews.json'],hashlib.sha256((data/'reviews.json').read_bytes()).hexdigest())
