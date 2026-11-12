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


def aza_reference():
    d=build([row(name='●神社(外字注記)',address='架空市甲町1738-2',
                 review_reason='annotated official name requires review')])
    c=correction(d,{'surface':'架空神社','reading':'かくうじんじゃ'})
    f=d['facilities'][0];ref=c['entries'][d['entries'][0]['id']]['references'][0]
    href=f['listing_url'].replace('https://','http://',1)
    ref.update(page_hash='b'*64,address_raw='埼玉県架空市甲町字岩内1738-2',
               excerpt='架空神社（かくうじんじゃ） 埼玉県架空市甲町字岩内1738-2')
    ref['address_identity_proof']=dict(kind='additional_aza_with_subject_link',added_aza_raw='字岩内',
        subject_link=dict(reference_url=ref['url'],reference_page_hash=ref['page_hash'],
            relation='subject_agency_profile',href=href,locator='External links: subject agency profile',
            responses=[dict(url=href,status=302,location=f['listing_url'],page_hash='c'*64,
                            fetched_at='2026-11-09T00:00:00+09:00'),
                       dict(url=f['listing_url'],status=200,page_hash=f['page_hash'],
                            fetched_at='2026-11-09T00:00:01+09:00')]))
    return d,c,ref


class AgencyRegistryReadingTest(unittest.TestCase):
    def candidate(self,raw,full,scope='partial_or_absent'):
        d=build([row(name='架空神社',reading_raw='')]);c=correction(d,{'reading':full})
        value=c['entries'][d['entries'][0]['id']];ref=value['references'][0]
        ref['source_kind']='government_corporate_register'
        primary=copy.deepcopy(ref);primary.update(url=d['facilities'][0]['listing_url'],source_kind='agency',
            reading_raw=raw,reading_scope=scope,excerpt='架空神社 '+raw+' '+ref['address_raw'])
        value['references'].insert(0,primary)
        return d,c

    def test_prefix_only_agreement_cannot_hide_an_extra_sound(self):
        for raw,full in [('カクウ','かくうだじんじゃ'),('カク','かくうじんじゃ')]:
            with self.subTest(raw=raw,full=full):
                d,c=self.candidate(raw,full)
                self.assertEqual(eligible(apply_corrections(d,c)),[])

    def test_exact_stem_and_full_readings_do_not_generate_any_suffix(self):
        for raw,scope in [('カクウ','partial_or_absent'),('カクウジンジャ','full_name')]:
            d,c=self.candidate(raw,'かくうじんじゃ',scope);before=copy.deepcopy(c)
            out=apply_corrections(d,c);self.assertEqual(len(eligible(out)),1)
            self.assertEqual(out['entries'][0]['reading'],'かくうじんじゃ');self.assertEqual(c,before)

    def test_explicit_full_agency_reading_must_agree_with_proposed_reading(self):
        d,c=self.candidate('カクウジンジャ','かくうだじんじゃ','full_name')
        self.assertEqual(eligible(apply_corrections(d,c)),[])

class AzaReferenceTest(unittest.TestCase):
    def test_additional_aza_with_observed_subject_link_resolves_name_only_hold(self):
        d,c,ref=aza_reference();before=copy.deepcopy(d)
        out=apply_corrections(d,c)
        self.assertEqual(len(eligible(out)),1)
        self.assertEqual(out['entries'][0]['surface'],'架空神社')
        self.assertEqual(out['entries'][0]['reading'],'かくうじんじゃ')
        self.assertEqual(out['facilities'][0]['address'],'架空市甲町1738-2')
        self.assertEqual(out['facilities'][0]['name_raw'],'●神社(外字注記)')
        self.assertEqual(out['entries'][0]['correction']['references'][0]['address_raw'],
                         '埼玉県架空市甲町字岩内1738-2')
        self.assertEqual(d,before)

    def test_direct_subject_link_also_accepts_explicit_koaza(self):
        d,c,ref=aza_reference();proof=ref['address_identity_proof'];link=proof['subject_link']
        link['href']=d['facilities'][0]['listing_url'];link['responses']=link['responses'][1:]
        proof['added_aza_raw']='小字岩内'
        ref['address_raw']='埼玉県架空市甲町小字岩内1738-2'
        ref['excerpt']='架空神社 かくうじんじゃ '+ref['address_raw']
        self.assertEqual(len(eligible(apply_corrections(d,c))),1)

    def test_same_aza_difference_without_complete_bound_link_stays_pending(self):
        mutations=[
            lambda r:r.pop('address_identity_proof'),
            lambda r:r['address_identity_proof']['subject_link'].pop('locator'),
            lambda r:r['address_identity_proof']['subject_link'].update(locator=42),
            lambda r:r['address_identity_proof']['subject_link'].update(locator='   '),
            lambda r:r['address_identity_proof']['subject_link'].update(reference_page_hash='d'*64),
            lambda r:r['address_identity_proof']['subject_link'].update(reference_url='https://other.example.invalid/'),
            lambda r:r['address_identity_proof']['subject_link'].update(relation='nearby_shrine'),
            lambda r:r['address_identity_proof']['subject_link']['responses'][-1].update(page_hash='d'*64),
            lambda r:r['address_identity_proof']['subject_link']['responses'][0].update(location='https://other.example.invalid/'),
            lambda r:r['address_identity_proof']['subject_link']['responses'][0].pop('fetched_at'),
            lambda r:r['address_identity_proof']['subject_link']['responses'][-1].update(status=403),
            lambda r:r['address_identity_proof']['subject_link']['responses'][-1].update(url='https://agency.example.invalid/shrines/2'),
            lambda r:r['address_identity_proof'].update(added_aza_raw='字別所'),
            lambda r:r['address_identity_proof']['subject_link'].update(href='http://agency.example.invalid/shrines/2'),
            lambda r:r['address_identity_proof']['subject_link'].update(href='http://agency.example.invalid/shrines/1?facility=2'),
            lambda r:r['address_identity_proof']['subject_link'].update(href='http://user@agency.example.invalid/shrines/1'),
            lambda r:r['address_identity_proof']['subject_link']['responses'][0].update(page_hash='not-a-digest'),
            lambda r:r['address_identity_proof']['subject_link']['responses'][0].update(fetched_at='2026-11-09'),
            lambda r:r.update(page_hash='d'*64),
        ]
        for i,mutate in enumerate(mutations):
            with self.subTest(case=i):
                d,c,ref=aza_reference();mutate(ref)
                self.assertEqual(eligible(apply_corrections(d,c)),[])

    def test_subject_link_does_not_normalize_variant_address_characters(self):
        d,c,ref=aza_reference();f=d['facilities'][0]
        f['address']='架空市甲町沢1738-2'
        c['entries'][d['entries'][0]['id']]['original']['address']=f['address']
        ref['address_raw']='架空市甲町澤字岩内1738-2'
        ref['excerpt']='架空神社 かくうじんじゃ '+ref['address_raw']
        self.assertEqual(eligible(apply_corrections(d,c)),[])

    def test_subject_link_does_not_authorize_other_address_changes(self):
        for address in ['架空市甲町字岩内1738-20','架空市甲町字岩内1738',
                        '架空市乙町字岩内1738-2','別市甲町字岩内1738-2',
                        '架空市甲字岩内1738-2','別県架空市甲町字岩内1738-2','']:
            with self.subTest(address=address):
                d,c,ref=aza_reference();ref['address_raw']=address
                ref['excerpt']='架空神社 かくうじんじゃ '+address
                self.assertEqual(eligible(apply_corrections(d,c)),[])

    def test_subject_link_does_not_clear_identity_or_source_conflicts(self):
        for hold in ['source_conflicts','identity_review_required','mixed_reason']:
            with self.subTest(hold=hold):
                d,c,ref=aza_reference()
                if hold=='source_conflicts':d['facilities'][0][hold]=[{'name_raw':'別神社'}]
                elif hold=='identity_review_required':d['entries'][0][hold]=True
                else:d['facilities'][0]['review_reason']='annotated official name requires review; wrong printed code'
                self.assertEqual(eligible(apply_corrections(d,c)),[])

class CorrectionTest(unittest.TestCase):
    def test_exact_annotation_only_hold_accepts_bound_name_and_reading_correction(self):
        for raw,changes in [('カクウジンジャ',{'surface':'架空神社'}),('',{'surface':'架空神社','reading':'かくうじんじゃ'})]:
            with self.subTest(raw=raw):
                d=build([row(name='架空神社(原文注記)',reading_raw=raw,review_reason='annotated official name requires review')]);before=copy.deepcopy(d)
                out=apply_corrections(d,correction(d,changes))
                self.assertEqual(len(eligible(out)),1)
                self.assertEqual(validate(out),[])
                self.assertEqual(out['facilities'][0]['status'],'verified')
                self.assertEqual(out['entries'][0]['surface'],'架空神社')
                self.assertEqual(out['entries'][0]['reading'],'かくうじんじゃ')
                self.assertEqual(out['facilities'][0]['name_raw'],'架空神社(原文注記)')
                self.assertEqual(out['entries'][0]['reading_raw'],raw)
                self.assertEqual(out['facilities'][0]['source_hash'],before['facilities'][0]['source_hash'])
                self.assertEqual(d,before)
    def test_annotation_surface_only_never_supplies_unknown_reading(self):
        for raw in ['', '不明']:
            d=build([row(name='架空神社(原文注記)',reading_raw=raw,review_reason='annotated official name requires review')])
            out=apply_corrections(d,correction(d,{'surface':'架空神社'}))
            self.assertEqual(out['facilities'][0]['status'],'verified')
            self.assertEqual(out['entries'][0]['status'],'pending')
            self.assertEqual(out['entries'][0]['reading'],'')
            self.assertEqual(eligible(out),[])
    def test_mixed_annotation_and_identity_reasons_are_not_name_only(self):
        annotation='annotated official name requires review'
        for reason,review in [(annotation,annotation+'; printed profile code differs'),(annotation+'; map/profile addresses differ',annotation),('printed profile code differs',annotation),(annotation,'map/profile addresses differ')]:
            with self.subTest(reason=reason,review=review):
                d=build([row(name='架空神社(原文注記)',review_reason=review)])
                d['facilities'][0]['reason']=reason
                out=apply_corrections(d,correction(d,{'surface':'架空神社','reading':'かくうじんじゃ'}))
                self.assertEqual(out['facilities'][0]['status'],'pending')
                self.assertEqual(eligible(out),[])
    def test_annotation_reference_cannot_clear_source_conflict_or_identity_review(self):
        for kind in ['source_conflicts','identity_review_required']:
            d=build([row(name='架空神社(原文注記)',review_reason='annotated official name requires review')])
            if kind=='source_conflicts':d['facilities'][0][kind]=[{'name_raw':'別神社'}]
            else:d['entries'][0][kind]=True
            out=apply_corrections(d,correction(d,{'surface':'架空神社','reading':'かくうじんじゃ'}))
            self.assertEqual(out['facilities'][0]['status'],'pending')
            self.assertEqual(eligible(out),[])
    def test_annotation_name_reference_still_requires_same_nonblank_address(self):
        for address in ['', '架空市乙町1']:
            d=build([row(name='架空神社(原文注記)',address=address,review_reason='annotated official name requires review')])
            c=correction(d,{'surface':'架空神社','reading':'かくうじんじゃ'})
            ref=c['entries'][d['entries'][0]['id']]['references'][0]
            ref.update(address_raw='架空市乙町99',excerpt='架空神社（かくうじんじゃ） 架空市乙町99')
            self.assertEqual(eligible(apply_corrections(d,c)),[])

    def test_annotation_surface_only_does_not_fill_suppressed_reading(self):
        d=build([row(name='架空神社(原文注記)',review_reason='annotated official name requires review')])
        d['entries'][0]['reading']=''
        name_only=apply_corrections(d,correction(d,{'surface':'架空神社'}))
        self.assertEqual(name_only['entries'][0]['status'],'pending')
        self.assertEqual(name_only['entries'][0]['reading'],'')
        full=apply_corrections(d,correction(d,{'surface':'架空神社','reading':'かくうじんじゃ'}))
        self.assertEqual(len(eligible(full)),1)
    def test_existing_regional_name_only_correction_still_resolves(self):
        d=build([row(name='旧架空神社',review_reason='regional agency name differs from linked detail name')])
        out=apply_corrections(d,correction(d,{'surface':'架空神社','reading':'かくうじんじゃ'}))
        self.assertEqual(len(eligible(out)),1)
        self.assertEqual(out['facilities'][0]['name_raw'],'旧架空神社')

    def test_numeric_address_notation_preserves_all_parcel_components(self):
        for acquired,reference in [
            ('架空市甲町1丁目27番10号','埼玉県架空市甲町1−27−10'),
            ('架空市甲町3丁目19番地の3','埼玉県架空市甲町3丁目19-3'),
            ('架空市甲町4丁目1－43','埼玉県架空市甲町4-1-43')]:
            d=build([row(address=acquired,reading_raw='')]);c=correction(d,{'reading':'かくうじんじゃ'})
            ref=c['entries'][d['entries'][0]['id']]['references'][0]
            ref.update(address_raw=reference,excerpt='架空神社 かくうじんじゃ '+reference)
            out=apply_corrections(d,c)
            self.assertEqual(len(eligible(out)),1)
            self.assertEqual(out['facilities'][0]['address'],acquired)
            ref.update(address_raw=reference+'0',excerpt='架空神社 かくうじんじゃ '+reference+'0')
            self.assertEqual(eligible(apply_corrections(d,c)),[])

    def test_discovery_directory_is_not_accepted_as_dictionary_evidence(self):
        for host in ('jinja-net.jp','www.jinja-net.jp','jinja-net.jp.','www.jinja-net.jp.'):
            d=build([row(reading_raw='')]);c=correction(d,{'reading':'かくうじんじゃ'})
            c['entries'][d['entries'][0]['id']]['references'][0]['url']='https://'+host+'/jinja-all/example'
            self.assertEqual(eligible(apply_corrections(d,c)),[])
        d=build([row(url='https://jinja-net.jp/jinja-all/example')])
        self.assertEqual(eligible(d),[])

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

    def test_county_elision_cannot_hide_added_town_inside_a_city(self):
        d=build([row(address='架空市郡浜',reading_raw='不明')])
        c=correction(d,{'reading':'かくうじんじゃ'})
        ref=c['entries'][d['entries'][0]['id']]['references'][0]
        ref.update(address_raw='架空市海辺町郡浜2666',
                   excerpt='架空神社 かくうじんじゃ 架空市海辺町郡浜2666')
        self.assertEqual(eligible(apply_corrections(d,c)),[])

    def test_county_character_in_place_name_cannot_hide_a_different_city(self):
        for municipality in (None,'甲市'):
            with self.subTest(municipality=municipality):
                fields={} if municipality is None else {'municipality':municipality}
                d=build([row(address='甲市郡浜町1',reading_raw='不明',**fields)])
                c=correction(d,{'reading':'かくうじんじゃ'})
                ref=c['entries'][d['entries'][0]['id']]['references'][0]
                ref.update(address_raw='乙市郡浜町1',
                           excerpt='架空神社 かくうじんじゃ 乙市郡浜町1')
                self.assertEqual(eligible(apply_corrections(d,c)),[])

    def test_explicit_different_counties_are_not_interchangeable(self):
        d=build([row(address='架空郡架空町乙1',reading_raw='不明')])
        c=correction(d,{'reading':'かくうじんじゃ'})
        ref=c['entries'][d['entries'][0]['id']]['references'][0]
        ref.update(address_raw='別郡架空町乙1',
                   excerpt='架空神社 かくうじんじゃ 別郡架空町乙1')
        self.assertEqual(eligible(apply_corrections(d,c)),[])

    def test_county_character_in_place_name_cannot_hide_missing_city(self):
        d=build([row(address='甲市郡浜町1',reading_raw='不明')])
        c=correction(d,{'reading':'かくうじんじゃ'})
        ref=c['entries'][d['entries'][0]['id']]['references'][0]
        ref.update(address_raw='浜町1',excerpt='架空神社 かくうじんじゃ 浜町1')
        self.assertEqual(eligible(apply_corrections(d,c)),[])

    def test_county_omission_keeps_county_names_containing_city_character(self):
        for bare,full in [('高取町乙1','高市郡高取町乙1'),
                          ('仁木町乙1','余市郡仁木町乙1')]:
            for original,reference in [(bare,full),(full,bare)]:
                with self.subTest(original=original,reference=reference):
                    d=build([row(address=original,reading_raw='不明')])
                    c=correction(d,{'reading':'かくうじんじゃ'})
                    ref=c['entries'][d['entries'][0]['id']]['references'][0]
                    ref.update(address_raw=reference,
                               excerpt='架空神社 かくうじんじゃ '+reference)
                    self.assertEqual(len(eligible(apply_corrections(d,c))),1)

    def test_explicit_parcel_addition_within_same_whole_locality_is_preserved(self):
        d=build([row(address='架空市乙町',reading_raw='不明')])
        c=correction(d,{'reading':'かくうじんじゃ'})
        ref=c['entries'][d['entries'][0]['id']]['references'][0]
        ref.update(address_raw='架空市乙町123',
                   excerpt='架空神社 かくうじんじゃ 架空市乙町123')
        self.assertEqual(len(eligible(apply_corrections(d,c))),1)

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
