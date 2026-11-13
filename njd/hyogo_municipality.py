"""An inspected registered cityName supplements only a missing derived field."""
from datetime import datetime
import hashlib
import re
from njd.locations import _plain,_url,_hash,_raw_field,raw_address,_SNAPSHOT_FIELDS
from njd.records import municipality_from_address
from njd.normalize import normalize_reading
from njd.hyogo_profile_review import _numeric_address
from njd.hyogo_registry_window import registry_window_problems
from njd.adapters.hyogo import _reading_reason

KIND='hyogo_registered_municipality'


def municipality_problems(supplement,facility):
    address=raw_address(facility);name=facility.get('name_raw');code=facility.get('native_source_id')
    changes=supplement.get('changes')
    if (not isinstance(changes,dict) or set(changes)!={'municipality'}
        or changes['municipality']!='神崎郡神河町'):
        return ['municipality supplement only selects the inspected registered cityName']
    if (facility.get('source_key')!='hyogo' or facility.get('prefecture_code')!='28' or facility.get('prefecture')!='兵庫県'
        or not isinstance(code,str) or not re.fullmatch('[0-9]{7}',code)
        or not _plain(name) or facility.get('listed_name')!=name
        or facility.get('name_rendering_status') in ('external_glyph','unrenderable')
        or not _plain(address) or _raw_field(facility,'municipality')!=''
        or municipality_from_address(address,'兵庫県')!=''
        or facility.get('address')!=address
        or facility.get('municipality') not in ('',changes['municipality'])
        or facility.get('listing_url')!='https://www.hyogo-jinjacho.com/data/'+code+'.html'):
        return ['municipality selection requires unchanged Hyogo identity and only a missing derived city']
    snapshot={k:facility.get(k) for k in _SNAPSHOT_FIELDS};snapshot.update(address=address,municipality='')
    if (supplement.get('original')!=snapshot or supplement.get('facility_id')!=facility.get('id')
        or not _hash(supplement.get('expected_source_hash'))
        or supplement['expected_source_hash']!=facility.get('source_hash') or not _plain(supplement.get('reason'))):
        return ['municipality selection is stale or differs from the original snapshot']
    keys=('reference','map_reference','registry_reference','municipality_reference')
    if any(not isinstance(supplement.get(k),dict) for k in keys):return ['municipality selection lacks inspected references']
    profile,mapped,reg,town=[supplement[k] for k in keys]
    try:
        approved=datetime.fromisoformat(supplement.get('recorded_at',''))
        if approved.tzinfo is None:raise ValueError()
        for ref in (profile,mapped,reg,town):
            if not _url(ref.get('url')) or not _hash(ref.get('page_hash')) or any(not isinstance(ref.get(k),str) or not ref[k] for k in ('title','locator','excerpt','source_kind')):
                return ['incomplete municipality reference provenance']
            fetched=datetime.fromisoformat(ref.get('fetched_at',''));checked=datetime.fromisoformat(ref.get('checked_at',''))
            if fetched.tzinfo is None or checked.tzinfo is None or not fetched<=checked<=approved:raise ValueError()
    except (TypeError,ValueError):return ['invalid municipality evidence/approval chronology']
    kana=profile.get('reading_raw');raw=facility.get('address_raw');printed=profile.get('printed_code_raw')
    if (not isinstance(kana,str) or _reading_reason(name,kana) or profile.get('reading_scope')!='full_name'
        or not isinstance(raw,str) or not re.fullmatch(r'〒[0-9]{3}-[0-9]{4}\r?\n'+re.escape(address),raw)
        or not isinstance(printed,str) or not re.fullmatch(code+r'/(?:本務|兼務)',printed)
        or profile.get('source_kind')!='agency' or profile.get('url')!=facility['listing_url']
        or profile.get('name_raw')!=name or profile.get('address_raw')!=raw
        or profile.get('page_hash')!=facility.get('page_hash') or profile.get('locator')!=facility.get('source_locator')
        or hashlib.sha256('\0'.join((name,kana,address)).encode()).hexdigest()!=facility.get('source_hash')
        or not all(v in profile['excerpt'] for v in (name,kana,raw,printed))):
        return ['municipality evidence differs from original typed profile fields']
    occurrences=facility.get('xml_occurrences')
    if (not isinstance(occurrences,list) or len(occurrences)!=1 or not isinstance(occurrences[0],dict)
        or any(mapped.get(k)!=occurrences[0].get(k) for k in ('url','page_hash','locator','code_raw','name_raw','address_raw','protocol_url','href_derivation'))
        or mapped.get('source_kind')!='agency' or mapped.get('code_raw')!=code or mapped.get('name_raw')!=name
        or mapped.get('address_raw')!=address or facility.get('map_address_raw')!=address
        or not mapped.get('url','').startswith('https://www.hyogo-jinjacho.com/data/xml.php?')
        or mapped.get('protocol_url')!='https://www.hyogo-jinjacho.com/js/formsearch.js'
        or mapped.get('href_derivation')!='data/ + actual Locate code + .html'
        or not all(v in mapped['excerpt'] for v in (code,name,address))):
        return ['municipality selection requires the same single original map name/code/full address']
    if (town.get('source_kind')!='government_municipality' or town.get('publisher')!='神河町'
        or town.get('municipality_raw')!='神崎郡神河町'
        or town.get('url') not in ('https://www.town.kamikawa.hyogo.jp/0000000707.html','https://www.town.kamikawa.hyogo.jp/0000003593.html')
        or '神河町役場' not in town['excerpt'] or '兵庫県神崎郡神河町' not in town['excerpt']):
        return ['municipality lacks inspected full administrative-name evidence']
    issues=registry_window_problems(reg)
    if issues:return issues
    fields=reg.get('source_fields');state=reg['registry_state_proof']
    required=('corporateNumber','name','prefectureCode','prefectureName','cityName','streetNumber','postCode','kind','latest','process','closeDate','hihyoji','nameImageId','addressImageId','furigana')
    if not isinstance(fields,dict) or any(not isinstance(fields.get(k),str) for k in required):
        return ['invalid municipality independent registry fields']
    corporate=fields['corporateNumber'];full=fields['prefectureName']+fields['cityName']+fields['streetNumber']
    prefix=fields['cityName'].removesuffix('町')
    street=address[len(prefix):] if address.startswith(prefix) else ''
    if (reg.get('source_kind')!='government_corporate_register'
        or reg.get('url')!='https://www.houjin-bangou.nta.go.jp/download/zenken/index.html'
        or not re.fullmatch('[0-9]{13}',corporate) or reg.get('corporate_number')!=corporate
        or type(reg.get('csv_row')) is not int or reg['csv_row']<1
        or fields['name']!=name or reg.get('name_raw')!=name or reg.get('address_raw')!=full
        or fields['prefectureCode']!='28' or fields['prefectureName']!='兵庫県' or fields['cityName']!=changes['municipality']
        or not re.fullmatch('[0-9]{7}',fields['postCode']) or fields['postCode']!=raw[1:9].replace('-','')
        or not _plain(street) or not re.fullmatch(r'.+?[^0-9-][0-9]+(?:-[0-9]+)*',_numeric_address(street))
        or _numeric_address(street)!=_numeric_address(fields['streetNumber'])
        or not all(v in reg['excerpt'] for v in (name,full,fields['postCode']))
        or fields['kind']!='399' or fields['latest']!='1' or fields['process']=='99' or fields['closeDate']
        or fields['hihyoji']!='0' or fields['nameImageId'] or fields['addressImageId']
        or type(state.get('active_shrine_corporation_count_at_full_address')) is not int
        or state['active_shrine_corporation_count_at_full_address']!=1
        or state.get('active_corporate_numbers_at_full_address')!=[corporate]):
        return ['municipality lacks unique active same-name registry/full street/parcel/postcode support']
    if fields['furigana']:
        try:
            if normalize_reading(fields['furigana'])!=normalize_reading(kana):raise ValueError()
        except ValueError:return ['registered full-name kana conflicts with acquired profile']
    return []
