"""Synthetic numbered booklet observations, never evidence for actual shrines."""
import copy
import unittest
from test_records import build, row
from test_corrections import correction
from njd.corrections import apply_corrections
from njd.validation import eligible, validate


def fixture(annotation=''):
    data=build([row(reading_raw='',address='架空市乙町山里1061番地2')])
    doc=correction(data,{'reading':'かくうじんじゃ'})
    ref=next(iter(doc['entries'].values()))['references'][0]
    name='架空神社'+('（'+annotation+'）' if annotation else '')
    profile='かくうじんじゃ\n'+name+'\n神社番号 12'
    table='12 / 架空神社 / 山里1061番地2'
    ref.update(url='https://tourism.example.invalid/booklet.pdf',page_hash='b'*64,
        source_kind='tourism_organization_booklet',reading_scope='full_name',
        address_raw='山里1061番地2',pdf_pages=18,source_page_index=7,source_card_number=12,
        profile_name_raw=name,profile_locality_annotation_raw=annotation,
        locator='PDF8 profile12 and PDF3 table12',excerpt=profile+'\n'+table,
        visual_review=dict(method='pdf_render_individual_review',profile_page_image_sha256='c'*64,table_page_image_sha256='d'*64))
    ref['booklet_address_context']=dict(kind='same_pdf_numbered_profile_explicit_prefix',
        url=ref['url'],page_hash=ref['page_hash'],checked_at=ref['checked_at'],
        source_page_index=2,record_number=12,name_raw='架空神社',address_raw=ref['address_raw'],
        prefecture_raw='埼玉県',municipality_raw='架空市',town_raw='乙町',
        heading_raw='乙町（25社）',prefix_declaration_raw='「埼玉県架空市乙町」を省略',
        prefix_excerpt='乙町（25社）\n「埼玉県架空市乙町」を省略',
        locator='PDF3 town scope and numbered table',profile_excerpt=profile,row_excerpt=table,
        individual_identity_review='same_subject_no_unresolved_location_conflict')
    return data,doc,ref


class BookletContextTest(unittest.TestCase):
    def test_numbered_profile_and_explicit_prefix_support_reading_without_rewriting(self):
        data,doc,ref=fixture();raw=copy.deepcopy(data);evidence=copy.deepcopy(doc)
        out=apply_corrections(data,doc)
        self.assertEqual(len(eligible(out)),1)
        self.assertEqual(out['entries'][0]['reading'],'かくうじんじゃ')
        self.assertEqual(out['entries'][0]['reading_raw'],'')
        self.assertEqual(out['facilities'],raw['facilities'])
        self.assertEqual(data,raw);self.assertEqual(doc,evidence)
        self.assertEqual(validate(out),[])
        self.assertEqual(apply_corrections(out,doc),out)

    def test_separately_printed_locality_annotation_is_not_part_of_shrine_reading(self):
        data,doc,ref=fixture('山里');self.assertEqual(len(eligible(apply_corrections(data,doc))),1)
        data,doc,ref=fixture('別里');self.assertEqual(eligible(apply_corrections(data,doc)),[])

    def test_wrong_literal_address_or_name_cannot_match(self):
        for address in ['架空市乙町山里1061番地','架空市乙町山里1061番地20','架空市甲町山里1061番地2',
                        '架空市乙町山里1061番地2','別市乙町山里1061番地2']:
            data,doc,ref=fixture();changed=build([row(reading_raw='',address=address)])
            new=correction(changed,{'reading':'かくうじんじゃ'});next(iter(new['entries'].values()))['references']=[ref]
            self.assertEqual(eligible(apply_corrections(changed,new)),[])
        data,doc,ref=fixture();ref['name_raw']='別神社';self.assertEqual(eligible(apply_corrections(data,doc)),[])

    def test_binding_fields_and_prefix_substrings_must_match_exactly(self):
        edits=[lambda r:r.pop('booklet_address_context'),lambda r:r.update(source_card_number=120),
            lambda r:r.update(source_page_index=True),lambda r:r.update(source_page_index=18),
            lambda r:r.update(pdf_pages=2),lambda r:r.update(reading_scope='partial_or_absent'),
            lambda r:r.update(source_kind='agency'),lambda r:r.update(url='http://tourism.example.invalid/booklet.pdf'),
            lambda r:r.update(visual_review={}),lambda r:r.update(profile_name_raw='架空神社・別神社'),
            lambda r:r['booklet_address_context'].update(prefix_declaration_raw='「埼玉県架空市」を省略'),
            lambda r:r['booklet_address_context'].update(row_excerpt='120 / 架空神社 / 山里1061番地20'),
            lambda r:r['booklet_address_context'].update(profile_excerpt='別の紹介'),
            lambda r:r['booklet_address_context'].update(source_page_index=7),
            lambda r:r['booklet_address_context'].update(individual_identity_review='unresolved_location_conflict'),
            lambda r:r.update(address_components={}),lambda r:r.update(csv_address_context={}),
            lambda r:r.update(document_address_context={})]
        for i,edit in enumerate(edits):
            with self.subTest(case=i):
                data,doc,ref=fixture();edit(ref);self.assertEqual(eligible(apply_corrections(data,doc)),[])

    def test_missing_and_malformed_context_fields_never_raise_or_fall_back(self):
        _,_,ref=fixture()
        for key in ref['booklet_address_context']:
            for bad in [None,[],{},7,'',True]:
                with self.subTest(key=key,bad=bad):
                    data,doc,ref=fixture();ref['booklet_address_context'][key]=bad
                    self.assertEqual(eligible(apply_corrections(data,doc)),[])
        for bad in [None,[],{},7,'',True]:
            data,doc,ref=fixture();ref['booklet_address_context']=bad
            self.assertEqual(eligible(apply_corrections(data,doc)),[])

    def test_mixed_good_reference_cannot_hide_corruption_or_expand_scope(self):
        for kind in ['corrupt','surface','excluded']:
            data,doc,ref=fixture();ordinary=next(iter(correction(data,{'reading':'かくうじんじゃ'})['entries'].values()))['references'][0]
            value=next(iter(doc['entries'].values()));value['references'].append(ordinary)
            if kind=='corrupt':ref['booklet_address_context']['page_hash']='c'*64
            if kind=='surface':value['changes']['surface']='架空神社'
            if kind=='excluded':data['entries'][0].update(status='excluded',reason='Existing exclusion')
            out=data
            for _ in range(3):
                out=apply_corrections(out,doc);self.assertEqual(eligible(out),[])
                if kind=='excluded':self.assertEqual((out['entries'][0]['status'],out['entries'][0]['reason']),('excluded','Existing exclusion'))

    def test_exclusions_remain_durable_even_with_corrupt_context(self):
        for corrupt in [False,True]:
            data,doc,ref=fixture();data['entries'][0].update(status='excluded',reason='Existing exclusion')
            if corrupt:ref['booklet_address_context']['page_hash']='c'*64
            out=data
            for _ in range(3):
                out=apply_corrections(out,doc);self.assertEqual(eligible(out),[])
                self.assertEqual((out['entries'][0]['status'],out['entries'][0]['reason']),('excluded','Existing exclusion'))

    def test_identity_facility_authority_holds_are_preserved(self):
        for kind in ['identity','facility','authority']:
            data,doc,ref=fixture()
            if kind=='identity':data['entries'][0]['identity_review_required']=True
            if kind=='facility':data['facilities'][0].update(status='pending',reason='identity unresolved')
            if kind=='authority':data['collection']['authority_status']='unconfirmed'
            self.assertEqual(eligible(apply_corrections(data,doc)),[])

    def test_saved_context_corruption_stops_offline_output(self):
        data,doc,ref=fixture();out=apply_corrections(data,doc);self.assertEqual(len(eligible(out)),1)
        out['entries'][0]['correction']['references'][0]['booklet_address_context']['record_number']=13
        self.assertTrue(validate(out));self.assertEqual(eligible(out),[])
