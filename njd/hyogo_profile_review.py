"""Evidence-bound profile selection, preserving original map discrepancies."""
from datetime import datetime
import re
from njd.hyogo_registry_window import registry_window_problems,observed_between
from njd.locations import _hash,_url,_plain
from njd.normalize import normalize_reading,compare_address_units
from njd.adapters.hyogo import _reading_reason,_url as _agency_url,PROTOCOL_URL

REASON='Hyogo map and profile official names differ or are missing'
LOCATION_REASON='Hyogo map and profile addresses differ'


def _numeric_address(value):
    value=compare_address_units(value.translate(str.maketrans('０１２３４５６７８９','0123456789')))
    value=re.sub(r'(?<=\d)丁目(?=\d)','-',value)
    value=re.sub(r'(?<=\d)番(?:地)?(?:の)?(?=\d)','-',value)
    return re.sub(r'(?<=\d)(?:番地|番|号)$','',value)


def hyogo_profile_problems(review,facility,entry):
    if review.get('review_kind') not in ('hyogo_profile_name_selection','hyogo_profile_location_selection'):
        return ['unsupported Hyogo profile selection kind']
    location_selected=review['review_kind']=='hyogo_profile_location_selection'
    selected_reason=LOCATION_REASON if location_selected else REASON
    proof=review.get('profile_selection_proof')
    if not isinstance(proof,dict):return ['missing Hyogo profile selection proof']
    code=facility.get('native_source_id');name=facility.get('name_raw');kana=entry.get('reading_raw')
    expected=dict(kind='hyogo_typed_profile_registered_location_selection' if location_selected else 'hyogo_typed_profile_registered_name_selection',facility_id=facility.get('id'),
        entry_id=entry.get('id'),expected_source_hash=entry.get('source_hash'),native_code=code,
        profile_name_raw=name,selection='profile_name_and_profile_kana_with_location_evidence' if location_selected else 'profile_name_and_profile_kana')
    if (any(proof.get(k)!=v for k,v in expected.items()) or not _hash(entry.get('source_hash'))
        or facility.get('source_hash')!=entry.get('source_hash') or review.get('confirmation')!='source_review'):
        return ['Hyogo profile proof differs from acquired identity']
    if (facility.get('source_key')!='hyogo' or facility.get('prefecture_code')!='28' or facility.get('prefecture')!='兵庫県'
        or not isinstance(code,str) or not re.fullmatch('[0-9]{7}',code)
        or facility.get('listing_url')!='https://www.hyogo-jinjacho.com/data/'+code+'.html'
        or facility.get('review_reason')!=selected_reason or facility.get('source_conflicts')
        or facility.get('identity_review_required') or facility.get('name_rendering_status') in ('external_glyph','unrenderable')
        or any(r.get('status') not in ('pending','verified') or r.get('reason') not in ('',selected_reason) for r in (facility,entry))):
        return ['Hyogo profile selection cannot override another condition']
    address=facility.get('address');raw=facility.get('address_raw');municipality=facility.get('municipality')
    if (not all(_plain(v) for v in (name,address,municipality)) or facility.get('listed_name')!=name
        or not address.startswith(municipality) or not re.search('[0-9０-９]+(?:-[0-9０-９]+)*$',address)
        or not isinstance(raw,str) or not re.fullmatch(r'〒[0-9]{3}-[0-9]{4}\r?\n'+re.escape(address),raw)
        or (not location_selected and facility.get('map_address_raw')!=address)):
        return ['Hyogo profile selection requires one unchanged complete address']
    try:
        reading=normalize_reading(kana)
        if _reading_reason(name,kana) or entry.get('reading_display_raw')!=kana:raise ValueError()
    except (ValueError,TypeError):return ['Hyogo profile lacks literal whole-name kana']
    outputs=review.get('outputs')
    if (review.get('split') or not isinstance(outputs,list) or len(outputs)!=1 or not isinstance(outputs[0],dict)
        or any(outputs[0].get(k)!=v for k,v in dict(surface=name,reading=reading,
            reading_url=facility['listing_url'],basis='agency_selected').items())):
        return ['Hyogo selection only outputs the unchanged profile name and kana']
    refs=review.get('references')
    if not isinstance(refs,list) or len(refs)!=3 or any(not isinstance(r,dict) for r in refs):
        return ['Hyogo selection requires three inspected references']
    if any(not isinstance(r.get('evidence_role'),str) for r in refs):return ['invalid Hyogo source roles']
    roles={r['evidence_role']:r for r in refs}
    if set(roles)!={'agency_profile','agency_map','registered_profile_identity'}:return ['missing or duplicate Hyogo source roles']
    try:
        approved=datetime.fromisoformat(review.get('recorded_at',''))
        if approved.tzinfo is None:raise ValueError()
    except (TypeError,ValueError):return ['incomplete Hyogo approval date']
    for ref in refs:
        if (not _hash(ref.get('page_hash')) or not _url(ref.get('url'))
            or any(not isinstance(ref.get(k),str) or not ref[k] for k in ('locator','title','excerpt','name_raw','source_kind'))):
            return ['incomplete Hyogo reference provenance']
        for k in ('checked_at','fetched_at'):
            try:
                if datetime.fromisoformat(ref.get(k,'')).tzinfo is None:raise ValueError()
            except (TypeError,ValueError):return ['incomplete Hyogo reference date']
        if not datetime.fromisoformat(ref['fetched_at'])<=datetime.fromisoformat(ref['checked_at'])<=approved:
            return ['Hyogo reference acquisition/inspection follows its approval']
    profile=roles['agency_profile'];mapped=roles['agency_map'];reg=roles['registered_profile_identity']
    printed=entry.get('printed_code_raw')
    if (not isinstance(printed,str) or not re.fullmatch(code+r'/(?:本務|兼務)',printed)
        or profile.get('source_kind')!='agency' or profile.get('url')!=facility['listing_url']
        or profile.get('page_hash')!=facility.get('page_hash') or profile.get('locator')!=facility.get('source_locator')
        or profile.get('name_raw')!=name or profile.get('reading_raw')!=kana or profile.get('reading_scope')!='full_name'
        or profile.get('address_raw')!=raw or profile.get('printed_code_raw')!=printed
        or not all(v in profile['excerpt'] for v in (name,kana,raw,printed))):
        return ['Hyogo profile fields differ from the acquired typed caption']
    occurrences=facility.get('xml_occurrences')
    if not isinstance(occurrences,list) or len(occurrences)!=1 or not isinstance(occurrences[0],dict):
        return ['Hyogo selection requires one unambiguous original map observation']
    original=occurrences[0]
    keys=('url','page_hash','locator','code_raw','name_raw','address_raw','protocol_url','href_derivation')
    if any(mapped.get(k)!=original.get(k) for k in keys):return ['Hyogo map evidence differs from original observation']
    try:
        if _agency_url(mapped['url'])!=mapped['url'] or '/data/xml.php?' not in mapped['url']:raise ValueError()
    except (TypeError,ValueError):return ['invalid original Hyogo map endpoint']
    map_address=facility.get('map_address_raw')
    if (mapped.get('source_kind')!='agency' or mapped.get('code_raw')!=code or mapped.get('address_raw')!=map_address
        or not _plain(map_address) or not re.search('[0-9０-９]+(?:-[0-9０-９]+)*$',map_address)
        or mapped.get('protocol_url')!=PROTOCOL_URL or mapped.get('href_derivation')!='data/ + actual Locate code + .html'
        or not _plain(mapped.get('name_raw')) or (mapped['name_raw']!=name if location_selected else mapped['name_raw']==name)
        or proof.get('map_name_raw')!=mapped['name_raw']
        or not all(v in mapped['excerpt'] for v in (mapped['name_raw'],code,map_address))):
        return ['Hyogo map code, full address or retained name is not bound']
    supported_address=address
    if location_selected:
        if (proof.get('profile_address_raw')!=address or proof.get('map_address_raw')!=map_address or map_address==address):
            return ['Hyogo location proof differs from the two original address fields']
        basis=proof.get('registered_address_basis')
        if basis=='profile':
            if proof.get('added_aza_raw'):return ['profile address selection cannot claim added aza']
        elif basis=='linked_map_additional_aza':
            extra=proof.get('added_aza_raw')
            parcel=re.fullmatch(r'(.+?[^0-9-])([0-9]+(?:-[0-9]+)*)',_numeric_address(address))
            if (not isinstance(extra,str) or not re.fullmatch(r'(?:小字|字)[\u3400-\u9fff々〆ヶぁ-ゖァ-ヺー]+',extra)
                or not parcel or _numeric_address(map_address)!=parcel[1]+extra+parcel[2]):
                return ['Hyogo linked map is not one explicit aza before the whole original parcel']
            supported_address=map_address
        else:return ['unsupported Hyogo registered address basis']
    elif proof.get('registered_address_basis') not in (None,'profile'):
        return ['name selection requires the unchanged profile address']
    protocol=mapped.get('protocol_reference')
    if (not isinstance(protocol,dict) or protocol.get('url')!=PROTOCOL_URL
        or protocol.get('page_hash')!='e124e51e28043bc10f5a9dec59c71e9c30c0c57851dda691e567f8c7376537f9'
        or not _plain(protocol.get('locator')) or protocol.get('profile_path_template')!='data/{code}.html'
        or not observed_between(protocol.get('fetched_at'),'20261113',protocol.get('checked_at'))
        or datetime.fromisoformat(protocol['checked_at'])>approved):
        return ['missing inspected Hyogo map-to-profile protocol provenance']
    window_problems=registry_window_problems(reg)
    if window_problems:return window_problems
    fields=reg.get('source_fields');state=reg.get('registry_state_proof')
    keys=('corporateNumber','name','prefectureCode','prefectureName','cityName','streetNumber','kind','latest',
        'process','closeDate','hihyoji','nameImageId','addressImageId','furigana')
    if not isinstance(fields,dict) or any(not isinstance(fields.get(k),str) for k in keys) or not isinstance(state,dict):
        return ['invalid Hyogo independent registry fields/state']
    try:
        if any(not isinstance(v,str) or not re.fullmatch('[0-9]{8}',v) for v in (reg.get('snapshot'),state.get('as_of'))):raise ValueError()
        if datetime.strptime(state['as_of'],'%Y%m%d')<datetime.strptime(reg['snapshot'],'%Y%m%d'):raise ValueError()
    except (TypeError,ValueError):return ['invalid Hyogo registry snapshot/state date']
    corporate=fields['corporateNumber'];full=fields['prefectureName']+fields['cityName']+fields['streetNumber']
    if (reg.get('source_kind')!='government_corporate_register'
        or reg.get('url')!='https://www.houjin-bangou.nta.go.jp/download/zenken/index.html'
        or not re.fullmatch('[0-9]{13}',corporate) or reg.get('corporate_number')!=corporate
        or type(reg.get('csv_row')) is not int or reg['csv_row']<1 or reg.get('name_raw')!=name or fields['name']!=name
        or fields['prefectureCode']!='28' or fields['prefectureName']!='兵庫県' or reg.get('address_raw')!=full
        or _numeric_address(full)!=_numeric_address('兵庫県'+supported_address.removeprefix('兵庫県'))
        or not all(v in reg['excerpt'] for v in (name,full))
        or fields['kind']!='399' or fields['latest']!='1' or fields['process']=='99'
        or fields['closeDate'] or fields['hihyoji']!='0' or fields['nameImageId'] or fields['addressImageId']
        or type(state.get('active_shrine_corporation_count_at_full_address')) is not int or state['active_shrine_corporation_count_at_full_address']!=1
        or state.get('active_corporate_numbers_at_full_address')!=[corporate]):
        return ['Hyogo profile lacks unique active exact registered name/full-address support']
    if fields['furigana']:
        try:
            if (normalize_reading(fields['furigana'])!=reading or reg.get('reading_raw')!=fields['furigana']
                or reg.get('reading_scope')!='full_name' or fields['furigana'] not in reg['excerpt']):raise ValueError()
        except ValueError:return ['Hyogo registered kana differs from whole profile kana']
    return []
