"""An addressless profile bound to an inspected municipal land-asset row.

The asset row corroborates a location, not shrine ownership or a pronunciation.
"""
from datetime import datetime
import hashlib,re
from njd.locations import _plain,_url,_hash,_raw_field,_SNAPSHOT_FIELDS
from njd.adapters.hyogo import _reading_reason,_url as agency_url,PROTOCOL_URL
from njd.hyogo_profile_review import _numeric_address
from njd.hyogo_registry_window import registry_window_problems,observed_between
# Both proofs require exactly the same unchanged addressless-profile registration.
from njd.hyogo_building_location import building_entry_problems as asset_entry_problems,REASON

KIND='hyogo_municipal_asset_location'
ASSET_URL='https://www.city.awaji.lg.jp/uploaded/attachment/44772.pdf'
ASSET_HASH='b3da6b887e1e8196d82083e9b2e069fcf24f70394658809b7b76f86669077422'
LISTING_URL='https://www.city.awaji.lg.jp/soshiki/zaisei/23476.html'

def asset_location_problems(s,f,source=None):
    if not isinstance(s,dict) or s.get('status')!='verified' or (source or {}).get('authority_status') in ('pending','unconfirmed'):
        return ['municipal asset location needs verified evidence and confirmed agency authority']
    name=f.get('name_raw');code=f.get('native_source_id');changes=s.get('changes');prior=f.get('location_supplement');applied=isinstance(prior,dict) and prior.get('applied') is True
    if not isinstance(changes,dict) or set(changes)!={'address','municipality'} or changes['municipality']!='淡路市' or not _plain(changes['address']):return ['municipal asset location requires an explicit Awaji location']
    if (f.get('source_key')!='hyogo' or f.get('prefecture_code')!='28' or f.get('prefecture')!='兵庫県'
        or not _plain(name) or f.get('listed_name')!=name or not isinstance(code,str) or not re.fullmatch('[0-9]{7}',code)
        or f.get('listing_url')!='https://www.hyogo-jinjacho.com/data/'+code+'.html'
        or f.get('review_reason')!=REASON or f.get('identity_review_required') or f.get('source_conflicts')
        or f.get('name_rendering_status') in ('external_glyph','unrenderable')
        or not ((f.get('status')=='pending' and f.get('reason')==REASON) or (applied and f.get('status')=='verified' and not f.get('reason')))
        or _raw_field(f,'address')!='' or _raw_field(f,'municipality')!='' or f.get('map_address_raw')!=''
        or f.get('address') not in ('',changes['address']) or f.get('municipality') not in ('','淡路市')):
        return ['municipal asset location cannot override another original condition']
    raw=f.get('address_raw');original={k:f.get(k) for k in _SNAPSHOT_FIELDS};original.update(address='',municipality='')
    if (not isinstance(raw,str) or not re.fullmatch(r'〒[0-9]{3}-[0-9]{4}',raw)
        or s.get('original')!=original or s.get('facility_id')!=f.get('id') or not _plain(s.get('entry_id'))
        or not _hash(s.get('expected_source_hash')) or s['expected_source_hash']!=f.get('source_hash') or not _plain(s.get('reason'))):return ['municipal asset location differs from the original postal-only identity']
    refs=[s.get(k) for k in ('reference','map_reference','municipal_reference','registry_reference')]
    if any(not isinstance(r,dict) for r in refs):return ['municipal asset location lacks four inspected references']
    profile,mapped,town,reg=refs
    try:
        approved=datetime.fromisoformat(s.get('recorded_at',''))
        if approved.tzinfo is None:raise ValueError()
        for ref in refs:
            if (not _url(ref.get('url')) or not _hash(ref.get('page_hash'))
                or any(not isinstance(ref.get(k),str) or not ref[k] for k in ('title','locator','excerpt','source_kind'))):return ['incomplete municipal asset provenance']
            fetched=datetime.fromisoformat(ref.get('fetched_at',''));checked=datetime.fromisoformat(ref.get('checked_at',''))
            if fetched.tzinfo is None or checked.tzinfo is None or not fetched<=checked<=approved:raise ValueError()
    except (TypeError,ValueError):return ['invalid municipal asset evidence chronology']
    kana=profile.get('reading_raw');printed=profile.get('printed_code_raw');locality=profile.get('locality_raw');context=profile.get('locality_context_raw')
    if (profile.get('source_kind')!='agency' or profile.get('url')!=f['listing_url'] or profile.get('page_hash')!=f.get('page_hash')
        or profile.get('locator')!=f.get('source_locator') or profile.get('name_raw')!=name or profile.get('address_raw')!=raw
        or not isinstance(kana,str) or _reading_reason(name,kana) or profile.get('reading_scope')!='full_name'
        or not isinstance(printed,str) or not re.fullmatch(code+r'/(?:本務|兼務)',printed)
        or hashlib.sha256((name+'\0'+kana+'\0').encode()).hexdigest()!=f.get('source_hash')
        or not _plain(locality) or not re.fullmatch(r'[\u3400-\u9fff々ヶ]+',locality)
        or context!='古来'+locality+'の明神として崇敬された。'
        or not all(v in profile['excerpt'] for v in (name,kana,raw,printed,context))):return ['municipal asset location lacks the unchanged typed profile and explicit subject locality']
    occurrences=f.get('xml_occurrences')
    if (not isinstance(occurrences,list) or len(occurrences)!=1 or not isinstance(occurrences[0],dict)
        or any(mapped.get(k)!=occurrences[0].get(k) for k in ('url','page_hash','locator','code_raw','name_raw','address_raw','protocol_url','href_derivation'))
        or mapped.get('source_kind')!='agency' or mapped.get('name_raw')!=name or mapped.get('code_raw')!=code or mapped.get('address_raw')!=''
        or mapped.get('protocol_url')!=PROTOCOL_URL or mapped.get('href_derivation')!='data/ + actual Locate code + .html'
        or not all(v in mapped['excerpt'] for v in (name,code))):return ['municipal asset location lacks one unchanged same-name map code']
    try:
        if agency_url(mapped['url'])!=mapped['url'] or '/data/xml.php?' not in mapped['url']:raise ValueError()
    except (KeyError,ValueError,TypeError):return ['invalid municipal asset map endpoint']
    protocol=mapped.get('protocol_reference')
    if (not isinstance(protocol,dict) or protocol.get('url')!=PROTOCOL_URL or protocol.get('page_hash')!='e124e51e28043bc10f5a9dec59c71e9c30c0c57851dda691e567f8c7376537f9'
        or protocol.get('profile_path_template')!='data/{code}.html' or not _plain(protocol.get('locator'))
        or not observed_between(protocol.get('fetched_at'),'20261113',protocol.get('checked_at'))
        or datetime.fromisoformat(protocol['checked_at'])>approved):return ['municipal asset location lacks inspected map-to-profile protocol evidence']
    parcel=town.get('parcel_raw');link=town.get('published_link_proof')
    if (town.get('source_kind')!='government_municipal_asset_register' or town.get('url')!=ASSET_URL or town.get('page_hash')!=ASSET_HASH
        or town.get('publisher')!='淡路市' or town.get('municipality_raw')!='淡路市' or type(town.get('pdf_page_1based')) is not int or town['pdf_page_1based']!=3
        or town.get('asset_class_raw')!='事業用土地' or town.get('name_raw')!=name
        or not isinstance(parcel,str) or not re.fullmatch(re.escape(locality)+r'[0-9]+(?:-[0-9]+)*',parcel)
        or town.get('source_fields')!={'所在地':parcel,'資産名称':name} or changes['address']!='淡路市'+parcel
        or not all(v in town['excerpt'] for v in ('事業用土地','所在地：'+parcel,'資産名称：'+name))
        or not isinstance(link,dict) or link.get('source_url')!=LISTING_URL or not _hash(link.get('source_page_hash'))
        or link.get('url')!=ASSET_URL or link.get('href_raw')!='/uploaded/attachment/44772.pdf'
        or not isinstance(link.get('label_raw'),str) or 'R6_固定資産台帳' not in link['label_raw']
        or not observed_between(link.get('fetched_at'),'20261113',town.get('checked_at'))):return ['municipal asset row, full parcel or published link is not explicitly bound']
    issues=registry_window_problems(reg)
    if issues:return issues
    fields=reg.get('source_fields');state=reg.get('registry_state_proof');required=('corporateNumber','name','prefectureCode','prefectureName','cityName','streetNumber','postCode','kind','latest','process','closeDate','hihyoji','nameImageId','addressImageId','furigana')
    if not isinstance(fields,dict) or any(not isinstance(fields.get(k),str) for k in required) or not isinstance(state,dict):return ['invalid municipal asset independent registry fields']
    corp=fields['corporateNumber'];full=fields['prefectureName']+fields['cityName']+fields['streetNumber']
    if (reg.get('source_kind')!='government_corporate_register' or reg.get('url')!='https://www.houjin-bangou.nta.go.jp/download/zenken/index.html'
        or not re.fullmatch('[0-9]{13}',corp) or reg.get('corporate_number')!=corp or type(reg.get('csv_row')) is not int or reg['csv_row']<1
        or fields['name']!=name or reg.get('name_raw')!=name or reg.get('address_raw')!=full
        or fields['prefectureCode']!='28' or fields['prefectureName']!='兵庫県' or fields['cityName']!='淡路市'
        or fields['postCode']!=raw[1:].replace('-','') or _numeric_address(fields['streetNumber'])!=_numeric_address(parcel)
        or fields['kind']!='399' or fields['latest']!='1' or fields['process']=='99' or fields['closeDate'] or fields['hihyoji']!='0' or fields['nameImageId'] or fields['addressImageId'] or fields['furigana']
        or not all(v in reg['excerpt'] for v in (name,full,fields['postCode']))
        or type(state.get('active_shrine_corporation_count_at_full_address')) is not int or state['active_shrine_corporation_count_at_full_address']!=1 or state.get('active_corporate_numbers_at_full_address')!=[corp]
        or type(state.get('active_same_name_postcode_count')) is not int or state['active_same_name_postcode_count']!=1 or state.get('active_same_name_postcode_corporate_numbers')!=[corp]):return ['municipal asset location lacks unique name/postcode/full-parcel independent support']
    return []
