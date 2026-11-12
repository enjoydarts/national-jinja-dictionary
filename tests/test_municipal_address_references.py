"""Safety boundaries for literal municipal CSV address evidence."""
import copy
import unittest
from test_records import row
from test_corrections import correction
from njd.records import build_dataset
from njd.corrections import apply_corrections
from njd.validation import eligible


def municipal_candidate(address='高知県高岡郡檮原町架空地区42番地',prefecture='高知県',code='39'):
    data=build_dataset('example',code,prefecture,'架空県神社庁',[row(address=address,reading_raw='')])
    doc=correction(data,{'reading':'かくうじんじゃ'})
    ref=doc['entries'][data['entries'][0]['id']]['references'][0]
    parts={'都道府県名':prefecture,'市区町村名':'梼原町','住所':'架空地区42番地'}
    ref.update(source_kind='municipal_open_data',page_hash='b'*64,csv_row=7,locator='CSV row 7',
               address_raw=''.join(parts.values()),address_components=parts,
               excerpt='架空神社 / かくうじんじゃ / '+' / '.join(k+'='+v for k,v in parts.items()))
    return data,doc,ref


class MunicipalAddressReferenceTest(unittest.TestCase):
    def test_literal_columns_support_reading_without_fabricating_contiguous_quote(self):
        data,doc,ref=municipal_candidate(address='高知県高岡郡梼原町架空地区42番地')
        before=copy.deepcopy(data);source=copy.deepcopy(ref)
        self.assertNotIn(ref['address_raw'],ref['excerpt'])
        out=apply_corrections(data,doc)
        self.assertEqual(len(eligible(out)),1)
        self.assertEqual(out['entries'][0]['reading'],'かくうじんじゃ')
        self.assertEqual(out['facilities'][0]['address'],'高知県高岡郡梼原町架空地区42番地')
        self.assertEqual(out['entries'][0]['correction']['references'][0],source)
        self.assertEqual(data,before)

    def test_yusuhara_municipality_spelling_preserves_raw_address(self):
        data,doc,ref=municipal_candidate()
        ref.pop('address_components');ref['excerpt']='架空神社 かくうじんじゃ '+ref['address_raw']
        out=apply_corrections(data,doc)
        self.assertEqual(len(eligible(out)),1)
        self.assertEqual(out['facilities'][0]['address'],'高知県高岡郡檮原町架空地区42番地')

    def test_old_municipality_with_separate_literal_columns_can_be_identified(self):
        data,doc,ref=municipal_candidate()
        self.assertEqual(len(eligible(apply_corrections(data,doc))),1)

    def test_missing_or_unverifiable_columns_cannot_resolve_identity(self):
        for mutate in [
            lambda r:r.pop('address_components'),
            lambda r:r['address_components'].pop('市区町村名'),
            lambda r:r['address_components'].update(郡='高岡郡'),
            lambda r:r['address_components'].update(住所=''),
            lambda r:r['address_components'].update(住所=42),
            lambda r:r.update(source_kind='reference'),
            lambda r:r.update(csv_row=0),
            lambda r:r.update(csv_row=True),
            lambda r:r.update(page_hash='not-a-digest'),
            lambda r:r.update(locator=''),
            lambda r:r.update(excerpt='架空神社 かくうじんじゃ 高知県 梼原町 架空地区42番地'),
        ]:
            data,doc,ref=municipal_candidate(address='高知県高岡郡梼原町架空地区42番地')
            mutate(ref)
            self.assertEqual(eligible(apply_corrections(data,doc)),[])

    def test_city_or_name_or_parcel_differences_are_not_repaired(self):
        for field,value in [('住所','架空地区42番地1'),('住所','架空地区420番地'),
                            ('住所','架空地区字東42番地'),('市区町村名','別町'),('都道府県名','愛媛県')]:
            data,doc,ref=municipal_candidate()
            ref['address_components'][field]=value
            ref['address_raw']=''.join(ref['address_components'].values())
            ref['excerpt']='架空神社 / かくうじんじゃ / '+' / '.join(k+'='+v for k,v in ref['address_components'].items())
            self.assertEqual(eligible(apply_corrections(data,doc)),[])
        data,doc,ref=municipal_candidate()
        ref['name_raw']='別神社';ref['excerpt']=ref['excerpt'].replace('架空神社','別神社')
        self.assertEqual(eligible(apply_corrections(data,doc)),[])

    def test_town_glyph_comparison_does_not_replace_locality_or_other_prefecture(self):
        for address,prefecture,code,actual in [
            ('高知県架空市檮原町42','高知県','39','高知県架空市梼原町42'),
            ('埼玉県高岡郡檮原町架空地区42番地','埼玉県','11','埼玉県梼原町架空地区42番地'),
            ('高知県別郡檮原町架空地区42番地','高知県','39','高知県高岡郡梼原町架空地区42番地')]:
            data,doc,ref=municipal_candidate(address,prefecture,code)
            ref.pop('address_components');ref['address_raw']=actual
            ref['excerpt']='架空神社 かくうじんじゃ '+actual
            self.assertEqual(eligible(apply_corrections(data,doc)),[])

    def test_municipality_only_observation_does_not_gain_a_parcel_through_glyph_matching(self):
        data,doc,ref=municipal_candidate(address='高知県高岡郡檮原町')
        self.assertEqual(eligible(apply_corrections(data,doc)),[])

    def test_reverse_municipality_spelling_keeps_reference_literal(self):
        data,doc,ref=municipal_candidate(address='高知県高岡郡梼原町架空地区42番地')
        ref['address_components']['市区町村名']='檮原町'
        ref['address_raw']=''.join(ref['address_components'].values())
        ref['excerpt']='架空神社 / かくうじんじゃ / '+' / '.join(k+'='+v for k,v in ref['address_components'].items())
        out=apply_corrections(data,doc)
        self.assertEqual(len(eligible(out)),1)
        self.assertEqual(out['entries'][0]['correction']['references'][0]['address_components']['市区町村名'],'檮原町')
