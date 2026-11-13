"""Individually inspected Sumoto building evidence for an addressless profile.

Municipal address is the derived location. Registry adds identity support only;
its additional aza and its kana are never used to compose address or reading.
"""
from datetime import datetime
import hashlib
import re
from njd.locations import _plain,_url,_hash,_raw_field,_SNAPSHOT_FIELDS
from njd.adapters.hyogo import _reading_reason,PROTOCOL_URL
from njd.hyogo_profile_review import _numeric_address
from njd.hyogo_registry_window import registry_window_problems

KIND='hyogo_cultural_building_location'
REASON='Hyogo profile address is missing'


def building_location_problems(s,f,source=None):
    if s.get('status')!='verified' or (source or {}).get('authority_status') in ('pending','unconfirmed'):
        return ['building location needs verified evidence and confirmed agency authority']
    prior=f.get('location_supplement');applied=isinstance(prior,dict) and prior.get('applied') is True
    changes=s.get('changes');name=f.get('name_raw');code=f.get('native_source_id')
    if (not isinstance(changes,dict) or set(changes)!={'address','municipality'}
        or changes['municipality']!='洲本市' or not _plain(changes['address'])
        or not re.fullmatch(r'洲本市[^0-9０-９]+[0-9０-９]+(?:-[0-9０-９]+)*',changes['address'])):
        return ['building location requires a literal full municipal address']
    if (f.get('source_key')!='hyogo' or f.get('prefecture_code')!='28' or f.get('prefecture')!='兵庫県'
        or not _plain(name) or f.get('listed_name')!=name or not isinstance(code,str) or not re.fullmatch('[0-9]{7}',code)
        or f.get('listing_url')!='https://www.hyogo-jinjacho.com/data/'+code+'.html'
        or f.get('review_reason')!=REASON or f.get('name_rendering_status') in ('external_glyph','unrenderable')
        or any(f.get(k) for k in ('identity_review_required','source_conflicts'))
        or not ((f.get('status')=='pending' and f.get('reason')==REASON)
                or (applied and f.get('status')=='verified' and not f.get('reason')))
        or _raw_field(f,'address')!='' or _raw_field(f,'municipality')!='' or f.get('map_address_raw')!=''
        or f.get('address') not in ('',changes['address']) or f.get('municipality') not in ('','洲本市')):
        return ['building location cannot override another acquired condition']
    raw=f.get('address_raw')
    if not isinstance(raw,str) or not re.fullmatch(r'〒[0-9]{3}-[0-9]{4}',raw):return ['missing original postal-only caption']
    original={k:f.get(k) for k in _SNAPSHOT_FIELDS};original.update(address='',municipality='')
    if (s.get('original')!=original or s.get('facility_id')!=f.get('id') or not _plain(s.get('entry_id'))
        or not _hash(s.get('expected_source_hash')) or s['expected_source_hash']!=f.get('source_hash')
        or not _plain(s.get('reason'))):return ['building location differs from original identity or fingerprint']
    refs=[s.get(k) for k in ('reference','map_reference','municipal_reference','registry_reference')]
    if any(not isinstance(x,dict) for x in refs):return ['building location lacks four inspected source records']
    profile,mapped,town,reg=refs
    try:
        approved=datetime.fromisoformat(s.get('recorded_at',''))
        if approved.tzinfo is None:raise ValueError()
        for ref in refs:
            if (not _url(ref.get('url')) or not _hash(ref.get('page_hash'))
                or any(not isinstance(ref.get(k),str) or not ref[k] for k in ('title','locator','excerpt','source_kind'))):
                return ['incomplete building-location source provenance']
            fetched=datetime.fromisoformat(ref.get('fetched_at',''));checked=datetime.fromisoformat(ref.get('checked_at',''))
            if fetched.tzinfo is None or checked.tzinfo is None or not fetched<=checked<=approved:raise ValueError()
    except (TypeError,ValueError):return ['invalid building-location evidence chronology']
    kana=profile.get('reading_raw');printed=profile.get('printed_code_raw')
    if (not isinstance(kana,str) or _reading_reason(name,kana) or profile.get('reading_scope')!='full_name'
        or not isinstance(printed,str) or not re.fullmatch(code+r'/(?:本務|兼務)',printed)
        or profile.get('source_kind')!='agency' or profile.get('url')!=f['listing_url']
        or profile.get('page_hash')!=f.get('page_hash') or profile.get('locator')!=f.get('source_locator')
        or profile.get('name_raw')!=name or profile.get('address_raw')!=raw
        or hashlib.sha256((name+'\0'+kana+'\0').encode()).hexdigest()!=f.get('source_hash')
        or not all(v in profile['excerpt'] for v in (name,kana,printed,raw))):
        return ['building location differs from original typed agency profile']
    occ=f.get('xml_occurrences')
    if (not isinstance(occ,list) or len(occ)!=1 or not isinstance(occ[0],dict)
        or any(mapped.get(k)!=occ[0].get(k) for k in ('url','page_hash','locator','code_raw','name_raw','address_raw','protocol_url','href_derivation'))
        or mapped.get('source_kind')!='agency' or mapped.get('code_raw')!=code or mapped.get('name_raw')!=name
        or mapped.get('address_raw')!='' or not mapped.get('url','').startswith('https://www.hyogo-jinjacho.com/data/xml.php?')
        or mapped.get('protocol_url')!=PROTOCOL_URL or mapped.get('href_derivation')!='data/ + actual Locate code + .html'
        or not all(v in mapped['excerpt'] for v in (name,code))):
        return ['building location requires one unchanged original map identity']
    address=changes['address']
    if (town.get('source_kind')!='government_cultural_building' or town.get('publisher')!='洲本市教育委員会生涯学習課'
        or not re.fullmatch(r'https://www\.city\.sumoto\.lg\.jp/soshiki/34/[0-9]+\.html',town.get('url',''))
        or town.get('name_raw')!=name+'本殿' or town.get('owner_name_raw')!=name or town.get('manager_name_raw')!=name
        or town.get('address_raw')!=address or town.get('reading_scope')!='building_full_name'
        or not all(v in town['excerpt'] for v in (name+'本殿',name,address,'洲本市教育委員会生涯学習課'))):
        return ['municipal evidence must identify this named shrine main building and its full location']
    proof=s.get('building_identity_proof')
    if (not isinstance(proof,dict) or proof.get('profile_page_hash')!=profile['page_hash']
        or proof.get('municipal_page_hash')!=town['page_hash'] or proof.get('name_raw')!=name
        or proof.get('profile_code_raw')!=code or proof.get('building_name_raw')!=town['name_raw']):
        return ['building correspondence is not bound to both inspected bodies']
    years=proof.get('chronology');structure=proof.get('structure')
    if (not isinstance(years,list) or len(years)!=3 or any(not isinstance(x,dict) for x in years)
        or [x.get('event') for x in years]!=['construction','repair','repair']
        or any(not isinstance(x.get('year'),str) or not re.fullmatch('[0-9]{4}',x['year']) for x in years)
        or len({x['year'] for x in years})!=3 or not isinstance(structure,dict)):
        return ['building correspondence needs three distinct construction/repair years and structure']
    for x in years:
        a=x.get('profile_raw');b=x.get('municipal_raw');y=x['year']
        if (not _plain(a) or not _plain(b) or a not in profile['excerpt'] or b not in town['excerpt']
            or not re.search(r'[（(]'+y+r'年?[）)]',a) or not re.search(r'[（(]'+y+r'年?[）)]',b)
            or (x['event']=='construction' and ('本殿上棟' not in a or '再興' not in b))
            or (x['event']=='repair' and ('本殿改修' not in a or '修理' not in b))):
            return ['construction or repair observation differs from the two main-building descriptions']
    if (structure.get('profile_raw')!='三間社流造' or structure.get('municipal_raw')!='三間社流造'
        or '三間社流造' not in profile['excerpt'] or '三間社流造' not in town['excerpt']):
        return ['main-building structure is missing or conflicts']
    issues=registry_window_problems(reg)
    if issues:return issues
    fields=reg.get('source_fields');state=reg['registry_state_proof'];aza=proof.get('registered_additional_aza_raw')
    required=('corporateNumber','name','prefectureCode','prefectureName','cityName','streetNumber','postCode','kind','latest','process','closeDate','hihyoji','nameImageId','addressImageId','furigana')
    if not isinstance(fields,dict) or any(not isinstance(fields.get(k),str) for k in required):return ['invalid registered building-location fields']
    corp=fields['corporateNumber'];full=fields['prefectureName']+fields['cityName']+fields['streetNumber'];street=address.removeprefix('洲本市')
    match=re.fullmatch(r'([^0-9０-９]+)([0-9０-９]+(?:-[0-9０-９]+)*)',street)
    if (not match or not _plain(aza) or not re.fullmatch(r'字[^字0-9０-９-]+',aza)
        or reg.get('source_kind')!='government_corporate_register'
        or reg.get('url')!='https://www.houjin-bangou.nta.go.jp/download/zenken/index.html'
        or not re.fullmatch('[0-9]{13}',corp) or reg.get('corporate_number')!=corp
        or type(reg.get('csv_row')) is not int or reg['csv_row']<1
        or fields['name']!=name or reg.get('name_raw')!=name or reg.get('address_raw')!=full
        or fields['prefectureCode']!='28' or fields['prefectureName']!='兵庫県' or fields['cityName']!='洲本市'
        or fields['postCode']!=raw[1:].replace('-','') or fields['kind']!='399' or fields['latest']!='1'
        or fields['process']=='99' or fields['closeDate'] or fields['hihyoji']!='0' or fields['nameImageId'] or fields['addressImageId']
        or fields['furigana'] or _numeric_address(fields['streetNumber'])!=match[1]+aza+_numeric_address(match[2])
        or not all(v in reg['excerpt'] for v in (name,full,fields['postCode']))
        or type(state.get('active_shrine_corporation_count_at_full_address')) is not int or state['active_shrine_corporation_count_at_full_address']!=1
        or state.get('active_corporate_numbers_at_full_address')!=[corp]
        or type(state.get('active_same_name_postcode_count')) is not int or state['active_same_name_postcode_count']!=1
        or state.get('active_same_name_postcode_corporate_numbers')!=[corp]):
        return ['registry must corroborate unique name/postcode/full parcel while retaining its additional aza and blank kana']
    return []


def building_entry_problems(s,f,e):
    p=s.get('reference',{})
    if not isinstance(p,dict):
        return ['building location entry requires a structured profile reference']
    if (e.get('id')!=s.get('entry_id') or e.get('facility_id')!=f.get('id')
        or e.get('status') not in ('pending','verified') or e.get('reason') not in ('',REASON)
        or e.get('identity_review_required') or e.get('reading_source_kind')!='agency'
        or e.get('surface')!=f.get('name_raw') or e.get('name_raw')!=f.get('name_raw')
        or e.get('source_hash')!=f.get('source_hash') or e.get('page_hash')!=f.get('page_hash')
        or e.get('reading_raw')!=p.get('reading_raw') or e.get('reading_display_raw')!=p.get('reading_raw')
        or e.get('printed_code_raw')!=p.get('printed_code_raw') or e.get('reading_url')!=f.get('listing_url')):
        return ['building location cannot override entry identity, exclusions or literal profile reading']
    return []
