"""A single CSV name placeholder bound to an individually inspected image."""
from datetime import datetime
import hashlib
import re
from urllib.parse import urljoin
from njd.locations import _plain,_hash,raw_address
from njd.normalize import normalize_reading
from njd.hyogo_profile_review import _numeric_address
from njd.hyogo_registry_window import DAILY_FILES,observed_between
from njd.corporate import image_review_problems
from njd.adapters.hyogo import _reading_reason

KIND='registered_name_image_full_reading'
ARCHIVE_URL='https://www.houjin-bangou.nta.go.jp/download/zenken/index.html'
ARCHIVE_HASH='87869a2c6b84617c97c9aa95138a34ef17899540cee159a81ac3529b3ea3d510'


def _before(value,approved):
    try:
        date=datetime.fromisoformat(value)
        return date.tzinfo is not None and date<=approved
    except (TypeError,ValueError):return False


def _window_problems(reg):
    state=reg.get('registry_state_proof')
    if (reg.get('snapshot')!='20261030' or reg.get('file_id')!='28432' or reg.get('page_hash')!=ARCHIVE_HASH
        or reg.get('zip_member')!='25_shiga_all_20261030.csv' or not isinstance(state,dict)
        or state.get('as_of')!='20261112' or type(state.get('daily_rows')) is not int or state['daily_rows']!=19178
        or not observed_between(reg.get('fetched_at'),'20261030',reg.get('checked_at'))
        or type(state.get('target_corporate_or_full_parcel_events')) is not int or state['target_corporate_or_full_parcel_events']!=0):
        return ['registered image differs from the inspected Shiga monthly/daily window']
    monthly=state.get('monthly_base')
    expected=dict(url=ARCHIVE_URL,page_hash=ARCHIVE_HASH,file_id='28432',snapshot='20261030',data_rows=44347)
    if (not isinstance(monthly,list) or len(monthly)!=1 or not isinstance(monthly[0],dict)
        or any(monthly[0].get(k)!=v for k,v in expected.items()) or type(monthly[0].get('data_rows')) is not int
        or not observed_between(monthly[0].get('fetched_at'),'20261030',reg.get('checked_at'))):
        return ['registered image lacks the inspected complete Shiga archive']
    daily=state.get('daily_deltas')
    if not isinstance(daily,list) or len(daily)!=8:return ['registered image lacks the eight inspected global daily archives']
    # These eight files are nationwide; only the monthly prefecture differs.
    for actual,pinned in zip(daily,DAILY_FILES):
        wanted={k:pinned[k] for k in ('date','file_id','page_hash','url')};wanted['data_rows']=pinned['rows']
        if (not isinstance(actual,dict) or any(actual.get(k)!=v for k,v in wanted.items()) or type(actual.get('data_rows')) is not int
            or not observed_between(actual.get('fetched_at'),pinned['date'],reg.get('checked_at'))):
            return ['registered image daily evidence differs from inspected files/counts/dates']
    return []


def image_correction_problems(correction,facility,entry,source=None):
    if (correction.get('correction_kind')!=KIND or correction.get('status')!='verified' or not _plain(correction.get('case_id'))
        or not _plain(correction.get('reason')) or not isinstance(correction.get('changes'),dict) or set(correction['changes'])!={'reading'}):
        return ['unsupported registered-name-image reading correction']
    from njd.agency_details import _shiga_index_url
    name=facility.get('name_raw');address=raw_address(facility);code=facility.get('native_source_id')
    if (facility.get('source_key')!='shiga' or facility.get('prefecture_code')!='25' or facility.get('prefecture')!='滋賀県'
        or not isinstance(facility.get('listing_url'),str) or not _shiga_index_url(facility['listing_url'])
        or facility.get('status')!='verified' or facility.get('reason') or not _plain(name) or facility.get('listed_name')!=name
        or not _plain(address) or facility.get('address')!=address or not _plain(facility.get('municipality'))
        or not address.startswith(facility['municipality']) or re.search('[0-9０-９]',address)
        or any(facility.get(k) for k in ('identity_review_required','source_conflicts','review_reason'))
        or facility.get('name_rendering_status') in ('external_glyph','unrenderable') or entry.get('identity_review_required') or entry.get('human_review')
        or (source or {}).get('authority_status') in ('pending','unconfirmed') or not isinstance(code,str) or not re.fullmatch('[0-9]{1,5}',code)):
        return ['registered-name-image correction cannot override another facility condition']
    if (entry.get('facility_id')!=facility.get('id') or entry.get('name_raw')!=name or entry.get('surface')!=name or entry.get('reading_raw')!=''
        or entry.get('listing_url')!=facility.get('listing_url') or entry.get('page_hash')!=facility.get('page_hash')
        or not _hash(entry.get('source_hash')) or entry['source_hash']!=facility.get('source_hash')
        or hashlib.sha256('\0'.join((name,'',address)).encode()).hexdigest()!=entry['source_hash']
        or correction.get('facility_id')!=facility.get('id') or correction.get('expected_source_hash')!=entry['source_hash']
        or correction.get('original')!=dict(name_raw=name,reading_raw='',address=address,listing_url=facility.get('listing_url'))):
        return ['registered-name-image correction is stale or changes an original field']
    refs=correction.get('references')
    if not isinstance(refs,list) or len(refs)!=2 or any(not isinstance(r,dict) for r in refs):return ['registered-name-image correction requires two inspected references']
    agency,reg=refs
    try:
        approved=datetime.fromisoformat(correction.get('recorded_at',''))
        if approved.tzinfo is None:raise ValueError()
    except (TypeError,ValueError):return ['invalid registered image approval time']
    for ref in refs:
        if (not all(_plain(ref.get(k)) for k in ('title','source_kind','name_raw','locator','excerpt')) or not _hash(ref.get('page_hash'))
            or not _before(ref.get('checked_at'),approved)):
            return ['incomplete registered image reference provenance']
        if not _before(ref.get('fetched_at'),datetime.fromisoformat(ref['checked_at'])):return ['registered image reference acquisition follows inspection']
    if reg.get('source_kind')!='government_corporate_register' or reg.get('url')!=ARCHIVE_URL:return ['registered image reading is not from the original NTA CSV']
    old=facility.get('agency_detail_reading_research');index=agency.get('index_proof')
    if not isinstance(old,dict) or not isinstance(old.get('index_proof'),dict) or not isinstance(old.get('reference'),dict) or not isinstance(index,dict):
        return ['registered image lacks original and inspected native agency bindings']
    original_index=old['index_proof'];original_detail=old['reference']
    url='https://www.shiga-jinjacho.jp/ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-detail.html?mode:view=1&view:oid='+code
    expected_index=dict(index_url=facility.get('listing_url'),index_locator=facility.get('source_locator'),source_id=code,name_raw=name,address_raw=address,
        base_href='https://www.shiga-jinjacho.jp/',url=url)
    if (any(original_index.get(k)!=v or index.get(k)!=v for k,v in expected_index.items())
        or original_index.get('index_page_hash')!=facility.get('page_hash') or not _hash(index.get('index_page_hash'))
        or not _plain(index.get('href_raw')) or index['href_raw']!=original_index.get('href_raw')
        or urljoin(index['base_href'],index['href_raw'])!=url
        or not _plain(index.get('index_excerpt')) or name not in index['index_excerpt'] or address not in index['index_excerpt']
        or not _before(index.get('index_checked_at'),approved)):
        return ['registered image native ID/href differs from the acquired index observation']
    full=agency.get('address_raw');stem=agency.get('reading_raw')
    if (agency.get('source_kind')!='agency' or agency.get('identity_only') is not True or agency.get('url')!=url
        or agency.get('agency_code')!=code or agency.get('name_raw')!=name or agency.get('reading_scope')!='partial_or_absent'
        or agency.get('alias_display_raw')!='' or not _plain(full) or not _plain(stem)
        or any(agency.get(k)!=original_detail.get(k) for k in ('url','agency_code','name_raw','address_raw','reading_raw','name_display_raw'))
        or not all(v in agency['excerpt'] for v in (name,stem,full)) or not full.startswith('滋賀県'+address)
        or not re.fullmatch('[0-9]+(?:-[0-9]+)*',_numeric_address(full[len('滋賀県'+address):]))):
        return ['registered image lacks the original code-bound full agency parcel and kana stem']
    fields=reg.get('source_fields');required=('corporateNumber','name','furigana','prefectureCode','prefectureName','cityName','streetNumber','kind','latest','process','closeDate','hihyoji','nameImageId','addressImageId')
    if not isinstance(fields,dict) or any(not isinstance(fields.get(k),str) for k in required):return ['invalid image-backed CSV fields']
    registered_full=fields['prefectureName']+fields['cityName']+fields['streetNumber']
    if (fields['kind']!='399' or fields['prefectureCode']!='25' or fields['prefectureName']!='滋賀県' or fields['latest']!='1'
        or fields['process']=='99' or fields['closeDate'] or fields['hihyoji']!='0' or fields['addressImageId'] or not fields['nameImageId']
        or not registered_full.startswith('滋賀県'+address)
        or _numeric_address(registered_full[len('滋賀県'+address):])!=_numeric_address(full[len('滋賀県'+address):])
        or type(reg.get('csv_row')) is not int or reg['csv_row']<1 or reg.get('reading_scope')!='full_name'
        or not _plain(reg.get('address_raw'))
        or not all(v and v in reg['excerpt'] for v in (fields['name'],fields['furigana'],reg.get('address_raw','')))):
        return ['registered image lacks active exact full-address/whole-kana CSV support']
    issues=image_review_problems(reg)
    if issues:return issues
    issues=_window_problems(reg)
    if issues:return issues
    state=reg['registry_state_proof'];corp=fields['corporateNumber']
    if (type(state.get('active_religious_corporations_at_native_full_address')) is not int or state['active_religious_corporations_at_native_full_address']!=1
        or state.get('active_corporate_numbers_at_native_full_address')!=[corp]):return ['registered image full parcel does not identify one active corporation']
    proof=reg.get('registered_name_image_identity');im=reg['image_reviews']['nameImageId'];csvname=fields['name']
    if not isinstance(proof,dict) or csvname.count('＿')!=1 or len(csvname)!=len(name):return ['registered image requires one explicit original CSV placeholder']
    index_in_name=csvname.index('＿')
    expected=dict(rule='literal_registered_name_placeholder_with_individual_image_review',target_entry_id=entry.get('id'),expected_source_hash=entry['source_hash'],
        image_field='nameImageId',image_id=fields['nameImageId'],image_page_hash=im.get('page_hash'),placeholder_character='＿',
        placeholder_indices_zero_based=[index_in_name],registered_name_raw=csvname,transcribed_character=name[index_in_name],transcribed_full_name_raw=name)
    indices=proof.get('placeholder_indices_zero_based')
    if (any(proof.get(k)!=v for k,v in expected.items()) or not isinstance(indices,list) or len(indices)!=1 or type(indices[0]) is not int
        or name[index_in_name]=='＿' or any(a!=b for i,(a,b) in enumerate(zip(csvname,name)) if i!=index_in_name)
        or im.get('placeholder_field_name_raw')!=csvname or im.get('placeholder_character')!='＿'
        or type(im.get('placeholder_character_index_zero_based')) is not int or im['placeholder_character_index_zero_based']!=index_in_name
        or im.get('transcribed_full_name_raw')!=name or name not in im['note']
        or not _before(im.get('checked_at'),approved) or not observed_between(im.get('fetched_at'),'20261030',im.get('checked_at'))):
        return ['registered image transcription changes more than the individually inspected placeholder']
    match=correction.get('identity_match');expected=dict(agency_native_id=code,actual_detail_id=code,agency_name_raw=name,original_address_raw=address,
        native_full_address_raw=full,registered_name_raw=csvname,registered_image_name_raw=name,registered_full_address_raw=reg['address_raw'])
    if not isinstance(match,dict) or any(match.get(k)!=v for k,v in expected.items()):return ['registered image identity declaration differs from actual source fields']
    from njd.corrections import _agency_reading_compatible
    try:
        reading=normalize_reading(fields['furigana'])
        if (_reading_reason(name,fields['furigana']) or correction['changes']['reading']!=reading
            or not _agency_reading_compatible(name,stem,'partial_or_absent',reading)):raise ValueError()
    except (TypeError,ValueError):return ['registered image reading is not the same CSV full kana compatible with the literal agency stem']
    prior=entry.get('correction')
    if entry.get('status')=='pending' and entry.get('reason')=='missing agency reading' and entry.get('reading')=='' and entry.get('reading_source_kind')=='agency':
        if prior:return ['registered image cannot replace another pending correction']
    elif not (entry.get('status')=='verified' and not entry.get('reason') and entry.get('reading')==reading and entry.get('reading_source_kind')=='reference'
        and entry.get('reading_url')==ARCHIVE_URL and isinstance(prior,dict) and prior.get('correction_kind')==KIND):
        return ['registered image cannot override another entry condition or exclusion']
    return []
