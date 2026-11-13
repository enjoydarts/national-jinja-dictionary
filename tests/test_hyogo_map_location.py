"""Synthetic shrine identity; public archive/ordinance provenance is separate."""
import copy,hashlib,unittest
from test_hyogo_profile_review import fixture as profile_fixture
from njd.locations import apply_locations,location_problems
from njd.validation import eligible,blocking_problems

KIND='hyogo_documented_map_location';REASON='Hyogo map and profile addresses differ'

def fixture():
 d,_,v=profile_fixture();f=d['facilities'][0];e=d['entries'][0];name=f['name_raw'];kana=e['reading_raw'];code=f['native_source_id'];when=v['recorded_at']
 address='丹波丹波篠山市架空町5';raw='〒000-0000\n'+address;digest=hashlib.sha256('\0'.join((name,kana,address)).encode()).hexdigest()
 f.update(address=address,address_raw=raw,municipality='丹波丹波篠山市',source_hash=digest,reason=REASON,review_reason=REASON,map_address_raw='篠山市架空町5')
 e.update(source_hash=digest,reason=REASON);m=f['xml_occurrences'][0];m.update(name_raw=name,address_raw='篠山市架空町5')
 profile,mapped,reg=copy.deepcopy(v['references']);profile.update(address_raw=raw,excerpt=name+' / '+kana+' / '+code+'/兼務 / '+raw)
 mapped.update(name_raw=name,address_raw=m['address_raw'],excerpt=code+' / '+name+' / '+m['address_raw'])
 fields=reg['source_fields'];fields.update(cityName='丹波篠山市',streetNumber='架空町５番地',postCode='0000000');full='兵庫県丹波篠山市架空町５番地';reg.update(address_raw=full,excerpt=name+' / '+full+' / 0000000')
 reg['registry_state_proof'].update(active_same_name_postcode_count=1,active_same_name_postcode_corporate_numbers=[fields['corporateNumber']])
 ordinance=dict(url='https://www.city.tambasasayama.lg.jp/section/reiki_int/reiki_honbun/j700RG00001635.html',page_hash='9ae4e9f544807232c87d1df1b1faa129328316dd6935aefaa74c4f9af876e6e2',fetched_at=when,checked_at=when,title='市の名称を変更する条例',source_kind='government_municipality',publisher='丹波篠山市',locator='本則・附則',former_prefix_raw='篠山市',current_prefix_raw='丹波篠山市',effective_date='2019-05-01',excerpt='篠山市の名称を丹波篠山市に変更する。 この条例は、平成31年5月1日から施行する。')
 s=dict(supplement_kind=KIND,status='verified',facility_id=f['id'],entry_id=e['id'],expected_source_hash=digest,recorded_at=when,reason='人工の同コード旧地図・条例・一意登記を個別照合',original={k:f.get(k) for k in ('name_raw','address','municipality','listing_url','official_site_url','native_source_id')},changes=dict(address=full,municipality='丹波篠山市'),reference=profile,map_reference=mapped,registry_reference=reg,municipality_reference=ordinance)
 return d,dict(schema_version=1,facilities={f['id']:s}),s

class HyogoMapLocationTest(unittest.TestCase):
 def test_selects_independent_address_and_preserves_original_fields(self):
  d,doc,s=fixture();old=copy.deepcopy(d);self.assertEqual(location_problems(s,d['facilities'][0],d['collection']),[])
  out=apply_locations(d,doc);f=out['facilities'][0];e=out['entries'][0]
  self.assertEqual((f['address'],f['municipality']),('兵庫県丹波篠山市架空町５番地','丹波篠山市'));self.assertEqual(e['reading'],'かくうはちまんじんじゃ');self.assertEqual(len(eligible(out)),1);self.assertFalse(blocking_problems(out))
  for k in ('id','source_hash','address_raw','map_address_raw','xml_occurrences','review_reason'):self.assertEqual(f[k],old['facilities'][0][k])
  for k in ('id','name_raw','surface','reading_raw','reading_url','printed_code_raw','source_hash'):self.assertEqual(e[k],old['entries'][0][k])
  self.assertEqual(f['location_supplement']['original']['address'],'丹波丹波篠山市架空町5');self.assertEqual(d,old);self.assertEqual(apply_locations(out,doc),out)

 def test_registry_branch_difference_cannot_be_hidden_in_consistent_quotes(self):
  for street in ['架空町５０番地','架空町５番地１','別町５番地']:
   with self.subTest(street=street):
    d,doc,s=fixture();reg=s['registry_reference'];reg['source_fields']['streetNumber']=street;full='兵庫県丹波篠山市'+street;reg.update(address_raw=full,excerpt=reg['name_raw']+' / '+full+' / 0000000');s['changes']['address']=full
    out=apply_locations(d,doc);self.assertFalse(eligible(out));self.assertEqual(out['facilities'][0]['address'],'丹波丹波篠山市架空町5')

 def test_missing_identity_and_provenance_hold_the_registration(self):
  mutations=[lambda s:s.update(expected_source_hash='f'*64),lambda s:s.update(entry_id='other'),lambda s:s['reference'].update(reading_raw='ベツジンジャ'),lambda s:s['map_reference'].update(code_raw='6300002'),lambda s:s['municipality_reference'].update(effective_date='2019-05-02'),lambda s:s['municipality_reference'].update(page_hash='f'*64),lambda s:s['map_reference']['protocol_reference'].update(page_hash='f'*64),lambda s:s['registry_reference']['source_fields'].update(postCode='0000001'),lambda s:s['registry_reference']['source_fields'].update(furigana='ベツジンジャ'),lambda s:s['registry_reference']['registry_state_proof'].update(active_shrine_corporation_count_at_full_address=2),lambda s:s['registry_reference']['registry_state_proof'].update(active_same_name_postcode_count=2),lambda s:s['registry_reference']['registry_state_proof']['daily_resources'].pop(),lambda s:s.update(recorded_at='2020-01-01T00:00:00+00:00')]
  for i,change in enumerate(mutations):
   with self.subTest(case=i):
    d,doc,s=fixture();change(s);out=apply_locations(d,doc);self.assertFalse(eligible(out))

 def test_other_conditions_and_multiple_entries_are_not_overridden(self):
  for case in ('reason','excluded','authority','name','identity','glyph','extra_entry','partial_kana'):
   with self.subTest(case=case):
    d,doc,s=fixture();f=d['facilities'][0];e=d['entries'][0]
    if case=='reason':f['review_reason']='other'
    elif case=='excluded':e['status']='excluded'
    elif case=='authority':d['collection']['authority_status']='unconfirmed'
    elif case=='name':f['listed_name']='別神社'
    elif case=='identity':f['identity_review_required']=True
    elif case=='glyph':f['name_rendering_status']='external_glyph'
    elif case=='extra_entry':d['entries'].append(dict(e,id='another'))
    elif case=='partial_kana':e['reading_raw']='カクウ'
    self.assertFalse(eligible(apply_locations(d,doc)))

 def test_broken_references_hold_instead_of_interrupting_application(self):
  for field in ('reference','map_reference','registry_reference','municipality_reference'):
   for value in (None,[],0,'bad'):
    with self.subTest(field=field,value=value):
     d,doc,s=fixture();s[field]=value;out=apply_locations(d,doc);self.assertFalse(eligible(out));self.assertEqual(out['facilities'][0]['address'],'丹波丹波篠山市架空町5')

 def test_invalid_applied_evidence_is_detected_and_reapplication_restores_raw(self):
  d,doc,s=fixture();out=apply_locations(d,doc);self.assertEqual(len(eligible(out)),1)
  loc=out['facilities'][0]['location_supplement'];loc['registry_reference']['source_fields']['postCode']='0000001';self.assertTrue(blocking_problems(out))
  doc['facilities'][s['facility_id']]=copy.deepcopy(loc);bad=apply_locations(out,doc);self.assertFalse(eligible(bad));self.assertEqual((bad['facilities'][0]['address'],bad['facilities'][0]['municipality']),('丹波丹波篠山市架空町5','丹波丹波篠山市'))

 def test_applied_single_registration_contract_blocks_the_entire_facility(self):
  from test_hyogo_building_location import fixture as building_fixture
  # The shared location contract must keep the original candidate out of
  # dictionaries even when the added, unreviewed candidate is rejected alone.
  for make in (fixture,building_fixture):
   for change in ('append','replace','remove'):
    with self.subTest(kind=make.__module__,change=change):
     d,doc,s=make();out=apply_locations(d,doc);self.assertEqual(len(eligible(out)),1)
     if change=='append':out['entries'].append(dict(out['entries'][0],id='unreviewed-second-entry'))
     elif change=='replace':out['entries'][0]['id']='unreviewed-second-entry'
     else:out['entries']=[]
     self.assertFalse(eligible(out));self.assertTrue(any(p['kind']=='facility' and p['id']==s['facility_id'] for p in blocking_problems(out)))
