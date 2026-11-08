"""Synthetic records only; these are not shrine evidence or dictionary data."""
import copy
import tempfile
import unittest
from pathlib import Path
from njd.normalize import normalize_reading
from njd.validation import validate, eligible
from njd.storage import save_dataset, load_dataset, apply_decisions
from njd.adapters.gunma import parse

HTML = '''<section id="test"><table><thead><tr><th>神社名</th><th>カナ</th><th>所在地</th><th>連絡先</th></tr></thead><tbody>
<tr><th>試驗神社</th><td>ｼｹﾝｼﾞﾝｼﾞｬ</td><td>架空市甲町1</td><td rowspan="2">000</td></tr>
<tr><th>試驗神社</th><td>ｼｹﾝｼﾞﾝｼﾞｬ</td><td>架空市乙町2</td></tr>
<tr><th>未確認社</th><td></td><td>架空市丙町3</td></tr></tbody></table></section>'''

def dataset():
    return parse(HTML, '2026-11-08T00:00:00+00:00', 'a'*64)

class NormalizeTest(unittest.TestCase):
    def test_mechanical_only(self):
        self.assertEqual(normalize_reading('ｼｹﾝｼﾞﾝｼﾞｬ'), 'しけんじんじゃ')
        self.assertEqual(normalize_reading('シケンじんじゃ'), 'しけんじんじゃ')
        for raw in ['し けん', '神社', 'shiken', 'し\nけん', 'し\tけん', 'し\u200bけん', 'ヷ', '']:
            with self.subTest(raw=raw), self.assertRaises(ValueError): normalize_reading(raw)

class ParseTest(unittest.TestCase):
    def test_rowspan_and_same_name_different_address(self):
        d = dataset()
        self.assertEqual(len(d['facilities']), 3)
        self.assertEqual(len({f['id'] for f in d['facilities']}), 3)
        self.assertEqual(d['entries'][0]['surface'], '試驗神社')
        self.assertEqual(d['entries'][0]['reading_raw'], 'ｼｹﾝｼﾞﾝｼﾞｬ')
        self.assertEqual(d['facilities'][1]['address'], '架空市乙町2')
        self.assertEqual(len(eligible(d)), 2)
        self.assertEqual(d['entries'][2]['status'], 'pending')
        self.assertEqual([x['id'] for x in d['facilities']], [x['id'] for x in dataset()['facilities']])
    def test_changed_structure_fails_closed(self):
        with self.assertRaises(ValueError): parse('<table><tr><th>試験</th><td>かな</td></tr></table>', '2026-11-08', 'a'*64)
    def test_branch_information_row_is_not_a_facility(self):
        html=HTML.replace('</tbody>', '<tr><th>架空支部</th><td></td><td></td><td>支部リンク</td></tr></tbody>')
        d=parse(html,'2026-11-08','a'*64)
        self.assertEqual(len(d['facilities']),3)
        self.assertEqual(len(d['collection']['non_facility_rows']),1)
    def test_unrelated_tables_not_ingested(self):
        html=HTML+'<table><tr><th>観光情報</th><td>かな</td><td>架空市甲1</td></tr></table>'
        self.assertEqual(len(parse(html,'2026-11-08','a'*64)['facilities']),3)
    def test_scope_limit(self):
        self.assertEqual(len(parse(HTML, '2026-11-08', 'a'*64, limit=1)['facilities']), 1)

class ValidationTest(unittest.TestCase):
    def test_missing_evidence_never_exports(self):
        d = dataset(); d['entries'][0]['evidence'] = ''
        self.assertTrue(validate(d))
        self.assertEqual(len(eligible(d)), 1)
    def test_unconfirmed_or_wrong_surface_never_exports(self):
        for field,value in [('status','pending'),('surface','別名'),('reading','し けん'),('reading_url',''),('reading','べつのよみ')]:
            d=dataset(); d['entries'][0][field]=value
            self.assertEqual(len(eligible(d)),1)
    def test_wrong_field_types_are_reported_not_crashed(self):
        for field in ['reading','source_hash','surface']:
            d=dataset();d['entries'][0][field]=[]
            self.assertTrue(validate(d))
            self.assertEqual(eligible(d),[])
    def test_duplicate_id_is_invalid(self):
        d=dataset(); d['facilities'][1]['id']=d['facilities'][0]['id']
        self.assertTrue(any('duplicate' in x['reason'] for x in validate(d)))
        self.assertEqual(eligible(d), [])
    def test_entry_source_must_match_facility(self):
        d=dataset(); d['entries'][0]['listing_url']='https://example.invalid/other'
        self.assertEqual(len(eligible(d)),1)

class StorageTest(unittest.TestCase):
    def test_snapshot_and_deterministic_json(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'common.json'; d=dataset()
            save_dataset(p,d); before=p.read_bytes(); save_dataset(p,d)
            self.assertEqual(before,p.read_bytes())
            changed=copy.deepcopy(d); changed['facilities'][0]['listed_name']='変更'
            delta=save_dataset(p,changed)
            self.assertTrue(delta['changed_facilities'])
            self.assertEqual(load_dataset(p),changed)
            self.assertTrue(list((p.parent/'snapshots').glob('*.json')))
    def test_human_exclusion_survives_and_stale_decision_quarantines(self):
        d=dataset(); e=d['entries'][0]
        decisions={e['id']:{'expected_source_hash':e['source_hash'],'status':'excluded','reason':'人手の除外'}}
        out=apply_decisions(d,decisions)
        self.assertEqual(out['entries'][0]['status'],'excluded')
        self.assertEqual(d['entries'][0]['status'],'verified')
        d['entries'][0]['source_hash']='b'*64
        self.assertEqual(apply_decisions(d,decisions)['entries'][0]['status'],'pending')

if __name__=='__main__': unittest.main()

class ReviewRegressionTest(unittest.TestCase):
    def test_decisions_cannot_rewrite_acquired_raw_reading(self):
        d=dataset(); e=d['entries'][0]
        decision={e['id']:{'expected_source_hash':e['source_hash'],'status':'verified','reason':'test','reading':'べつよみ','reading_raw':'ベツヨミ'}}
        with self.assertRaises(ValueError): apply_decisions(d,decision)
    def test_tampered_original_fingerprint_invalid(self):
        d=dataset();d['entries'][0]['reading']=d['entries'][0]['reading_raw']='べつよみ'
        self.assertEqual(len(eligible(d)),1)
    def test_missing_reading_can_use_separate_official_supplement(self):
        d=dataset();e=d['entries'][2];f=d['facilities'][2]
        self.assertEqual(f['status'],'verified')
        self.assertIsNone(f['official_site_url'])
        decision={e['id']:{'expected_source_hash':e['source_hash'],'status':'verified','reason':'official supplement reviewed','reading':'みかくにんしゃ','reading_url':'https://shrine.example.invalid/about', 'reading_source_kind':'shrine_official','supplemental_reading_raw':'ミカクニンシャ','supplemental_official_verification':{'url':'https://shrine.example.invalid/','evidence_url':'https://shrine.example.invalid/about','name_raw':f['listed_name'],'address_raw':f['address'],'evidence':'official identity and address shown','checked_at':'2026-11-08T00:00:00+00:00','status':'verified'},'supplemental_name':f['listed_name'],'supplemental_address':f['address'],'evidence':'linked official site displays exact listed name and address','checked_at':'2026-11-08T00:00:00+00:00'}}
        corrected=apply_decisions(d,decision)
        self.assertEqual(corrected['entries'][2]['reading_raw'],'')
        self.assertEqual(len(eligible(corrected)),3)
    def test_multiline_address_is_pending_not_merged(self):
        d=parse(HTML.replace('架空市甲町1','架空市甲町1<br>別市乙町2'),'2026-11-08','a'*64)
        self.assertEqual(d['entries'][0]['status'],'pending')
        self.assertIn('multiple address',d['entries'][0]['reason'])
    def test_name_or_address_changes_quarantine_and_manual_identity_link(self):
        from njd.storage import reconcile_identity
        old=dataset()
        changed=parse(HTML.replace('架空市甲町1','架空市甲町一番地'),'2026-11-08','a'*64)
        new_id=changed['facilities'][0]['id'];old_id=old['facilities'][0]['id']
        pending=reconcile_identity(old,changed,{})
        self.assertEqual(pending['entries'][0]['status'],'pending')
        repeat=reconcile_identity(pending,changed,{})
        self.assertEqual(repeat['entries'][0]['status'],'pending')
        linked=reconcile_identity(pending,changed,{new_id:{'facility_id':old_id,'expected_source_hash':changed['entries'][0]['source_hash'],'reason':'identity reviewed'}})
        self.assertEqual(linked['facilities'][0]['id'],old_id)
        self.assertEqual(linked['entries'][0]['id'],old['entries'][0]['id'])
