"""Synthetic same-row CSV facts; never evidence for actual shrine readings."""
import copy
import unittest
from test_records import build, row
from test_corrections import correction
from njd.corrections import apply_corrections
from njd.validation import eligible, validate


def fixture():
    data=build([row(reading_raw='',address='架空市乙町字山ノ神1061')])
    doc=correction(data,{'reading':'かくうじんじゃ'})
    ref=next(iter(doc['entries'].values()))['references'][0]
    fields={'No':'1','神社名':'架空神社','カナ':'カクウジンジャ','所在地':'架空市乙町1061','小字':'山ノ神'}
    excerpt=' / '.join(k+'='+v for k,v in fields.items())
    ref.update(url='https://research.example.invalid/data.csv',page_hash='b'*64,
        source_kind='university_hosted_community_research_csv',mime_type='text/csv',
        reading_scope='full_name',reading_raw='カクウジンジャ',address_raw=fields['所在地'],
        source_fields=fields,csv_record_number=2,locator='CSV logical record2, No=1',excerpt=excerpt)
    ref['csv_address_context']=dict(kind='same_csv_record_explicit_aza',url=ref['url'],
        page_hash=ref['page_hash'],checked_at=ref['checked_at'],csv_record_number=2,
        row_id_raw='1',comparison_separator='字',source_fields=copy.deepcopy(fields),locator=ref['locator'],excerpt=excerpt)
    return data,doc,ref


class CsvContextTest(unittest.TestCase):
    def test_explicit_same_row_fields_supply_comparison_without_rewriting_evidence(self):
        data,doc,ref=fixture();before=copy.deepcopy(data);evidence=copy.deepcopy(doc)
        out=apply_corrections(data,doc)
        self.assertEqual(len(eligible(out)),1)
        self.assertEqual(out['entries'][0]['reading'],'かくうじんじゃ')
        self.assertEqual(out['entries'][0]['reading_raw'],'')
        self.assertEqual(out['facilities'],before['facilities'])
        self.assertEqual(ref['address_raw'],'架空市乙町1061')
        self.assertEqual(data,before);self.assertEqual(doc,evidence)
        self.assertEqual(validate(out),[])
        self.assertEqual(apply_corrections(out,doc),out)

    def test_neighboring_record_excerpt_cannot_satisfy_prefix_values(self):
        data,doc,ref=fixture()
        wrong=ref['excerpt'].replace('No=1','No=10').replace('所在地=架空市乙町1061','所在地=架空市乙町10610')
        ref['excerpt']=wrong;ref['csv_address_context']['excerpt']=wrong
        self.assertEqual(eligible(apply_corrections(data,doc)),[])

    def test_explicit_locality_can_match_without_an_unprinted_aza_separator(self):
        data,doc,ref=fixture();data=build([row(reading_raw='',address='架空市乙町山ノ神1061')])
        new=correction(data,{'reading':'かくうじんじゃ'});next(iter(new['entries'].values()))['references']=[ref]
        ref['csv_address_context']['comparison_separator']=''
        self.assertEqual(len(eligible(apply_corrections(data,new))),1)
        ref['csv_address_context']['comparison_separator']='別'
        self.assertEqual(eligible(apply_corrections(data,new)),[])

    def test_mismatched_binding_and_nonliteral_fields_are_held(self):
        edits=[lambda r:r.pop('csv_address_context'),lambda r:r.update(source_kind='official_agency'),
            lambda r:r.update(mime_type='application/pdf'),lambda r:r.update(reading_scope='partial_or_absent'),
            lambda r:r.update(csv_record_number=True),lambda r:r.update(page_hash='c'*64),
            lambda r:r['csv_address_context'].update(csv_record_number=3),
            lambda r:r['csv_address_context'].update(row_id_raw='2'),
            lambda r:r['csv_address_context'].update(page_hash='c'*64),
            lambda r:r['csv_address_context'].update(url='https://other.example.invalid/data.csv'),
            lambda r:r['csv_address_context'].update(checked_at='2026-11-13'),
            lambda r:r['csv_address_context'].update(locator=''),
            lambda r:r['csv_address_context'].update(excerpt='別行の抜粋'),
            lambda r:r['csv_address_context']['source_fields'].update(小字='別山'),
            lambda r:r.update(excerpt='架空神社 / カクウジンジャ / 架空市乙町1061'),
            lambda r:r['source_fields'].update(カナ='カクウ'),
            lambda r:r['source_fields'].update(神社名='別神社'),
            lambda r:r.update(address_components={'住所':'架空市乙町1061'})]
        for i,edit in enumerate(edits):
            with self.subTest(case=i):
                data,doc,ref=fixture();edit(ref)
                self.assertEqual(eligible(apply_corrections(data,doc)),[])

    def test_wrong_locality_or_parcel_never_uses_the_same_name_to_match(self):
        for address in ['架空市乙町字山ノ神1061-1','架空市乙町字山ノ神106','架空市乙町字山ノ神10610',
                        '架空市乙町字別山1061','架空市甲町字山ノ神1061','別市乙町字山ノ神1061']:
            with self.subTest(address=address):
                data,doc,ref=fixture();data=build([row(reading_raw='',address=address)])
                new=correction(data,{'reading':'かくうじんじゃ'});next(iter(new['entries'].values()))['references']=[ref]
                self.assertEqual(eligible(apply_corrections(data,new)),[])

    def test_invalid_context_does_not_fall_back_to_a_complete_address(self):
        data,doc,ref=fixture();ref['address_raw']='架空市乙町字山ノ神1061'
        ref['excerpt']+=' / 架空市乙町字山ノ神1061';ref['csv_address_context']['page_hash']='c'*64
        self.assertEqual(eligible(apply_corrections(data,doc)),[])

    def test_existing_exclusion_is_durable_over_repeated_valid_and_corrupt_application(self):
        for corrupt in [False,True]:
            data,doc,ref=fixture();data['entries'][0].update(status='excluded',reason='Existing explicit exclusion')
            if corrupt:ref['csv_address_context']['page_hash']='c'*64
            out=data
            for _ in range(3):
                out=apply_corrections(out,doc)
                self.assertEqual(out['entries'][0]['status'],'excluded')
                self.assertEqual(out['entries'][0]['reason'],'Existing explicit exclusion')
                self.assertEqual(eligible(out),[])

    def test_mixed_references_cannot_clear_an_exclusion_or_bypass_the_context_scope(self):
        for kind in ['excluded','surface']:
            with self.subTest(kind=kind):
                data,doc,ref=fixture()
                ordinary=next(iter(correction(data,{'reading':'かくうじんじゃ'})['entries'].values()))['references'][0]
                value=next(iter(doc['entries'].values()));value['references'].append(ordinary)
                if kind=='excluded':data['entries'][0].update(status='excluded',reason='Existing explicit exclusion')
                else:value['changes']['surface']='架空神社'
                out=data
                for _ in range(3):
                    out=apply_corrections(out,doc)
                    self.assertEqual(eligible(out),[])
                    if kind=='excluded':
                        self.assertEqual(out['entries'][0]['status'],'excluded')
                        self.assertEqual(out['entries'][0]['reason'],'Existing explicit exclusion')

    def test_mixed_references_cannot_hide_a_corrupt_csv_context(self):
        data,doc,ref=fixture()
        ordinary=next(iter(correction(data,{'reading':'かくうじんじゃ'})['entries'].values()))['references'][0]
        next(iter(doc['entries'].values()))['references'].append(ordinary)
        ref['csv_address_context']['page_hash']='c'*64
        self.assertEqual(eligible(apply_corrections(data,doc)),[])

    def test_other_identity_holds_and_surface_changes_are_not_resolved(self):
        for kind in ['identity','facility','authority','surface']:
            data,doc,ref=fixture()
            if kind=='identity':data['entries'][0]['identity_review_required']=True
            if kind=='facility':data['facilities'][0].update(status='pending',reason='identity unresolved')
            if kind=='authority':data['collection']['authority_status']='unconfirmed'
            if kind=='surface':next(iter(doc['entries'].values()))['changes']['surface']='架空神社'
            self.assertEqual(eligible(apply_corrections(data,doc)),[])

    def test_malformed_binding_fields_are_rejected_without_raising(self):
        data,doc,ref=fixture();keys=list(ref['csv_address_context'])
        for key in keys:
            for bad in [None,[],7,'',True]:
                with self.subTest(field=key,value=bad):
                    data,doc,ref=fixture();ref['csv_address_context'][key]=bad
                    self.assertEqual(eligible(apply_corrections(data,doc)),[])

    def test_malformed_context_is_held_and_saved_evidence_corruption_stops_output(self):
        for value in [None,[],7,'',True]:
            data,doc,ref=fixture();ref['csv_address_context']=value
            self.assertEqual(eligible(apply_corrections(data,doc)),[])
        data,doc,ref=fixture();out=apply_corrections(data,doc)
        self.assertEqual(len(eligible(out)),1)
        out['entries'][0]['correction']['references'][0]['csv_address_context']['row_id_raw']='2'
        self.assertTrue(validate(out));self.assertEqual(eligible(out),[])
