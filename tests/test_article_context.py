"""Synthetic article facts; none are evidence for real shrine readings."""
import copy
import unittest
from test_records import build,row
from test_corrections import correction
from njd.corrections import apply_corrections
from njd.validation import eligible,validate


def fixture(annotation=True):
    data=build([row(reading_raw='',address='架空市乙町山里1061番地2')])
    doc=correction(data,{'reading':'かくうじんじゃ'});ref=next(iter(doc['entries'].values()))['references'][0]
    raw='乙町山里'+('（おつまちやまざと）' if annotation else '')+'1061番地2'
    heading='架空神社（かくうじんじゃ）';paragraph=raw+'　>>　Googleマップ'
    ref.update(url='https://research.example.invalid/archives/1',page_hash='b'*64,
        source_kind='independent_secondary_reference',mime_type='text/html',reading_scope='full_name',
        address_raw=raw,heading_raw=heading,address_paragraph_raw=paragraph,excerpt=heading+'\n'+paragraph,
        locator='direct body h2[15] and p[16]',
        body_locator='#mainEntity > div.clearfix',body_elements=80,scope_element_index=4,heading_element_index=15,
        address_element_index=16,heading_tag='h2',address_tag='p',address_kana_annotation=None)
    if annotation:ref['address_kana_annotation']=dict(raw='（おつまちやまざと）',start=raw.index('（'),end=raw.index('）')+1)
    ref['article_address_context']=dict(kind='same_article_explicit_omitted_municipality',
        url=ref['url'],page_hash=ref['page_hash'],checked_at=ref['checked_at'],
        body_locator=ref['body_locator'],body_elements=80,structure_kind='direct_article_body_children',
        scope_element_index=4,scope_tag='p',prefecture_raw='埼玉県',municipality_raw='架空市',
        declaration_raw='※以下、埼玉県架空市を省略',scope_paragraph_raw='※以下、埼玉県架空市を省略',
        locator='direct body p[4] precedes h2[15] and p[16]',
        individual_identity_review='literal_heading_and_full_parcel_no_identity_hold')
    return data,doc,ref


class ArticleContextTest(unittest.TestCase):
    def test_explicit_article_prefix_and_literal_annotation_support_reading_without_rewriting(self):
        data,doc,ref=fixture();raw=copy.deepcopy(data);evidence=copy.deepcopy(doc);out=apply_corrections(data,doc)
        self.assertEqual(len(eligible(out)),1);self.assertEqual(out['entries'][0]['reading'],'かくうじんじゃ')
        self.assertEqual(out['entries'][0]['reading_raw'],'');self.assertEqual(out['facilities'],raw['facilities'])
        self.assertEqual(data,raw);self.assertEqual(doc,evidence);self.assertEqual(validate(out),[])
        self.assertEqual(apply_corrections(out,doc),out)

    def test_plain_address_and_parenthesized_declaration_are_supported(self):
        data,doc,ref=fixture(False);c=ref['article_address_context'];c['declaration_raw']='（以下、埼玉県架空市を省略）';c['scope_paragraph_raw']='冒頭の所在説明'+c['declaration_raw']+'を含む本文。'
        self.assertEqual(len(eligible(apply_corrections(data,doc))),1)

    def test_wrong_literal_locality_parcel_and_name_are_held(self):
        for address in ['架空市乙町山里1061番地20','架空市乙町山里1061番地','架空市乙町字山里1061番地2',
                        '架空市乙町山里1061番地2','別市乙町山里1061番地2']:
            data,doc,ref=fixture();changed=build([row(reading_raw='',address=address)]);new=correction(changed,{'reading':'かくうじんじゃ'});next(iter(new['entries'].values()))['references']=[ref]
            self.assertEqual(eligible(apply_corrections(changed,new)),[])
        data,doc,ref=fixture();ref['heading_raw']='別神社（かくうじんじゃ）';self.assertEqual(eligible(apply_corrections(data,doc)),[])

    def test_bad_scope_nonadjacent_blocks_or_other_document_never_match(self):
        edits=[lambda r:r.pop('article_address_context'),lambda r:r.update(mime_type='application/pdf'),
            lambda r:r.update(source_kind='agency'),lambda r:r.update(reading_scope='partial_or_absent'),
            lambda r:r.update(body_locator='aside'),lambda r:r.update(heading_tag='li'),
            lambda r:r.update(address_tag='blockquote'),lambda r:r.update(address_element_index=17),
            lambda r:r.update(heading_element_index=True),lambda r:r.update(body_elements=16),
            lambda r:r.update(address_components={}),lambda r:r.update(booklet_address_context={}),
            lambda r:r.update(csv_address_context={}),lambda r:r.update(document_address_context={}),
            lambda r:r['article_address_context'].update(scope_element_index=16),
            lambda r:r['article_address_context'].update(structure_kind='quoted_article_card'),
            lambda r:r['article_address_context'].update(declaration_raw='市内なので省略'),
            lambda r:r['article_address_context'].update(declaration_raw='※以下、埼玉県別市を省略'),
            lambda r:r['article_address_context'].update(url='https://other.example.invalid/archives/1'),
            lambda r:r['article_address_context'].update(checked_at='2026-11-13'),
            lambda r:r.update(excerpt=r['excerpt']+'別の住所'),
            lambda r:r.update(address_paragraph_raw=r['address_raw']+'10610 >> Googleマップ')]
        for i,edit in enumerate(edits):
            with self.subTest(case=i):
                data,doc,ref=fixture();edit(ref);self.assertEqual(eligible(apply_corrections(data,doc)),[])

    def test_annotation_cannot_delete_kanji_or_use_an_unbound_range(self):
        edits=[lambda a:a.update(start=0),lambda a:a.update(end=16),lambda a:a.update(start=True),
               lambda a:a.update(raw='（別山）'),lambda a:a.update(raw='（おつまち）'),lambda a:a.update(end=[])]
        for edit in edits:
            data,doc,ref=fixture();edit(ref['address_kana_annotation']);self.assertEqual(eligible(apply_corrections(data,doc)),[])
        for bad in [[],{},True,7,'']:
            data,doc,ref=fixture();ref['address_kana_annotation']=bad;self.assertEqual(eligible(apply_corrections(data,doc)),[])

    def test_malformed_context_fields_and_missing_values_never_raise(self):
        _,_,ref=fixture()
        for key in ref['article_address_context']:
            for bad in [None,[],{},7,'',True]:
                with self.subTest(key=key,bad=bad):
                    data,doc,ref=fixture();ref['article_address_context'][key]=bad;self.assertEqual(eligible(apply_corrections(data,doc)),[])
        for bad in [None,[],{},7,'',True]:
            data,doc,ref=fixture();ref['article_address_context']=bad;self.assertEqual(eligible(apply_corrections(data,doc)),[])

    def test_mixed_good_reference_cannot_bypass_corruption_surface_scope_or_exclusion(self):
        for kind in ['corrupt','surface','excluded']:
            data,doc,ref=fixture();ordinary=next(iter(correction(data,{'reading':'かくうじんじゃ'})['entries'].values()))['references'][0];value=next(iter(doc['entries'].values()));value['references'].append(ordinary)
            if kind=='corrupt':ref['article_address_context']['page_hash']='c'*64
            if kind=='surface':value['changes']['surface']='架空神社'
            if kind=='excluded':data['entries'][0].update(status='excluded',reason='Existing exclusion')
            out=data
            for _ in range(3):
                out=apply_corrections(out,doc);self.assertEqual(eligible(out),[])
                if kind=='excluded':self.assertEqual((out['entries'][0]['status'],out['entries'][0]['reason']),('excluded','Existing exclusion'))

    def test_other_holds_and_repeated_exclusions_are_preserved(self):
        for kind in ['identity','facility','authority','excluded','corrupt_excluded']:
            data,doc,ref=fixture()
            if kind=='identity':data['entries'][0]['identity_review_required']=True
            if kind=='facility':data['facilities'][0].update(status='pending',reason='identity unresolved')
            if kind=='authority':data['collection']['authority_status']='unconfirmed'
            if 'excluded' in kind:data['entries'][0].update(status='excluded',reason='Existing exclusion')
            if kind=='corrupt_excluded':ref['article_address_context']['page_hash']='c'*64
            out=data
            for _ in range(3):
                out=apply_corrections(out,doc);self.assertEqual(eligible(out),[])
                if 'excluded' in kind:self.assertEqual((out['entries'][0]['status'],out['entries'][0]['reason']),('excluded','Existing exclusion'))

    def test_saved_context_corruption_stops_offline_output(self):
        data,doc,ref=fixture();out=apply_corrections(data,doc);self.assertEqual(len(eligible(out)),1)
        out['entries'][0]['correction']['references'][0]['article_address_context']['scope_element_index']=16
        self.assertTrue(validate(out));self.assertEqual(eligible(out),[])
