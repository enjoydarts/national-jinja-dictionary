import copy
import unittest
from test_records import build,row
from njd.corrections import apply_corrections
from njd.validation import eligible,validate
from njd.exporters import render
from njd.storage import apply_decisions


def correction(d,changes):
    f=d['facilities'][0];e=d['entries'][0]
    surface=changes.get('surface',e['surface']);reading=changes.get('reading','かくうじんじゃ')
    return {'schema_version':1,'entries':{e['id']:dict(status='verified',facility_id=f['id'],expected_source_hash=e['source_hash'],
        original=dict(name_raw=f['name_raw'],reading_raw=e['reading_raw'],address=f['address'],listing_url=f['listing_url']),
        changes=changes,reason='reference name, full reading and exact address inspected',identity_match='same city and parcel; native listing identity retained',
        references=[dict(url='https://reference.example.invalid/shrine',title='Synthetic reference',source_kind='reference',name_raw=surface,
            reading_raw=reading,address_raw=f['address'],excerpt=surface+'（'+reading+'） '+f['address'],checked_at='2026-11-09T00:00:00+09:00')])}}

class CorrectionTest(unittest.TestCase):
    def test_name_correction_keeps_original_and_restores_valid_candidate(self):
        d=build([row(name='架空\n神社')]);before=copy.deepcopy(d)
        result=apply_corrections(d,correction(d,{'surface':'架空神社'}))
        self.assertEqual(d,before);self.assertEqual(result['facilities'][0]['name_raw'],'架空\n神社')
        self.assertEqual(result['entries'][0]['surface'],'架空神社')
        self.assertEqual(validate(result),[]);self.assertEqual(len(eligible(result)),1)
    def test_external_reading_correction_keeps_acquired_reading(self):
        d=build([row(reading_raw='誤入力')]);result=apply_corrections(d,correction(d,{'reading':'かくうじんじゃ'}))
        self.assertEqual(result['entries'][0]['reading_raw'],'誤入力')
        self.assertEqual(result['entries'][0]['reading_source_kind'],'reference')
        self.assertEqual(render(result,'mozc').rows,1)
    def test_missing_or_nonmatching_reference_never_confirms_reading(self):
        d=build([row(reading_raw='誤入力')]);c=correction(d,{'reading':'かくうじんじゃ'})
        c['entries'][d['entries'][0]['id']]['references'][0]['reading_raw']='べつのよみ'
        self.assertEqual(eligible(apply_corrections(d,c)),[])
    def test_stale_correction_requires_review(self):
        original=build([row()]);c=correction(original,{'surface':'架空神社'})
        changed=build([row(reading_raw='ベツヨミ')]);out=apply_corrections(changed,c)
        self.assertEqual(out['entries'][0]['status'],'pending')
        self.assertEqual(eligible(out),[])
    def test_external_reference_cannot_replace_agency_listing_authority(self):
        d=build([row()]);d['collection']['authority_status']='pending'
        result=apply_corrections(d,correction(d,{'reading':'かくうじんじゃ'}))
        self.assertEqual(eligible(result),[])
    def test_manual_exclusion_takes_precedence_over_correction(self):
        d=build([row(reading_raw='誤入力')]);e=d['entries'][0]
        result=apply_corrections(d,correction(d,{'reading':'かくうじんじゃ'}))
        result=apply_decisions(result,{e['id']:dict(expected_source_hash=e['source_hash'],status='excluded',reason='reviewed exclusion')})
        self.assertEqual(eligible(result),[])

    def test_name_fix_does_not_confirm_an_unresolved_reading(self):
        d=build([row(name='架空\n神社',reading_raw='不明')])
        out=apply_corrections(d,correction(d,{'surface':'架空神社'}))
        self.assertEqual(out['entries'][0]['status'],'pending')
        self.assertEqual(eligible(out),[])

    def test_missing_source_name_uses_reference_without_inventing_original(self):
        d=build([row(name='')])
        out=apply_corrections(d,correction(d,{'surface':'架空神社'}))
        self.assertEqual(out['facilities'][0]['name_raw'],'')
        self.assertEqual(out['entries'][0]['surface'],'架空神社')
        self.assertEqual(len(eligible(out)),1)

    def test_reference_for_another_facility_cannot_supply_reading(self):
        d=build([row(reading_raw='不明')]);c=correction(d,{'reading':'かくうじんじゃ'})
        ref=c['entries'][d['entries'][0]['id']]['references'][0]
        ref.update(name_raw='別神社',address_raw='別県別市99',excerpt='別神社 かくうじんじゃ 別県別市99')
        self.assertEqual(eligible(apply_corrections(d,c)),[])

    def test_reading_reference_is_bound_to_the_identified_facility(self):
        d=build([row(reading_raw='不明')]);c=correction(d,{'reading':'かくうじんじゃ'})
        refs=c['entries'][d['entries'][0]['id']]['references'];other=copy.deepcopy(refs[0])
        refs[0]['reading_raw']='';refs[0]['excerpt']=refs[0]['name_raw']+' '+refs[0]['address_raw']
        other.update(address_raw='別県別市99',excerpt='架空神社 かくうじんじゃ 別県別市99');refs.append(other)
        self.assertEqual(eligible(apply_corrections(d,c)),[])

    def test_name_correction_keeps_unrelated_identity_quarantine(self):
        d=build([row(review_reason='source identity conflict requires review')])
        self.assertEqual(eligible(apply_corrections(d,correction(d,{'surface':'架空神社'}))),[])

    def test_name_correction_keeps_carriage_return_address_quarantine(self):
        d=build([row(address='架空市乙町1\r架空市乙町2')])
        self.assertEqual(eligible(apply_corrections(d,correction(d,{'surface':'架空神社'}))),[])

    def test_location_comparison_accepts_explicit_county_but_not_other_prefecture(self):
        d=build([row(address='架空町乙1',municipality='架空町',reading_raw='不明')])
        d['facilities'][0]['prefecture']='架空県'
        c=correction(d,{'reading':'かくうじんじゃ'});ref=c['entries'][d['entries'][0]['id']]['references'][0]
        ref['address_raw']='〒123-4567 架空県架空郡架空町乙１番地';ref['excerpt']='架空神社 かくうじんじゃ '+ref['address_raw']
        self.assertEqual(len(eligible(apply_corrections(d,c))),1)
        ref['address_raw']='他県架空郡架空町乙１番地';ref['excerpt']='架空神社 かくうじんじゃ '+ref['address_raw']
        self.assertEqual(eligible(apply_corrections(d,c)),[])

    def test_explicit_parcel_separator_comparison_keeps_branch_number(self):
        d=build([row(address='架空市乙町88-1',reading_raw='不明')]);c=correction(d,{'reading':'かくうじんじゃ'})
        ref=c['entries'][d['entries'][0]['id']]['references'][0]
        ref['address_raw']='架空市乙町８８番地の１';ref['excerpt']='架空神社 かくうじんじゃ '+ref['address_raw']
        self.assertEqual(len(eligible(apply_corrections(d,c))),1)
        ref['address_raw']='架空市乙町８８番地の２';ref['excerpt']='架空神社 かくうじんじゃ '+ref['address_raw']
        self.assertEqual(eligible(apply_corrections(d,c)),[])

    def test_locality_prefix_does_not_establish_different_place_name(self):
        d=build([row(address='架空町福岡',reading_raw='不明')]);c=correction(d,{'reading':'かくうじんじゃ'})
        ref=c['entries'][d['entries'][0]['id']]['references'][0]
        ref['address_raw']='架空町福岡原123';ref['excerpt']='架空神社 かくうじんじゃ '+ref['address_raw']
        self.assertEqual(eligible(apply_corrections(d,c)),[])

    def test_session_query_change_keeps_correction_for_same_native_facility(self):
        d=build([row(reading_raw='不明')]);c=correction(d,{'reading':'かくうじんじゃ'})
        updated=copy.deepcopy(d)
        for r in updated['facilities']+updated['entries']:r['listing_url']+='?page=2&session=new'
        out=apply_corrections(updated,c)
        self.assertEqual(len(eligible(out)),1)
        self.assertEqual(out['entries'][0]['correction']['original']['listing_url'],d['facilities'][0]['listing_url'])
        changed=copy.deepcopy(updated)
        for r in changed['facilities']+changed['entries']:r['listing_url']='https://other.example.invalid/shrines/1'
        self.assertEqual(eligible(apply_corrections(changed,c)),[])

    def test_changed_endpoint_or_invalid_snapshot_url_is_not_accepted(self):
        d=build([row(reading_raw='不明')]);c=correction(d,{'reading':'かくうじんじゃ'})
        c['entries'][d['entries'][0]['id']]['original']['listing_url']=123
        self.assertEqual(eligible(apply_corrections(d,c)),[])
        c=correction(d,{'reading':'かくうじんじゃ'});updated=copy.deepcopy(d)
        updated['facilities'][0]['native_source_id']=None
        for r in updated['facilities']+updated['entries']:r['listing_url']+='?session=new'
        self.assertEqual(eligible(apply_corrections(updated,c)),[])
