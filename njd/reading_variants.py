"""Two literal full readings of one unchanged typed Hyogo profile subject."""
from datetime import datetime
import hashlib
import re
from uuid import NAMESPACE_URL,uuid5
from njd.locations import _plain,_hash,raw_address
from njd.normalize import normalize_reading
from njd.adapters.hyogo import _reading_reason,_city_name_comparison,_url as agency_url,CITY_NAME_CHANGE

KIND='same_name_parenthesized_full_readings'
SUPERSEDED='Superseded by explicitly reviewed full-reading variants'


def variant_id(parent,surface,reading):
    return str(uuid5(NAMESPACE_URL,f'{parent}|same-name-full-reading-variant|{surface}|{reading}'))


def _before(value,approved):
    try:
        date=datetime.fromisoformat(value)
        return date.tzinfo is not None and date<=approved
    except (TypeError,ValueError):return False


def variant_problems(review,facility,entry,source=None):
    if (review.get('review_kind')!=KIND or review.get('confirmation')!='source_review'
        or not _plain(review.get('case_id')) or not _plain(review.get('reason'))
        or any(review.get(k) for k in ('split','excluded_name_prefix','excluded_reading_prefix','accepted_identity_differences','resolved_reading_conflicts'))):
        return ['unsupported full-reading variant review or identity concessions']
    proof=review.get('proof');name=facility.get('name_raw');raw=entry.get('reading_raw');address=raw_address(facility);code=facility.get('native_source_id')
    parent=str(uuid5(NAMESPACE_URL,f"{facility.get('id')}|primary"))
    if (not isinstance(proof,dict) or proof.get('kind')!='agency_same_name_parenthesized_full_readings'
        or any(proof.get(k)!=v for k,v in dict(entry_id=parent,facility_id=facility.get('id'),expected_source_hash=entry.get('source_hash'),
            native_source_id=code,formal_name_raw=name,whole_reading_raw=raw,whole_reading_field='header.hero div.kana').items())):
        return ['variant proof differs from the original subject/whole kana']
    if (facility.get('source_key')!='hyogo' or facility.get('prefecture_code')!='28' or facility.get('prefecture')!='兵庫県'
        or facility.get('status')!='verified' or facility.get('reason') or not _plain(name) or facility.get('listed_name')!=name
        or any(c in name for c in '()（）') or not _plain(address) or facility.get('address')!=address
        or not _plain(facility.get('municipality')) or not address.startswith(facility['municipality'])
        or not re.search('[0-9０-９]+(?:-[0-9０-９]+)*$',address)
        or any(facility.get(k) for k in ('identity_review_required','review_reason','source_conflicts'))
        or facility.get('name_rendering_status') in ('external_glyph','unrenderable')
        or entry.get('identity_review_required') or entry.get('correction')
        or (source or {}).get('authority_status') in ('pending','unconfirmed')
        or not isinstance(code,str) or not re.fullmatch('[0-9]{7}',code)
        or facility.get('listing_url')!='https://www.hyogo-jinjacho.com/data/'+code+'.html'):
        return ['full-reading variants cannot override identity, location, exclusion or authority conditions']
    outputs=review.get('outputs')
    if (not isinstance(raw,str) or entry.get('reading_display_raw')!=raw or not _hash(entry.get('source_hash'))
        or entry.get('source_hash')!=facility.get('source_hash')
        or hashlib.sha256('\0'.join((name,raw,address)).encode()).hexdigest()!=entry['source_hash']
        or review.get('facility_id')!=facility['id'] or review.get('expected_source_hash')!=entry['source_hash']
        or review.get('original')!=dict(name_raw=name,reading_raw=raw,address=address,listing_url=facility['listing_url'])
        or not isinstance(outputs,list) or len(outputs)!=2 or any(not isinstance(o,dict) for o in outputs)):
        return ['variant review is stale or lacks exactly two bound outputs']
    match=re.fullmatch(r'([ァ-ヺー]+)（([ァ-ヺー]+)）',raw)
    if not match or any(_reading_reason(name,match[i]) for i in (1,2)):
        return ['variant kana is not exactly two fully printed name readings']
    intervals=[dict(start=match.start(i),end=match.end(i),raw=match[i],reading=normalize_reading(match[i])) for i in (1,2)]
    delimiters=[dict(start=match.end(1),end=match.end(1)+1,raw='（'),dict(start=match.end(2),end=match.end(2)+1,raw='）')]
    ranges=(proof.get('reading_intervals'),proof.get('delimiters'))
    if (any(not isinstance(rows,list) or len(rows)!=2 or any(not isinstance(row,dict) or any(type(row.get(k)) is not int for k in ('start','end')) for row in rows) for rows in ranges)
        or ranges[0]!=intervals or ranges[1]!=delimiters):
        return ['variant intervals/delimiters do not cover the original whole kana']
    for output,interval in zip(outputs,intervals):
        selected=output.get('source_interval')
        if (not isinstance(selected,dict) or set(selected)!={'start','end'} or any(type(selected[k]) is not int for k in ('start','end'))
            or selected!={k:interval[k] for k in ('start','end')}
            or any(output.get(k)!=v for k,v in dict(surface=name,reading=interval['reading'],source_reading_raw=interval['raw'],
                reading_url=facility['listing_url'],basis='agency_full_reading_variant').items())):
            return ['variant outputs are not the unchanged whole source tokens']
    if outputs[0]['reading']==outputs[1]['reading']:return ['duplicate literal full-reading variants']
    if entry.get('id')==parent and not entry.get('parent_entry_id'):
        prior=entry.get('human_review')
        own_excluded=(entry.get('status')=='excluded' and entry.get('reason')==SUPERSEDED
            and entry.get('superseded_by_review')==review['case_id'] and isinstance(prior,dict) and prior.get('review_kind')==KIND)
        if not own_excluded and not (entry.get('status')=='pending' and entry.get('reason')=='missing or nonliteral full agency reading'):
            return ['original variant parent has another condition']
    elif (entry.get('parent_entry_id')!=parent or entry.get('derivation_kind')!=KIND
        or entry.get('id')!=variant_id(parent,name,entry.get('reading'))
        or entry.get('reading') not in [x['reading'] for x in outputs] or entry.get('reading_source_kind')!='user_review'
        or entry.get('status')!='verified' or entry.get('reason')):
        return ['invalid full-reading variant child identity/status']
    refs=review.get('references')
    if not isinstance(refs,list) or len(refs)!=1 or not isinstance(refs[0],dict):return ['variant selection requires one typed profile reference']
    ref=refs[0];display=facility.get('address_raw');printed=entry.get('printed_code_raw')
    try:
        approved=datetime.fromisoformat(review.get('recorded_at',''))
        if approved.tzinfo is None:raise ValueError()
    except (TypeError,ValueError):return ['invalid variant approval time']
    if (not isinstance(display,str) or not re.fullmatch(r'〒[0-9]{3}-[0-9]{4}\r?\n'+re.escape(address),display)
        or not isinstance(printed,str) or not re.fullmatch(code+r'/(?:本務|兼務)',printed)
        or ref.get('source_kind')!='agency' or ref.get('url')!=facility['listing_url']
        or ref.get('name_raw')!=name or ref.get('reading_raw')!=raw or ref.get('address_raw')!=address
        or ref.get('display_address_raw')!=display or ref.get('printed_code_raw')!=printed
        or ref.get('locator')!=facility.get('source_locator') or not _plain(ref.get('title'))
        or not _hash(ref.get('page_hash')) or ref['page_hash']!=facility.get('page_hash')
        or ref.get('field_counts')!=dict(formal_names=1,kana_fields=1,addresses=1,printed_codes=1)
        or any(type(v) is not int for v in ref['field_counts'].values())
        or not isinstance(ref.get('excerpt'),str) or not all(v in ref['excerpt'] for v in (name,raw,display,printed))
        or not _before(ref.get('checked_at'),approved)):
        return ['variant profile lacks exact single heading/kana/code/address provenance']
    checked=datetime.fromisoformat(ref['checked_at'])
    if not _before(ref.get('fetched_at'),checked):return ['variant profile acquisition follows inspection']
    if any(proof.get(k)!=v for k,v in dict(profile_url=ref['url'],profile_page_hash=ref['page_hash'],profile_address=address,
        profile_address_raw=display,profile_printed_code_raw=printed).items()):return ['variant proof differs from inspected profile']
    occurrences=facility.get('xml_occurrences');mapped=proof.get('xml_reference')
    if (not isinstance(occurrences,list) or len(occurrences)!=1 or not isinstance(occurrences[0],dict) or not isinstance(mapped,dict)
        or any(mapped.get(k)!=occurrences[0].get(k) for k in ('url','page_hash','locator','code_raw','name_raw','address_raw','protocol_url','href_derivation'))
        or mapped.get('code_raw')!=code or mapped.get('name_raw')!=name or mapped.get('address_raw')!=facility.get('map_address_raw')
        or not _plain(mapped.get('address_raw')) or not _hash(mapped.get('page_hash')) or not _plain(mapped.get('locator'))
        or not _before(mapped.get('fetched_at'),approved)):
        return ['variant review lacks the single original map identity']
    try:
        if agency_url(mapped.get('url'))!=mapped['url'] or '/data/xml.php?' not in mapped['url']:raise ValueError()
    except (TypeError,ValueError):return ['invalid variant map endpoint']
    if mapped['address_raw']!=address:
        comparison=_city_name_comparison(mapped['address_raw'],address)
        if comparison is None:return ['variant map/profile full addresses differ']
        comparison['profile_address_raw']=display
        if facility.get('address_comparisons')!=[comparison] or proof.get('existing_city_name_change')!=[comparison]:
            return ['variant review lacks unchanged prior ordinance-bound city comparison']
        ordinance=proof.get('city_name_change_recheck')
        if (not isinstance(ordinance,dict) or ordinance.get('url')!=CITY_NAME_CHANGE['ordinance_reference']['url']
            or not _hash(ordinance.get('page_hash')) or not _plain(ordinance.get('locator'))
            or not isinstance(ordinance.get('excerpt'),str)
            or any(s not in ordinance['excerpt'] for s in ('篠山市の名称を丹波篠山市に変更する。','この条例は、平成31年5月1日から施行する。'))
            or not _before(ordinance.get('checked_at'),approved)):
            return ['variant city-name difference lacks inspected ordinance text']
        if not _before(ordinance.get('fetched_at'),datetime.fromisoformat(ordinance['checked_at'])):
            return ['variant ordinance acquisition follows inspection']
    elif facility.get('address_comparisons') or proof.get('existing_city_name_change') or proof.get('city_name_change_recheck'):
        return ['variant review claims an unnecessary city-name substitution']
    return []


def variant_graph_problems(entries):
    """An applied group keeps its original parent and both approved siblings."""
    indexed={};groups={};issues=[]
    for entry in entries:
        eid=entry.get('id')
        if isinstance(eid,str):indexed.setdefault(eid,[]).append(entry)
        if entry.get('derivation_kind')==KIND:
            parent=entry.get('parent_entry_id')
            if not isinstance(parent,str):issues.append((eid,'invalid full-reading variant parent type'))
            else:groups.setdefault(parent,[]).append(entry)
        review=entry.get('human_review')
        if (isinstance(eid,str) and isinstance(review,dict) and review.get('review_kind')==KIND
            and entry.get('status')=='excluded' and entry.get('reason')==SUPERSEDED):groups.setdefault(eid,[])
    for root,children in groups.items():
        parents=indexed.get(root,[]);parent=parents[0] if len(parents)==1 else None
        review=parent.get('human_review') if parent else None
        valid=bool(parent and parent.get('status')=='excluded' and parent.get('reason')==SUPERSEDED
            and isinstance(review,dict) and review.get('review_kind')==KIND and parent.get('superseded_by_review')==review.get('case_id'))
        outputs=review.get('outputs') if isinstance(review,dict) else None
        expected=set()
        if isinstance(outputs,list) and len(outputs)==2 and all(isinstance(o,dict) and all(isinstance(o.get(k),str) for k in ('surface','reading')) for o in outputs):
            expected={variant_id(root,o['surface'],o['reading']) for o in outputs}
        valid=valid and len(expected)==2 and len(children)==2 and {c.get('id') for c in children}==expected
        valid=valid and all(c.get('human_review')==review and c.get('facility_id')==parent.get('facility_id') and c.get('source_hash')==parent.get('source_hash') for c in children)
        if not valid:
            for member in parents+children:issues.append((member.get('id'),'incomplete or inconsistent full-reading variant parent/sibling group'))
    return issues
