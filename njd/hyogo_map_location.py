"""Select an independently registered location through an unchanged old-city map.

This does not repair a profile string. Both profile and map observations remain
immutable; the selected address comes from inspected independent register fields.
"""
from datetime import datetime
import hashlib,re
from njd.locations import _plain,_url,_hash,_raw_field,raw_address,_SNAPSHOT_FIELDS
from njd.adapters.hyogo import _reading_reason,_url as agency_url,PROTOCOL_URL,CITY_NAME_CHANGE
from njd.hyogo_profile_review import _numeric_address,LOCATION_REASON
from njd.hyogo_registry_window import registry_window_problems,observed_between
from njd.normalize import normalize_reading

KIND='hyogo_documented_map_location'
ORDINANCE_HASH='9ae4e9f544807232c87d1df1b1faa129328316dd6935aefaa74c4f9af876e6e2'

def map_location_problems(supplement,facility,source=None):
    if not isinstance(supplement,dict):return ['invalid documented map location']
    address=raw_address(facility);city=_raw_field(facility,'municipality');name=facility.get('name_raw');code=facility.get('native_source_id')
    prior=facility.get('location_supplement');reapplied=isinstance(prior,dict) and prior.get('applied') is True
    allowed=(facility.get('status')=='pending' and facility.get('reason')==LOCATION_REASON) or (reapplied and facility.get('status')=='verified' and not facility.get('reason'))
    if (supplement.get('status')!='verified' or not allowed or (source or {}).get('authority_status') in ('pending','unconfirmed')
        or facility.get('source_key')!='hyogo' or facility.get('prefecture_code')!='28' or facility.get('prefecture')!='兵庫県'
        or not isinstance(code,str) or not re.fullmatch('[0-9]{7}',code) or not _plain(name) or facility.get('listed_name')!=name
        or facility.get('listing_url')!='https://www.hyogo-jinjacho.com/data/'+code+'.html'
        or facility.get('review_reason')!=LOCATION_REASON or facility.get('identity_review_required') or facility.get('source_conflicts')
        or facility.get('name_rendering_status') in ('external_glyph','unrenderable')):
        return ['documented map location cannot override another agency condition']
    snapshot={k:facility.get(k) for k in _SNAPSHOT_FIELDS};snapshot.update(address=address,municipality=city)
    if (supplement.get('original')!=snapshot or supplement.get('facility_id')!=facility.get('id')
        or not _hash(supplement.get('expected_source_hash')) or supplement['expected_source_hash']!=facility.get('source_hash')
        or not _plain(supplement.get('reason'))):return ['documented map location differs from the original identity']
    keys=('reference','map_reference','registry_reference','municipality_reference')
    if any(not isinstance(supplement.get(k),dict) for k in keys):return ['missing inspected documented map location references']
    profile,mapped,reg,ordinance=[supplement[k] for k in keys]
    try:
        approved=datetime.fromisoformat(supplement.get('recorded_at',''))
        if approved.tzinfo is None:raise ValueError()
        for ref in (profile,mapped,reg,ordinance):
            if (not _url(ref.get('url')) or not _hash(ref.get('page_hash'))
                or any(not isinstance(ref.get(k),str) or not ref[k] for k in ('title','locator','excerpt','source_kind'))):return ['incomplete documented map location provenance']
            fetched=datetime.fromisoformat(ref.get('fetched_at',''));checked=datetime.fromisoformat(ref.get('checked_at',''))
            if fetched.tzinfo is None or checked.tzinfo is None or not fetched<=checked<=approved:raise ValueError()
    except (TypeError,ValueError):return ['invalid documented map location chronology']
    raw=facility.get('address_raw');kana=profile.get('reading_raw');printed=profile.get('printed_code_raw')
    if (not _plain(address) or not isinstance(raw,str) or not re.fullmatch(r'〒[0-9]{3}-[0-9]{4}\r?\n'+re.escape(address),raw)
        or profile.get('source_kind')!='agency' or profile.get('url')!=facility['listing_url']
        or profile.get('page_hash')!=facility.get('page_hash') or profile.get('locator')!=facility.get('source_locator')
        or profile.get('name_raw')!=name or profile.get('address_raw')!=raw or profile.get('reading_scope')!='full_name'
        or not isinstance(kana,str) or _reading_reason(name,kana)
        or not isinstance(printed,str) or not re.fullmatch(code+r'/(?:本務|兼務)',printed)
        or hashlib.sha256('\0'.join((name,kana,address)).encode()).hexdigest()!=facility.get('source_hash')
        or not all(v in profile['excerpt'] for v in (name,kana,raw,printed))):return ['documented map location profile is not the unchanged typed source']
    occurrences=facility.get('xml_occurrences')
    if not isinstance(occurrences,list) or len(occurrences)!=1 or not isinstance(occurrences[0],dict):return ['documented map location needs one original map observation']
    fields=('url','page_hash','locator','code_raw','name_raw','address_raw','protocol_url','href_derivation')
    if (any(mapped.get(k)!=occurrences[0].get(k) for k in fields) or mapped.get('source_kind')!='agency'
        or mapped.get('name_raw')!=name or mapped.get('code_raw')!=code or mapped.get('address_raw')!=facility.get('map_address_raw')
        or mapped.get('protocol_url')!=PROTOCOL_URL or mapped.get('href_derivation')!='data/ + actual Locate code + .html'):
        return ['documented map location is not bound to its original same-name code']
    try:
        if agency_url(mapped['url'])!=mapped['url'] or '/data/xml.php?' not in mapped['url']:raise ValueError()
    except (KeyError,ValueError,TypeError):return ['invalid documented map endpoint']
    old=CITY_NAME_CHANGE['old_prefix'];new=CITY_NAME_CHANGE['new_prefix'];ma=mapped.get('address_raw')
    suffix=ma[len(old):] if isinstance(ma,str) and ma.startswith(old) else ''
    if (not _plain(suffix) or not re.fullmatch(r'.+?[^0-9-][0-9]+(?:-[0-9]+)*',_numeric_address(suffix))
        or city!='丹波丹波篠山市' or address!=city+suffix
        or not all(v in mapped['excerpt'] for v in (code,name,ma))):return ['old-city map must retain the entire same original locality and parcel']
    if (ordinance.get('url')!=CITY_NAME_CHANGE['ordinance_reference']['url'] or ordinance.get('page_hash')!=ORDINANCE_HASH
        or ordinance.get('source_kind')!='government_municipality' or ordinance.get('publisher')!='丹波篠山市'
        or ordinance.get('former_prefix_raw')!=old or ordinance.get('current_prefix_raw')!=new
        or ordinance.get('effective_date')!='2019-05-01'
        or not all(s in ordinance['excerpt'] for s in ('篠山市の名称を丹波篠山市に変更する。','この条例は、平成31年5月1日から施行する。'))):return ['documented map location lacks the inspected city-name ordinance']
    protocol=mapped.get('protocol_reference')
    if (not isinstance(protocol,dict) or protocol.get('url')!=PROTOCOL_URL
        or protocol.get('page_hash')!='e124e51e28043bc10f5a9dec59c71e9c30c0c57851dda691e567f8c7376537f9'
        or protocol.get('profile_path_template')!='data/{code}.html' or not _plain(protocol.get('locator'))
        or not observed_between(protocol.get('fetched_at'),'20261113',protocol.get('checked_at'))
        or datetime.fromisoformat(protocol['checked_at'])>approved):return ['documented map location lacks public map-to-profile protocol evidence']
    issues=registry_window_problems(reg)
    if issues:return issues
    fields=reg.get('source_fields');state=reg.get('registry_state_proof')
    required=('corporateNumber','name','prefectureCode','prefectureName','cityName','streetNumber','postCode','kind','latest','process','closeDate','hihyoji','nameImageId','addressImageId','furigana')
    if not isinstance(fields,dict) or any(not isinstance(fields.get(k),str) for k in required) or not isinstance(state,dict):return ['invalid documented map independent registry fields']
    corporate=fields['corporateNumber'];full=fields['prefectureName']+fields['cityName']+fields['streetNumber'];changes=supplement.get('changes')
    if (reg.get('source_kind')!='government_corporate_register' or reg.get('url')!='https://www.houjin-bangou.nta.go.jp/download/zenken/index.html'
        or not re.fullmatch('[0-9]{13}',corporate) or reg.get('corporate_number')!=corporate
        or type(reg.get('csv_row')) is not int or reg['csv_row']<1 or reg.get('name_raw')!=name or fields['name']!=name
        or reg.get('address_raw')!=full or fields['prefectureCode']!='28' or fields['prefectureName']!='兵庫県' or fields['cityName']!=new
        or _numeric_address(fields['streetNumber'])!=_numeric_address(suffix) or fields['postCode']!=raw[1:9].replace('-','')
        or not all(v in reg['excerpt'] for v in (name,full,fields['postCode']))
        or fields['kind']!='399' or fields['latest']!='1' or fields['process']=='99' or fields['closeDate'] or fields['hihyoji']!='0' or fields['nameImageId'] or fields['addressImageId']
        or type(state.get('active_shrine_corporation_count_at_full_address')) is not int or state['active_shrine_corporation_count_at_full_address']!=1
        or state.get('active_corporate_numbers_at_full_address')!=[corporate]
        or type(state.get('active_same_name_postcode_count')) is not int or state['active_same_name_postcode_count']!=1
        or state.get('active_same_name_postcode_corporate_numbers')!=[corporate]
        or changes!=dict(address=full,municipality=new)):return ['documented map location lacks unique same-name full-parcel/postcode registry support']
    if fields['furigana']:
        try:
            if normalize_reading(fields['furigana'])!=normalize_reading(kana):raise ValueError()
        except ValueError:return ['registered kana conflicts with literal whole profile kana']
    return []

def map_entry_problems(supplement,facility,entry):
    p=supplement.get('reference') if isinstance(supplement,dict) else None
    if not isinstance(p,dict):return ['documented map entry lacks a typed profile reference']
    if (supplement.get('entry_id')!=entry.get('id') or entry.get('facility_id')!=facility.get('id')
        or entry.get('source_hash')!=supplement.get('expected_source_hash')
        or entry.get('name_raw')!=facility.get('name_raw') or entry.get('surface')!=facility.get('name_raw')
        or entry.get('reading_raw')!=p.get('reading_raw') or entry.get('reading_display_raw')!=p.get('reading_raw')
        or entry.get('printed_code_raw')!=p.get('printed_code_raw') or entry.get('reading_url')!=facility.get('listing_url')
        or entry.get('reading_source_kind')!='agency' or entry.get('page_hash')!=facility.get('page_hash')
        or entry.get('status') not in ('pending','verified') or entry.get('reason') not in ('',LOCATION_REASON)
        or entry.get('identity_review_required')):return ['documented map entry differs from its single original whole-reading registration']
    return []
