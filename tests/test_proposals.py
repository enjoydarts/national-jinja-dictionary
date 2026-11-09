import copy
import tempfile
import unittest
from pathlib import Path
from test_records import build, row
from test_corrections import correction
from njd import proposals
from njd.nationwide import save_collection
from njd.storage import load_dataset, write_json
from njd.__main__ import _effective
from njd.validation import eligible


class ProposalImportTests(unittest.TestCase):
    def test_agency_priority_cannot_borrow_identity_or_reading_from_secondary_reference(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);data,old=self.setup_data(root);eid=data['entries'][0]['id']
            write_json(root/'corrections.json',old);new=correction(data,{'reading':'べつのじんじゃ'})
            ref=copy.deepcopy(new['entries'][eid]['references'][0])
            ref.update(url='https://agency.example.invalid/shrines/1',source_kind='agency',
                name_raw='別神社',address_raw='架空市甲町99',excerpt='別神社 架空市甲町99')
            new['entries'][eid]['references'].append(ref)
            with self.assertRaises(ValueError):proposals.import_proposals(root,new,apply=True,prefer_agency=True)
            self.assertEqual(load_dataset(root/'corrections.json'),old)

    def test_primary_agency_reading_may_supersede_secondary_with_evidence_retained(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);data,old=self.setup_data(root);eid=data['entries'][0]['id']
            write_json(root/'corrections.json',old)
            new=copy.deepcopy(old);c=new['entries'][eid];ref=c['references'][0]
            c['changes']['reading']='べつのじんじゃ'
            ref.update(url='https://agency.example.invalid/shrines/1',source_kind='agency',reading_raw='べつのじんじゃ',excerpt='架空神社 べつのじんじゃ 架空市乙町1')
            with self.assertRaises(ValueError):proposals.import_proposals(root,new,apply=True)
            result=proposals.import_proposals(root,new,apply=True,prefer_agency=True)
            self.assertEqual(result['replaced'],1)
            stored=load_dataset(root/'corrections.json')['entries'][eid]
            self.assertEqual(stored['superseded_secondary_reading'],'かくうじんじゃ')
            self.assertEqual(len(stored['references']),2)
            self.assertEqual(eligible(_effective(root))[0]['reading'],'べつのじんじゃ')
            repeat=proposals.import_proposals(root,new,apply=True,prefer_agency=True)
            self.assertEqual((repeat['replaced'],repeat['unchanged']),(0,1))
            conflict=copy.deepcopy(new);conflict['entries'][eid]['changes']['reading']='べつじんじゃ'
            r=conflict['entries'][eid]['references'][0];r.update(reading_raw='べつじんじゃ',excerpt='架空神社 べつじんじゃ 架空市乙町1')
            with self.assertRaises(ValueError):proposals.import_proposals(root,conflict,apply=True,prefer_agency=True)

    def test_prefer_agency_requires_actual_agency_host_and_never_changes_surface(self):
        for change in ('external','surface'):
            with self.subTest(change=change),tempfile.TemporaryDirectory() as td:
                root=Path(td);data,old=self.setup_data(root);eid=data['entries'][0]['id']
                write_json(root/'corrections.json',old);new=copy.deepcopy(old);c=new['entries'][eid]
                c['references'][0]['source_kind']='agency'
                if change=='surface':c['changes']['surface']='架空神社別称'
                with self.assertRaises(ValueError):proposals.import_proposals(root,new,apply=True,prefer_agency=True)

    def setup_data(self, root):
        data=build([row(reading_raw='')]);save_collection(root,'example',data)
        return data,correction(data,{'reading':'かくうじんじゃ'})

    def test_preview_then_atomic_apply_and_repeat_preserves_original(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);data,doc=self.setup_data(root)
            before=(root/'sources/example.json').read_bytes()
            self.assertEqual(proposals.import_proposals(root,doc)['added'],1)
            self.assertFalse((root/'corrections.json').exists())
            self.assertEqual(proposals.import_proposals(root,doc,apply=True)['added'],1)
            self.assertEqual(len(eligible(_effective(root))),1)
            self.assertEqual(proposals.import_proposals(root,doc,apply=True)['unchanged'],1)
            self.assertEqual((root/'sources/example.json').read_bytes(),before)

    def test_any_invalid_target_prevents_partial_import(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);data,doc=self.setup_data(root)
            doc['entries']['missing-entry']=copy.deepcopy(next(iter(doc['entries'].values())))
            with self.assertRaises(ValueError):proposals.import_proposals(root,doc,apply=True)
            self.assertFalse((root/'corrections.json').exists())

    def test_stale_source_and_existing_manual_judgments_are_protected(self):
        for change in ('source','correction','review','decision'):
            with self.subTest(change=change),tempfile.TemporaryDirectory() as td:
                root=Path(td);data,doc=self.setup_data(root);eid=data['entries'][0]['id']
                if change=='source':save_collection(root,'example',build([row(reading_raw='')|{'address':'架空市乙町2'}]))
                elif change=='decision':write_json(root/'decisions.json',{eid:dict(status='excluded',reason='manual exclusion')})
                else:write_json(root/('corrections.json' if change=='correction' else 'reviews.json'),dict(schema_version=1,entries={eid:dict(status='needs_review',reason='existing judgment')}))
                before=(root/'corrections.json').read_bytes() if (root/'corrections.json').exists() else None
                with self.assertRaises(ValueError):proposals.import_proposals(root,doc,apply=True)
                self.assertEqual((root/'corrections.json').read_bytes() if (root/'corrections.json').exists() else None,before)

    def test_discovery_directory_proposal_and_wrong_parcel_rejected(self):
        for change in ('discovery','address'):
            with self.subTest(change=change),tempfile.TemporaryDirectory() as td:
                root=Path(td);data,doc=self.setup_data(root);ref=next(iter(doc['entries'].values()))['references'][0]
                if change=='discovery':ref['url']='https://jinja-net.jp/jinja-all/'
                else:ref['address_raw']='架空市乙町99';ref['excerpt']='架空神社 かくうじんじゃ 架空市乙町99'
                with self.assertRaises(ValueError):proposals.import_proposals(root,doc,apply=True)
                self.assertFalse((root/'corrections.json').exists())
