"""Source-bound review of one locality/parcel line break, never address edits."""
from datetime import datetime
import re
import unicodedata
from njd.corrections import _reference_matches
from njd.locations import _hash,_url
from njd.normalize import normalize_reading

REASON='multiple address lines; facility identity requires review'


def address_layout_problems(review,facility,entry):
    proof=review.get('address_presentation_proof')
    if not isinstance(proof,dict):return ['missing address presentation proof']
    expected=dict(kind='agency_two_line_locality_parcel',facility_id=facility.get('id'),
        entry_id=entry.get('id'),expected_source_hash=entry.get('source_hash'))
    if any(proof.get(k)!=v for k,v in expected.items()) or not _hash(expected['expected_source_hash']):
        return ['address presentation proof differs from the source identity']
    if review.get('confirmation')!='source_review' or facility.get('source_hash')!=entry.get('source_hash'):
        return ['address presentation requires source review of one source hash']
    if (facility.get('status') not in ('pending','verified') or entry.get('status') not in ('pending','verified')
        or facility.get('reason') not in ('',REASON) or entry.get('reason') not in ('',REASON)):
        return ['address presentation cannot override another condition']
    if not isinstance(facility.get('name_raw'),str) or not facility['name_raw']:
        return ['missing acquired shrine name']
    raw=facility.get('address');pref=facility.get('prefecture');municipality=facility.get('municipality')
    if not isinstance(raw,str) or not isinstance(pref,str) or not isinstance(municipality,str):
        return ['missing acquired address layout']
    value=raw.replace('\r\n','\n');parts=value.split('\n')
    if (len(parts)!=2 or any(ord(c)<32 and c!='\n' for c in value)
        or not pref or not municipality or not parts[0].startswith(pref+municipality)
        or len(parts[0])<=len(pref+municipality) or re.search('[0-9０-９]',parts[0])
        or not re.fullmatch('[0-9]+(?:-[0-9]+)*',unicodedata.normalize('NFKC',parts[1]))
        or proof.get('joined_address_raw')!=''.join(parts)):
        return ['address is not one locality line and one complete parcel line']
    refs=review.get('references')
    if not isinstance(refs,list) or len(refs)!=3 or any(not isinstance(r,dict) for r in refs):
        return ['address presentation requires three separate source references']
    if any(not isinstance(r.get('evidence_role'),str) for r in refs):
        return ['address presentation source roles are invalid']
    byrole={r.get('evidence_role'):r for r in refs}
    if set(byrole)!={'agency_index','agency_address','registered_address_identity'}:
        return ['address presentation source roles are missing or duplicated']
    for ref in refs:
        if (not _hash(ref.get('page_hash')) or not _url(ref.get('url'))
            or any(not isinstance(ref.get(k),str) or not ref[k] for k in ('locator','excerpt','name_raw','title','source_kind'))):
            return ['address presentation reference provenance is incomplete']
        for field in ('fetched_at','checked_at'):
            try:
                if datetime.fromisoformat(ref.get(field,'')).tzinfo is None:raise ValueError()
            except (ValueError,TypeError):return ['address presentation reference date is incomplete']
    outputs=review.get('outputs')
    if not isinstance(outputs,list) or len(outputs)!=1 or not isinstance(outputs[0],dict):
        return ['address presentation requires one unchanged agency reading']
    try:reading=normalize_reading(entry.get('reading_raw'))
    except (ValueError,TypeError):return ['address presentation lacks literal agency kana']
    name=facility.get('name_raw');output=outputs[0];index=byrole['agency_index'];detail=byrole['agency_address']
    if (name!=facility.get('listed_name') or output.get('surface')!=name or output.get('reading')!=reading
        or output.get('basis')!='agency_selected' or output.get('reading_url')!=facility.get('listing_url')
        or index.get('source_kind')!='agency' or index.get('url')!=facility.get('listing_url')
        or index.get('page_hash')!=facility.get('page_hash') or index.get('locator')!=facility.get('source_locator')
        or index.get('name_raw')!=name or index.get('reading_raw')!=entry.get('reading_raw')
        or index.get('reading_scope')!='full_name' or index.get('address_raw')!=municipality
        or index.get('native_href_raw')!=facility.get('native_source_id')
        or not all(v in index.get('excerpt','') for v in (name,entry['reading_raw'],municipality))):
        return ['address presentation differs from the explicit agency index reading/link']
    source=facility.get('address_source')
    if (not isinstance(source,dict) or source.get('applied') is not True
        or source.get('url')!=facility.get('native_source_id') or source.get('link_url')!=source.get('url')
        or source.get('name_raw')!=name or source.get('address_raw')!=raw
        or detail.get('source_kind')!='agency' or detail.get('url')!=source.get('url')
        or detail.get('page_hash')!=source.get('page_hash') or detail.get('locator')!=source.get('locator')
        or detail.get('name_raw')!=name or detail.get('address_raw')!=raw
        or not all(v in detail.get('excerpt','') for v in (name,raw))):
        return ['address presentation differs from the acquired typed address field']
    reg=byrole['registered_address_identity'];fields=reg.get('source_fields');state=reg.get('registry_state_proof')
    if not isinstance(fields,dict) or not isinstance(state,dict):return ['missing independent full-address identity']
    if any(not isinstance(fields.get(k),str) for k in ('corporateNumber','name','prefectureCode','prefectureName',
        'cityName','streetNumber','kind','latest','process','closeDate','hihyoji','nameImageId','addressImageId','furigana')):
        return ['invalid registered identity field types']
    corporate=fields.get('corporateNumber')
    if (reg.get('source_kind')!='government_corporate_register'
        or reg.get('url')!='https://www.houjin-bangou.nta.go.jp/download/zenken/index.html'
        or not isinstance(corporate,str) or not re.fullmatch('[0-9]{13}',corporate)
        or reg.get('corporate_number')!=corporate or type(reg.get('csv_row')) is not int or reg['csv_row']<1
        or not isinstance(reg.get('snapshot'),str) or not re.fullmatch('[0-9]{8}',reg['snapshot'])
        or fields.get('name')!=name or reg.get('name_raw')!=name
        or fields.get('prefectureCode')!=facility.get('prefecture_code') or fields.get('prefectureName')!=pref
        or any(not isinstance(fields.get(k),str) for k in ('cityName','streetNumber'))
        or reg.get('address_raw')!=pref+fields.get('cityName','')+fields.get('streetNumber','')
        or not all(v in reg['excerpt'] for v in (name,reg.get('address_raw','')))
        or fields.get('kind')!='399' or fields.get('latest')!='1' or fields.get('process')=='99'
        or fields.get('closeDate')!='' or fields.get('hihyoji')!='0'
        or fields.get('nameImageId')!='' or fields.get('addressImageId')!='' or fields.get('furigana')!=''
        or type(state.get('active_matching_full_address_count')) is not int or state['active_matching_full_address_count']!=1
        or state.get('active_matching_corporate_numbers')!=[corporate]
        or not isinstance(state.get('as_of'),str) or not re.fullmatch('[0-9]{8}',state['as_of'])
        or not _reference_matches(reg,facility,entry,{})):
        return ['independent unique active name/full-address identity is not bound']
    return []
