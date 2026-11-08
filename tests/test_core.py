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
