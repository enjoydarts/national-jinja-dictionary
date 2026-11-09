"""Evidence-backed overlays; acquired names/readings remain immutable."""
import copy
import re
import unicodedata
from datetime import datetime
from urllib.parse import urlsplit
from njd.normalize import normalize_reading


def _url(value):
    try:return urlsplit(value).scheme in ('http','https') and bool(urlsplit(value).hostname)
    except (TypeError,ValueError):return False


def _comparison(value):
    """Matching only. Never writes normalized text to acquired/output fields."""
    return re.sub(r'\s+','',unicodedata.normalize('NFKC',value or ''))


def _reference_matches(ref,facility,entry,changes):
    names={_comparison(facility.get('listed_name')),_comparison(entry.get('surface')),
           _comparison(changes.get('surface'))}-{''}
    if _comparison(ref.get('name_raw')) not in names:return False
    def address(value):
        return _comparison(value).removeprefix(facility.get('prefecture','')).replace('大字','').removesuffix('番地')
    actual=address(ref.get('address_raw'))
    sources=[facility.get('address')]
    detail=facility.get('address_source',{})
    if detail.get('url')==facility.get('native_source_id'):
        sources.append(detail.get('address_raw'))
    # A source may publish only a locality. Exact full street numbers, when
    # present, must match; do not accept lot 1 as a prefix of lot 10.
    for raw in sources:
        expected=address(raw)
        if not expected or not actual:continue
        if actual==expected:return True
        if not re.search(r'\d',expected) and actual.startswith(expected):return True
    return False


def correction_problems(correction,facility,entry,source=None):
    problems=[]
    if not isinstance(correction,dict):return ['invalid correction object']
    if correction.get('status')!='verified':return ['correction is not verified']
    if (source or {}).get('authority_status') in ('pending','unconfirmed'):
        problems.append('official agency listing authority remains unconfirmed')
    if entry.get('identity_review_required'):problems.append('facility identity still requires review')
    if correction.get('facility_id')!=facility['id']:problems.append('facility identity differs from correction target')
    if correction.get('expected_source_hash')!=entry.get('source_hash'):problems.append('correction is stale; acquired source changed')
    original=correction.get('original',{})
    expected=dict(name_raw=facility.get('name_raw'),reading_raw=entry.get('reading_raw'),address=facility.get('address'),listing_url=facility.get('listing_url'))
    if original!=expected:problems.append('original source snapshot differs')
    if not correction.get('reason') or not correction.get('identity_match'):problems.append('missing correction reason or facility comparison')
    changes=correction.get('changes')
    if not isinstance(changes,dict) or not changes or set(changes)-{'surface','reading'}:
        return problems+['unsupported or missing correction changes']
    if any(not isinstance(v,str) or not v for v in changes.values()):return problems+['invalid corrected value']
    if any(ord(c)<32 or ord(c)==127 for c in changes.get('surface','')):problems.append('control character in corrected surface')
    if '<' in changes.get('surface','') or '>' in changes.get('surface',''):problems.append('corrected surface is not plain text')
    refs=correction.get('references')
    if not isinstance(refs,list) or not refs:return problems+['missing inspected references']
    name_supported='surface' not in changes;reading_supported='reading' not in changes;identity_supported=False
    for ref in refs:
        if not isinstance(ref,dict):problems.append('invalid reference object');continue
        if not _url(ref.get('url')) or not ref.get('title') or not ref.get('source_kind'):
            problems.append('reference URL, title or source type missing')
        try:datetime.fromisoformat(ref.get('checked_at',''))
        except (TypeError,ValueError):problems.append('reference inspection date missing')
        if not ref.get('name_raw') or not ref.get('excerpt'):
            problems.append('reference name or actual excerpt missing')
        bound=_reference_matches(ref,facility,entry,changes)
        if bound and ref.get('name_raw') and ref.get('name_raw') in ref.get('excerpt','') and ref.get('address_raw') and ref.get('address_raw') in ref.get('excerpt',''):
            identity_supported=True
        if bound and 'surface' in changes and ref.get('name_raw')==changes['surface'] and changes['surface'] in ref.get('excerpt',''):
            name_supported=True
        if 'reading' in changes:
            raw=ref.get('reading_raw','')
            try:
                if bound and normalize_reading(raw)==changes['reading'] and raw in ref.get('excerpt',''):
                    reading_supported=True
            except (TypeError,ValueError):pass
    if not identity_supported:problems.append('no inspected reference explicitly identifies name and location')
    if not name_supported:problems.append('corrected name is not explicit in the inspected reference')
    if not reading_supported:problems.append('corrected full reading is not explicit in the inspected reference')
    return problems


def apply_corrections(data,document):
    if document.get('schema_version')!=1 or not isinstance(document.get('entries'),dict):
        raise ValueError('unsupported correction document')
    corrections=document['entries']
    if not corrections:return data
    result=copy.deepcopy(data);facilities={f['id']:f for f in result['facilities']};applied=[];pending=[];seen=set()
    for entry in result['entries']:
        correction=corrections.get(entry['id'])
        if correction is None:continue
        seen.add(entry['id']);facility=facilities[entry['facility_id']]
        source=result['collection'].get('sources',{}).get(facility.get('source_key'),result['collection'])
        problems=correction_problems(correction,facility,entry,source)
        entry['correction']=copy.deepcopy(correction)
        if problems:
            entry['status']='pending';entry['reason']='; '.join(problems+[correction.get('reason','')])
            entry['correction']['status']='needs_review';entry['correction']['validation_problems']=problems
            pending.append(entry['id']);continue
        changes=correction['changes']
        if 'surface' in changes:
            entry['surface']=changes['surface']
            # Only name-rendering defects can be resolved by a name reference.
            # Missing addresses, conflicting identities and multiple addresses
            # remain pending even when a reading/name is known elsewhere.
            name_can_be_resolved=bool(facility['name_raw'] or facility.get('native_source_id'))
            name_reasons={'control or layout characters in source name; explicit review required',
                          'source name uses an external glyph; Unicode correction requires references',
                          'missing name, address or municipality',
                          'regional agency name differs from linked detail name'}
            name_only=facility['status']=='verified' or facility.get('reason') in name_reasons
            review_is_name_only=not facility.get('review_reason') or facility['review_reason']=='regional agency name differs from linked detail name'
            address_valid=facility['address'] and not any(ord(c)<32 or ord(c)==127 for c in facility['address'])
            if name_can_be_resolved and name_only and review_is_name_only and address_valid and facility['municipality'] and not facility.get('source_conflicts'):
                facility['status']='verified';facility['reason']=''
                facility['resolved_name_unicode']=changes['surface']
        if 'reading' in changes:
            entry['reading']=changes['reading'];entry['reading_source_kind']='reference'
            for ref in correction['references']:
                try:matched=normalize_reading(ref.get('reading_raw',''))==entry['reading'] and ref.get('reading_raw','') in ref.get('excerpt','')
                except (TypeError,ValueError):matched=False
                if matched and _reference_matches(ref,facility,entry,changes):entry['reading_url']=ref['url'];entry['checked_at']=ref['checked_at'];break
        reading_resolved='reading' in changes
        if not reading_resolved:
            try:reading_resolved=normalize_reading(entry['reading_raw'])==entry['reading']
            except (TypeError,ValueError):reading_resolved=False
        entry['status']='verified' if facility['status']=='verified' and reading_resolved else 'pending'
        entry['reason']='' if entry['status']=='verified' else (facility['reason'] or 'reading still requires evidence')
        (applied if entry['status']=='verified' else pending).append(entry['id'])
    result['collection']['corrections']=dict(applied=sorted(applied),pending=sorted(pending),unmatched=sorted(set(corrections)-seen))
    return result
