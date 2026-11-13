"""Bound review of an explicitly printed current-address notation note.

Only comparison strings are normalized. Acquired addresses are never edited.
"""
from datetime import datetime
import re
import unicodedata
from urllib.parse import urljoin,urlsplit,parse_qs
from njd.locations import _hash,_url
from njd.normalize import normalize_reading,compare_address_units
from njd.address_layout import REASON

CURRENT_NOTE='※東日本大震災復興事業区画整理に伴い、令和3年11月27日に当住所へ表記変更となりました。'


def _numeric_address(value):
    value=compare_address_units(unicodedata.normalize('NFKC',value))
    value=re.sub(r'(?<=\d)丁目(?=\d)','-',value)
    return re.sub(r'(?<=\d)番地(?=\d)','-',value)


def current_address_note_problems(review,facility,entry):
    proof=review.get('address_presentation_proof')
    if not isinstance(proof,dict):return ['missing current-address note proof']
    expected=dict(kind='agency_current_address_notation_note',facility_id=facility.get('id'),
        entry_id=entry.get('id'),expected_source_hash=entry.get('source_hash'))
    if (any(proof.get(k)!=v for k,v in expected.items()) or not _hash(expected['expected_source_hash'])
        or facility.get('source_hash')!=entry.get('source_hash') or review.get('confirmation')!='source_review'):
        return ['current-address note proof differs from source identity']
    if any(r.get('status') not in ('pending','verified') or r.get('reason') not in ('',REASON) for r in (facility,entry)):
        return ['current-address note cannot override another condition']
    raw=facility.get('address');pref=facility.get('prefecture');municipality=facility.get('municipality')
    if not all(isinstance(x,str) and x for x in (raw,pref,municipality)):
        return ['missing original current-address field']
    parts=raw.replace('\r\n','\n').split('\n')
    if (len(parts)!=2 or parts[1]!=CURRENT_NOTE or any(ord(c)<32 or ord(c)==127 for c in parts[0])
        or not parts[0].startswith(pref+municipality) or not re.fullmatch(r'.+[^0-9０-９][0-9０-９]+(?:-[0-9０-９]+)+',parts[0])
        or proof.get('address_first_line_raw')!=parts[0] or proof.get('current_address_note_raw')!=parts[1]):
        return ['address is not the inspected current-address notation note']
    refs=review.get('references')
    if not isinstance(refs,list) or len(refs)!=3 or any(not isinstance(r,dict) for r in refs):
        return ['current-address note requires three separate inspected references']
    if any(not isinstance(r.get('evidence_role'),str) for r in refs):return ['invalid current-address source roles']
    roles={r['evidence_role']:r for r in refs}
    if set(roles)!={'agency_index','agency_detail','registered_address_identity'}:
        return ['missing or duplicate current-address source roles']
    for ref in refs:
        if (not _hash(ref.get('page_hash')) or not _url(ref.get('url'))
            or any(not isinstance(ref.get(k),str) or not ref[k] for k in ('locator','excerpt','name_raw','title','source_kind'))):
            return ['incomplete current-address reference provenance']
        for k in ('fetched_at','checked_at'):
            try:
                if datetime.fromisoformat(ref.get(k,'')).tzinfo is None:raise ValueError()
            except (TypeError,ValueError):return ['incomplete current-address reference date']
    name=facility.get('name_raw');kana=entry.get('reading_raw')
    if not isinstance(name,str) or not name or name!=facility.get('listed_name'):
        return ['current-address note requires an unchanged agency name']
    try:reading=normalize_reading(kana)
    except (ValueError,TypeError):return ['missing explicit whole agency reading']
    outputs=review.get('outputs')
    if (review.get('split') or not isinstance(outputs,list) or len(outputs)!=1 or not isinstance(outputs[0],dict)
        or any(outputs[0].get(k)!=v for k,v in dict(surface=name,reading=reading,
            reading_url=facility.get('listing_url'),basis='agency_selected').items())):
        return ['current-address note requires one unchanged agency reading']
    index=roles['agency_index'];detail=roles['agency_detail']
    if (index.get('url')!=facility.get('listing_url') or index.get('page_hash')!=facility.get('page_hash')
        or index.get('locator')!=facility.get('source_locator') or index.get('address_raw')!=raw):
        return ['current-address index differs from acquired source']
    for ref in (index,detail):
        if (ref.get('source_kind')!='agency' or ref.get('name_raw')!=name or ref.get('reading_raw')!=kana
            or ref.get('reading_scope')!='full_name' or not all(v in ref['excerpt'] for v in (name,kana,parts[0],parts[1]))):
            return ['missing explicit agency name, whole kana, current address or note']
    href=index.get('native_href_raw');sid=facility.get('native_source_id')
    if not isinstance(href,str) or not href or not isinstance(sid,str) or not re.fullmatch(r'[0-9]+',sid):
        return ['missing actual agency detail link and numeric identity']
    target=urljoin(index['url'],href)
    if not _url(target):return ['invalid agency detail link']
    source_url=urlsplit(index['url']);detail_url=urlsplit(target)
    if ((source_url.scheme,source_url.netloc)!=(detail_url.scheme,detail_url.netloc)
        or detail_url.path!=source_url.path.rsplit('/',1)[0]+'/detail.php'
        or detail_url.fragment or parse_qs(detail_url.query).get('code')!=[sid]
        or detail.get('url')!=target or proof.get('detail_url')!=target
        or detail.get('page_hash')!=proof.get('detail_page_hash') or detail.get('locator')!=proof.get('detail_locator')
        or detail.get('address_first_line_raw')!=parts[0] or detail.get('current_address_note_raw')!=parts[1]):
        return ['current-address detail is not the bound agency field/link']
    reg=roles['registered_address_identity'];fields=reg.get('source_fields');state=reg.get('registry_state_proof')
    keys=('corporateNumber','name','prefectureCode','prefectureName','cityName','streetNumber','kind',
        'latest','process','closeDate','hihyoji','nameImageId','addressImageId','furigana')
    if not isinstance(fields,dict) or any(not isinstance(fields.get(k),str) for k in keys) or not isinstance(state,dict):
        return ['invalid current-address registry fields/state']
    corporate=fields['corporateNumber'];address=fields['prefectureName']+fields['cityName']+fields['streetNumber']
    try:
        if any(not isinstance(v,str) or not re.fullmatch('[0-9]{8}',v) for v in (reg.get('snapshot'),state.get('as_of'))):raise ValueError()
        snapshot=datetime.strptime(reg.get('snapshot',''),'%Y%m%d')
        asof=datetime.strptime(state.get('as_of',''),'%Y%m%d')
        if asof<snapshot:raise ValueError()
    except (TypeError,ValueError):return ['invalid registry snapshot/state date']
    if (reg.get('source_kind')!='government_corporate_register'
        or reg.get('url')!='https://www.houjin-bangou.nta.go.jp/download/zenken/index.html'
        or not re.fullmatch('[0-9]{13}',corporate) or reg.get('corporate_number')!=corporate
        or type(reg.get('csv_row')) is not int or reg['csv_row']<1
        or reg.get('name_raw')!=name or fields['name']!=name or fields['prefectureCode']!=facility.get('prefecture_code')
        or fields['prefectureName']!=pref or reg.get('address_raw')!=address
        or _numeric_address(address)!=_numeric_address(parts[0])
        or fields['kind']!='399' or fields['latest']!='1' or fields['process']=='99'
        or fields['closeDate']!='' or fields['hihyoji']!='0' or fields['nameImageId'] or fields['addressImageId']
        or reg.get('reading_raw')!=fields['furigana'] or reg.get('reading_scope')!='full_name'
        or not all(v and v in reg['excerpt'] for v in (name,address,fields['furigana']))
        or type(state.get('active_matching_full_address_count')) is not int or state['active_matching_full_address_count']!=1
        or state.get('active_matching_corporate_numbers')!=[corporate]):
        return ['independent current name, whole address and reading are not bound']
    try:
        if normalize_reading(fields['furigana'])!=reading:raise ValueError()
    except ValueError:return ['registry whole kana differs from agency reading']
    return []
