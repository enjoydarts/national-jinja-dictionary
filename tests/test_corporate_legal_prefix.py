"""Legal-form comparison follows the opened official furigana rule only."""
import copy
from pathlib import Path
import tempfile
import unittest
from test_corporate import row,archive,target,META,LANDING
from njd import corporate as c
from njd.corrections import correction_problems
from njd.http import Page
from njd.storage import write_json,load_dataset


class CorporateLegalPrefixTests(unittest.TestCase):
    def proposal(self,**changes):
        return c.proposals_for_archive(archive([row(name='宗教法人前田神社',**changes)]),[target()],META)

    def test_explicit_legal_prefix_keeps_raw_name_and_literal_kana(self):
        accepted,pending=self.proposal();self.assertEqual(pending,{})
        p=accepted['e'];ref=p['references'][0]
        self.assertEqual(p['changes'],dict(reading='まえだじんじゃ'))
        self.assertEqual(ref['name_raw'],'宗教法人前田神社')
        self.assertEqual(ref['source_fields']['name'],'宗教法人前田神社')
        self.assertEqual(ref['reading_raw'],'マエダジンジャ')
        self.assertEqual(ref['registered_name_identity']['shrine_name_raw'],'前田神社')
        self.assertEqual(correction_problems(p,target()['facility'],target()['entry'],target()['source']),[])

    def test_other_forms_internal_prefix_wrong_kind_or_address_are_not_stripped(self):
        for changes in [dict(name='一般社団法人前田神社'),dict(name='宗教法人宗教法人前田神社'),dict(name='前田神社宗教法人'),dict(name='宗教法人前田神社支部'),dict(name='宗教法人 前田神社'),dict(name='宗教法人前田神社',kind='301'),dict(name='宗教法人前田神社',streetNumber='大覚寺７６０番地')]:
            with self.subTest(changes=changes):
                self.assertEqual(c.proposals_for_archive(archive([row(**changes)]),[target()],META)[0],{})

    def test_a_different_direct_registered_name_prevents_false_uniqueness(self):
        rows=[row(name='宗教法人前田神社'),row(corporateNumber='9876543210123')]
        self.assertEqual(c.proposals_for_archive(archive(rows),[target()],META)[0],{})

    def test_competing_prefixed_identity_without_usable_kana_still_blocks_adoption(self):
        for raw in ('','シュウキョウホウジンマエダジンジャ'):
            with self.subTest(raw=raw):
                rows=[row(name='宗教法人前田神社'),row(name='宗教法人前田神社',corporateNumber='9876543210123',furigana=raw)]
                self.assertEqual(c.proposals_for_archive(archive(rows),[target()],META)[0],{})

    def test_manually_imported_prefix_packet_cannot_bind_only_a_locality(self):
        p=self.proposal()[0]['e'];t=target();t['facility']['address']='鳥取市大覚寺'
        p['original']['address']=t['facility']['address']
        self.assertTrue(correction_problems(p,t['facility'],t['entry'],t['source']))

    def test_legal_prefix_in_furigana_is_never_silently_removed(self):
        self.assertEqual(self.proposal(furigana='シュウキョウホウジンマエダジンジャ')[0],{})

    def test_image_backed_registered_name_still_requires_actual_image_review(self):
        self.assertEqual(self.proposal(nameImageId='00001234')[0],{})

    def test_missing_or_tampered_rule_packet_cannot_bind_a_name(self):
        original=self.proposal()[0]['e']
        mutations=[lambda r:r.pop('registered_name_identity'),
            lambda r:r['registered_name_identity'].update(shrine_name_raw='別神社'),
            lambda r:r['registered_name_identity']['rule_reference'].update(url='https://elsewhere.invalid/'),
            lambda r:r['registered_name_identity']['rule_reference'].update(page_hash='b'*64),
            lambda r:r['source_fields'].update(name='宗教法人別神社'),
            lambda r:r['source_fields'].update(latest='0'),
            lambda r:r['source_fields'].update(closeDate='2026-01-01'),
            lambda r:r['source_fields'].update(hihyoji='1'),
            lambda r:r.update(source_kind='reference')]
        for i,change in enumerate(mutations):
            with self.subTest(case=i):
                p=copy.deepcopy(original);change(p['references'][0])
                self.assertTrue(correction_problems(p,target()['facility'],target()['entry'],target()['source']))

    def test_previous_matching_profile_is_rechecked_from_cached_archive(self):
        class Client:
            def fetch(self,url,**kwargs):return Page(c.LANDING,200,{},LANDING.encode(),META['checked_at'])
            def download(self,meta,**kwargs):return Page(META['url'],200,{},archive([row(name='宗教法人前田神社')]),META['checked_at'])
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);t=target()
            write_json(root/'data/sources/test.json',dict(collection=t['source'],facilities=[t['facility']],entries=[t['entry']]))
            c.research(root/'data',root/'state',['31'],Client())
            path=root/'state/state/progress.json';state=load_dataset(path)
            state['prefectures']['31'].pop('matching_profile',None);write_json(path,state)
            result=c.research(root/'data',root/'state',['31'],Client())
            self.assertEqual(result['prefectures_attempted'],1)
            self.assertEqual(c.research(root/'data',root/'state',['31'],Client())['prefectures_attempted'],0)
