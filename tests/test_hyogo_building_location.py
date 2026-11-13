"""Artificial municipal-building evidence; not a factual identity assessment."""
import copy,hashlib,unittest
from test_hyogo_profile_review import fixture as profile_fixture
from njd.locations import apply_locations,location_problems
from njd.validation import eligible,blocking_problems

KIND='hyogo_cultural_building_location';REASON='Hyogo profile address is missing'

def fixture():
 d,_,v=profile_fixture();f=d['facilities'][0];e=d['entries'][0];name=f['name_raw'];kana=e['reading_raw'];code=f['native_source_id'];when=v['recorded_at']
 digest=hashlib.sha256((name+'\0'+kana+'\0').encode()).hexdigest()
 f.update(address='',address_raw='〒000-0000',municipality='',source_hash=digest,reason=REASON,review_reason=REASON,map_address_raw='')
 e.update(source_hash=digest,reading='',reason=REASON)
 m=f['xml_occurrences'][0];m.update(name_raw=name,address_raw='')
 profile,mapped,reg=copy.deepcopy(v['references']);profile.update(address_raw=f['address_raw'],excerpt=name+' / '+kana+' / '+code+'/兼務 / '+f['address_raw'])
 mapped.update(name_raw=name,address_raw='',excerpt=code+' / '+name)
 addr='洲本市架空町123-4';fields=reg['source_fields'];fields.update(cityName='洲本市',streetNumber='架空町字人工１２３番地の４',postCode='0000000');full='兵庫県'+fields['cityName']+fields['streetNumber'];reg.update(address_raw=full,excerpt=name+' / '+full+' / 0000000')
 state=reg['registry_state_proof'];state.update(active_same_name_postcode_corporate_numbers=[fields['corporateNumber']],active_same_name_postcode_count=1)
 town=dict(url='https://www.city.sumoto.lg.jp/soshiki/34/123.html',page_hash='c'*64,title='人工市文化財本殿',locator='本文文化財欄',source_kind='government_cultural_building',publisher='洲本市教育委員会生涯学習課',name_raw=name+'本殿',owner_name_raw=name,manager_name_raw=name,address_raw=addr,reading_raw='カクウハチマンジンジャホンデン',reading_scope='building_full_name',fetched_at=when,checked_at=when,excerpt=name+'本殿 / '+name+' / '+addr+' / 洲本市教育委員会生涯学習課')
 binding=dict(profile_page_hash=profile['page_hash'],municipal_page_hash=town['page_hash'],name_raw=name,profile_code_raw=code,building_name_raw=name+'本殿',registered_additional_aza_raw='字人工',chronology=[dict(event='construction',year='1603',profile_raw='慶長8年(1603)、本殿上棟',municipal_raw='慶長8年（1603年）に再興'),dict(event='repair',year='1724',profile_raw='享保9年(1724)、本殿改修',municipal_raw='享保9年（1724年）にも修理'),dict(event='repair',year='1845',profile_raw='弘化2年(1845)、本殿改修',municipal_raw='弘化2年（1845年）にも修理')],structure=dict(profile_raw='三間社流造',municipal_raw='三間社流造'))
 for x in binding['chronology']:profile['excerpt']+=' / '+x['profile_raw'];town['excerpt']+=' / '+x['municipal_raw']
 profile['excerpt']+=' / 三間社流造';town['excerpt']+=' / 三間社流造'
 s=dict(supplement_kind=KIND,status='verified',facility_id=f['id'],entry_id=e['id'],expected_source_hash=digest,original={k:f.get(k) for k in ('name_raw','address','municipality','listing_url','official_site_url','native_source_id')},reason='人工市本殿と原実codeの個別同定',recorded_at=when,changes=dict(address=addr,municipality='洲本市'),reference=profile,map_reference=mapped,municipal_reference=town,registry_reference=reg,building_identity_proof=binding)
 return d,dict(schema_version=1,facilities={f['id']:s}),s

class HyogoBuildingLocationTest(unittest.TestCase):
 def test_only_derived_address_and_original_literal_kana_are_adopted(self):
  d,doc,s=fixture();before=copy.deepcopy(d);f=d['facilities'][0];e=d['entries'][0]
  self.assertEqual(location_problems(s,f,d['collection']),[])
  out=apply_locations(d,doc);g=out['facilities'][0];x=out['entries'][0]
  self.assertEqual((g['address'],g['municipality']),('洲本市架空町123-4','洲本市'));self.assertEqual(len(eligible(out)),1);self.assertFalse(blocking_problems(out));self.assertEqual(x['reading'],'かくうはちまんじんじゃ')
  for k in ('id','source_hash','address_raw','map_address_raw','xml_occurrences','name_raw','review_reason'):self.assertEqual(g[k],f[k])
  for k in ('id','source_hash','reading_raw','reading_url','name_raw','surface','printed_code_raw'):self.assertEqual(x[k],e[k])
  self.assertEqual(d,before);self.assertEqual(apply_locations(out,doc),out)

 def test_independent_identity_and_provenance_mutations_are_rejected(self):
  edits=[lambda s:s.update(expected_source_hash='f'*64),lambda s:s['reference'].update(page_hash='f'*64),lambda s:s['reference'].update(printed_code_raw='6300002/兼務'),lambda s:s['reference'].update(reading_raw='ベツジンジャ'),lambda s:s['map_reference'].update(code_raw='6300002'),lambda s:s['changes'].update(address='洲本市架空町123'),lambda s:s['municipal_reference'].update(owner_name_raw='架空神社'),lambda s:s['municipal_reference'].update(manager_name_raw='架空神社'),lambda s:s['municipal_reference'].update(url='https://example.invalid/x'),lambda s:s['building_identity_proof']['chronology'].pop(),lambda s:s['building_identity_proof']['chronology'][1].update(year='1725'),lambda s:s['building_identity_proof']['chronology'][1].update(municipal_raw='享保10年（1725年）'),lambda s:s['building_identity_proof'].update(municipal_page_hash='f'*64),lambda s:s['building_identity_proof']['structure'].update(municipal_raw='一間社流造'),lambda s:s['registry_reference']['source_fields'].update(postCode='0000001'),lambda s:s['registry_reference']['source_fields'].update(furigana='ベツジンジャ'),lambda s:s['registry_reference']['registry_state_proof'].update(active_same_name_postcode_count=2),lambda s:s['registry_reference']['registry_state_proof']['daily_resources'].pop(),lambda s:s.update(recorded_at='2020-01-01T00:00:00+00:00')]
  for i,edit in enumerate(edits):
   with self.subTest(i=i):
    d,doc,s=fixture();edit(s);o=apply_locations(d,doc);self.assertFalse(eligible(o));self.assertEqual(o['facilities'][0]['address'],'')

 def test_wrong_branch_with_consistent_quotes_is_rejected(self):
  d,doc,s=fixture();reg=s['registry_reference'];reg['source_fields']['streetNumber']='架空町字人工１２３番地の４０';reg['address_raw']='兵庫県洲本市架空町字人工１２３番地の４０';reg['excerpt']=reg['name_raw']+' / '+reg['address_raw']+' / 0000000'
  self.assertFalse(eligible(apply_locations(d,doc)))

 def test_other_pending_conditions_and_original_fields_are_not_overridden(self):
  for case in ('reason','review_reason','address','map_address','glyph','identity','excluded','entry_kana','entry_code','authority','extra_entry'):
   with self.subTest(case=case):
    d,doc,s=fixture();f=d['facilities'][0];e=d['entries'][0]
    if case=='reason':f['reason']='other'
    elif case=='review_reason':f['review_reason']='other'
    elif case=='address':f['address']='洲本市別町1'
    elif case=='map_address':f['map_address_raw']='洲本市別町1'
    elif case=='glyph':f['name_rendering_status']='external_glyph'
    elif case=='identity':e['identity_review_required']=True
    elif case=='excluded':e['status']='excluded'
    elif case=='entry_kana':e['reading_raw']='ベツジンジャ'
    elif case=='entry_code':e['printed_code_raw']='6300002/兼務'
    elif case=='authority':d['collection']['authority_status']='unconfirmed'
    elif case=='extra_entry':d['entries'].append(dict(e,id='another'))
    self.assertFalse(eligible(apply_locations(d,doc)))

 def test_invalid_reapplication_restores_original_empty_fields_and_blocks_validation(self):
  d,doc,s=fixture();out=apply_locations(d,doc);self.assertEqual(len(eligible(out)),1)
  f=out['facilities'][0];f['location_supplement']['building_identity_proof']['chronology'].pop();self.assertTrue(blocking_problems(out));doc['facilities'][f['id']]=copy.deepcopy(f['location_supplement']);bad=apply_locations(out,doc);self.assertEqual((bad['facilities'][0]['address'],bad['facilities'][0]['municipality']),('',''));self.assertFalse(eligible(bad))

 def test_malformed_profile_reference_holds_and_validates_without_exception(self):
  # A broken saved reference must not interrupt national overlay application.
  for bad in (None,[],0,'bad'):
   for phase in ('initial','validate','reapply'):
    with self.subTest(value=bad,phase=phase):
     d,doc,s=fixture();fid=d['facilities'][0]['id']
     if phase=='initial':
      s['reference']=bad;out=apply_locations(d,doc)
     else:
      out=apply_locations(d,doc)
      if phase=='validate':
       out['facilities'][0]['location_supplement']['reference']=bad
       self.assertTrue(blocking_problems(out));continue
      s['reference']=bad;out=apply_locations(out,doc)
     self.assertFalse(eligible(out))
     self.assertEqual((out['facilities'][0]['address'],out['facilities'][0]['municipality']),('',''))
     self.assertEqual(out['facilities'][0]['address_raw'],'〒000-0000')
