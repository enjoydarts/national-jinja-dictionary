"""Synthetic shrine facts; public archive and publication receipts are separate."""
import copy,unittest
from test_hyogo_building_location import fixture as building_fixture
from njd.locations import apply_locations,location_problems
from njd.validation import eligible,blocking_problems

KIND='hyogo_municipal_asset_location'

def fixture():
 d,_,s=building_fixture();f=d['facilities'][0];e=d['entries'][0];name=f['name_raw'];when=s['recorded_at'];profile=s['reference'];profile.update(locality_raw='人工谷',locality_context_raw='古来人工谷の明神として崇敬された。');profile['excerpt']+=' / '+profile['locality_context_raw']
 s.update(supplement_kind=KIND,changes=dict(address='淡路市人工谷123-4',municipality='淡路市'));s.pop('building_identity_proof');url='https://www.city.awaji.lg.jp/uploaded/attachment/44772.pdf'
 s['municipal_reference']=dict(url=url,page_hash='b3da6b887e1e8196d82083e9b2e069fcf24f70394658809b7b76f86669077422',title='淡路市 令和6年度 固定資産台帳',source_kind='government_municipal_asset_register',publisher='淡路市',fetched_at=when,checked_at=when,locator='PDF p.3 所在地/資産名称の同じ行',pdf_page_1based=3,asset_class_raw='事業用土地',name_raw=name,parcel_raw='人工谷123-4',municipality_raw='淡路市',source_fields={'所在地':'人工谷123-4','資産名称':name},excerpt='事業用土地 / 所在地：人工谷123-4 / 資産名称：'+name,published_link_proof=dict(source_url='https://www.city.awaji.lg.jp/soshiki/zaisei/23476.html',source_page_hash='c'*64,fetched_at=when,href_raw='/uploaded/attachment/44772.pdf',label_raw='R6_固定資産台帳 [PDFファイル／1.89MB]',url=url))
 reg=s['registry_reference'];fields=reg['source_fields'];fields.update(cityName='淡路市',streetNumber='人工谷１２３番地の４');full='兵庫県淡路市人工谷１２３番地の４';reg.update(address_raw=full,excerpt=name+' / '+full+' / 0000000')
 return d,dict(schema_version=1,facilities={f['id']:s}),s

class HyogoAssetLocationTest(unittest.TestCase):
 def test_asset_location_preserves_original_empty_fields_and_literal_reading(self):
  d,doc,s=fixture();original=copy.deepcopy(d);self.assertEqual(location_problems(s,d['facilities'][0],d['collection']),[])
  out=apply_locations(d,doc);f=out['facilities'][0];e=out['entries'][0]
  self.assertEqual((f['address'],f['municipality']),('淡路市人工谷123-4','淡路市'));self.assertEqual(e['reading'],'かくうはちまんじんじゃ');self.assertEqual(len(eligible(out)),1);self.assertFalse(blocking_problems(out))
  self.assertEqual(f['location_supplement']['original']['address'],'');self.assertEqual(f['address_raw'],'〒000-0000')
  for k in ('id','source_hash','page_hash','map_address_raw','xml_occurrences'):self.assertEqual(f[k],original['facilities'][0][k])
  for k in ('id','source_hash','reading_raw','reading_url','surface','printed_code_raw'):self.assertEqual(e[k],original['entries'][0][k])
  self.assertEqual(d,original);self.assertEqual(apply_locations(out,doc),out)

 def test_registry_branch_and_extra_aza_are_rejected_even_with_consistent_quotes(self):
  for street in ['人工谷１２３番地４０','人工谷字別１２３番地４','人工谷１２３番地５']:
   with self.subTest(street=street):
    d,doc,s=fixture();reg=s['registry_reference'];reg['source_fields']['streetNumber']=street;reg.update(address_raw='兵庫県淡路市'+street,excerpt=reg['name_raw']+' / 兵庫県淡路市'+street+' / 0000000');self.assertFalse(eligible(apply_locations(d,doc)))

 def test_locality_publication_and_independent_identity_mutations_hold(self):
  edits=[lambda s:s['reference'].update(locality_raw='別谷'),lambda s:s['municipal_reference'].update(pdf_page_1based=4),lambda s:s['municipal_reference'].update(asset_class_raw='市道'),lambda s:s['municipal_reference']['published_link_proof'].update(href_raw='/another.pdf'),lambda s:s['municipal_reference']['source_fields'].update(所在地='人工谷123-5'),lambda s:s['municipal_reference'].update(name_raw='別神社'),lambda s:s['registry_reference']['source_fields'].update(postCode='0000001'),lambda s:s['registry_reference']['source_fields'].update(furigana='ベツジンジャ'),lambda s:s['registry_reference']['registry_state_proof'].update(active_same_name_postcode_count=2),lambda s:s['registry_reference']['registry_state_proof'].update(target_corporate_or_full_parcel_events=1),lambda s:s['map_reference'].update(code_raw='6300002'),lambda s:s.update(expected_source_hash='f'*64)]
  for i,edit in enumerate(edits):
   with self.subTest(case=i):
    d,doc,s=fixture();edit(s);out=apply_locations(d,doc);self.assertFalse(eligible(out));self.assertEqual((out['facilities'][0]['address'],out['facilities'][0]['municipality']),('',''))

 def test_other_original_conditions_are_not_overridden(self):
  for case in ('name','reason','excluded','partial','address','authority','multiple'):
   with self.subTest(case=case):
    d,doc,s=fixture();f=d['facilities'][0];e=d['entries'][0]
    if case=='name':f['listed_name']='別神社'
    elif case=='reason':f['review_reason']='other'
    elif case=='excluded':e['status']='excluded'
    elif case=='partial':e['reading_raw']='カクウ'
    elif case=='address':f['address']='淡路市別谷5'
    elif case=='authority':d['collection']['authority_status']='unconfirmed'
    elif case=='multiple':d['entries'].append(dict(e,id='another'))
    self.assertFalse(eligible(apply_locations(d,doc)))

 def test_malformed_references_and_invalid_reapplication_fail_closed(self):
  for key in ('reference','map_reference','municipal_reference','registry_reference'):
   for bad in (None,[],0,'bad'):
    with self.subTest(key=key,value=bad):
     d,doc,s=fixture();s[key]=bad;self.assertFalse(eligible(apply_locations(d,doc)))
  d,doc,s=fixture();out=apply_locations(d,doc);self.assertEqual(len(eligible(out)),1);loc=out['facilities'][0]['location_supplement'];loc['municipal_reference']['published_link_proof']=None
  self.assertTrue(blocking_problems(out));doc['facilities'][s['facility_id']]=copy.deepcopy(loc);bad=apply_locations(out,doc);self.assertFalse(eligible(bad));self.assertEqual(bad['facilities'][0]['address'],'')

 def test_applied_single_entry_contract_blocks_entire_facility(self):
  for change in ('append','replace','remove'):
   with self.subTest(change=change):
    d,doc,s=fixture();out=apply_locations(d,doc);self.assertEqual(len(eligible(out)),1)
    if change=='append':out['entries'].append(dict(out['entries'][0],id='another'))
    elif change=='replace':out['entries'][0]['id']='another'
    else:out['entries']=[]
    self.assertFalse(eligible(out));self.assertTrue(any(p['kind']=='facility' and p['id']==s['facility_id'] for p in blocking_problems(out)))
