"""Evidence-backed overlays; acquired names/readings remain immutable."""
import copy
import re
import unicodedata
from datetime import datetime
from urllib.parse import urlsplit
from njd.normalize import normalize_reading
from njd.locations import raw_address


def _url(value):
    if not isinstance(value,str):return False
    try:return urlsplit(value).scheme in ('http','https') and bool(urlsplit(value).hostname)
    except (TypeError,ValueError):return False


def discovery_only(value):
    """The user designated this directory for finding candidates, not evidence."""
    if not isinstance(value,str):return False
    try:host=(urlsplit(value).hostname or '').lower().rstrip('.')
    except ValueError:return False
    return host=='jinja-net.jp' or host.endswith('.jinja-net.jp')


def _comparison(value):
    """Matching only. Never writes normalized text to acquired/output fields."""
    return re.sub(r'\s+','',unicodedata.normalize('NFKC',value or ''))


def _subject_profile_link(ref,facility,proof):
    """Require recorded observations, not a guessed URL or a nearby-site link."""
    link=proof.get('subject_link')
    if not isinstance(link,dict):return False
    locator=link.get('locator')
    if (link.get('relation')!='subject_agency_profile' or
        not isinstance(locator,str) or not locator.strip() or
        link.get('reference_url')!=ref.get('url') or
        link.get('reference_page_hash')!=ref.get('page_hash')):return False
    def digest(value):return isinstance(value,str) and bool(re.fullmatch(r'[0-9a-f]{64}',value))
    if not digest(ref.get('page_hash')) or not digest(facility.get('page_hash')):return False
    href=link.get('href');target=facility.get('listing_url')
    if not _url(href) or not _url(target):return False
    before=urlsplit(href);after=urlsplit(target)
    # The only permitted redirect is the observed HTTP -> HTTPS upgrade of
    # the very same profile. No host/path/query substitution or credentials.
    if (before.username or before.password or after.username or after.password or
        before.fragment or after.fragment or
        (before.netloc,before.path,before.query)!=(after.netloc,after.path,after.query)):
        return False
    chain=link.get('responses')
    if not isinstance(chain,list) or len(chain) not in (1,2):return False
    if any(not isinstance(r,dict) for r in chain):return False
    if chain[0].get('url')!=href:return False
    for r in chain:
        if not digest(r.get('page_hash')):return False
        try:observed=datetime.fromisoformat(r.get('fetched_at',''))
        except (TypeError,ValueError):return False
        if observed.tzinfo is None:return False
    if len(chain)==2:
        if (before.scheme!='http' or after.scheme!='https' or
            chain[0].get('status') not in (301,302,307,308) or
            chain[0].get('location')!=target):return False
    elif href!=target:return False
    last=chain[-1]
    return (last.get('url')==target and last.get('status')==200 and
            last.get('page_hash')==facility['page_hash'])


def _additional_aza_matches(actual,expected,ref,facility):
    proof=ref.get('address_identity_proof')
    if not isinstance(proof,dict) or proof.get('kind')!='additional_aza_with_subject_link':return False
    extra=proof.get('added_aza_raw')
    if not isinstance(extra,str) or not re.fullmatch(r'(?:小字|字)[\u3400-\u9fff々〆ヶぁ-ゖァ-ヺー]+',extra):return False
    parcel=re.fullmatch(r'(.+?)([0-9]+(?:-[0-9]+)*)',expected)
    if not parcel or actual!=parcel[1]+extra+parcel[2]:return False
    return _subject_profile_link(ref,facility,proof)


def _reference_matches(ref,facility,entry,changes):
    names={_comparison(facility.get('listed_name')),_comparison(entry.get('surface')),
           _comparison(changes.get('surface'))}-{''}
    if _comparison(ref.get('name_raw')) not in names:return False
    def address(value):
        value=re.sub(r'^〒\d{3}-\d{4}','',_comparison(value))
        value=value.removeprefix(facility.get('prefecture',''))
        # Some agency lists omit 郡. Only remove a leading county after the
        # matching prefecture; never discard an unmatched prefecture prefix.
        value=re.sub(r'^[^都道府県]+?郡','',value)
        value=re.sub(r'(?<=\d)[−‐‑‒–—―](?=\d)','-',value)
        value=re.sub(r'(?<=\d)丁目(?=\d)','-',value)
        value=re.sub(r'(?<=\d)番(?:地)?(?:の)?(?=\d)','-',value)
        value=re.sub(r'(?<=\d)(?:番地|番|号)$','',value)
        return value.replace('大字','')
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
        if _additional_aza_matches(actual,expected,ref,facility):return True
        suffix=actual[len(expected):] if actual.startswith(expected) else ''
        if not re.search(r'\d',expected) and suffix and suffix[0].isdigit():return True
    return False


def _agency_reading_compatible(name,raw,scope,full):
    """Compare literal evidence, never construct a reading from a stem.

    An already supplied full reading may have only the stated shrine-name
    ending after the agency's stem. Prefix agreement cannot hide extra sounds.
    """
    try:stem=normalize_reading(raw)
    except (TypeError,ValueError):return False
    if stem==full:return True
    if scope=='full_name' or not full.startswith(stem):return False
    suffixes=[('神社',('じんじゃ','じんしゃ','しんじゃ','しんしゃ')),('神宮',('じんぐう',)),
        ('大社',('たいしゃ','だいしゃ','おおやしろ')),('宮',('ぐう','みや','きゅう')),('社',('しゃ','やしろ'))]
    endings=next((endings for suffix,endings in suffixes if name.endswith(suffix)),())
    return full[len(stem):] in endings


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
    expected=dict(name_raw=facility.get('name_raw'),reading_raw=entry.get('reading_raw'),address=raw_address(facility),listing_url=facility.get('listing_url'))
    snapshot_matches=original==expected
    if isinstance(original,dict) and set(original)==set(expected) and facility.get('native_source_id') and _url(original.get('listing_url')) and _url(expected['listing_url']):
        # Native facility identity and raw tuple/hash stay fixed even when a
        # CGI page adds pagination/session parameters. Keep the actual old
        # evidence URL; never rewrite it to a fabricated canonical URL.
        before=urlsplit(original.get('listing_url',''));after=urlsplit(expected['listing_url'])
        same_endpoint=bool(before.hostname) and (before.scheme,before.netloc,before.path,before.fragment)==(after.scheme,after.netloc,after.path,after.fragment)
        snapshot_matches=snapshot_matches or (same_endpoint and all(original[k]==expected[k] for k in ('name_raw','reading_raw','address')))
    if not snapshot_matches:problems.append('original source snapshot differs')
    if not correction.get('reason') or not correction.get('identity_match'):problems.append('missing correction reason or facility comparison')
    changes=correction.get('changes')
    if not isinstance(changes,dict) or not changes or set(changes)-{'surface','reading'}:
        return problems+['unsupported or missing correction changes']
    if any(not isinstance(v,str) or not v for v in changes.values()):return problems+['invalid corrected value']
    if any(ord(c)<32 or ord(c)==127 for c in changes.get('surface','')):problems.append('control character in corrected surface')
    if '<' in changes.get('surface','') or '>' in changes.get('surface',''):problems.append('corrected surface is not plain text')
    refs=correction.get('references')
    if not isinstance(refs,list) or not refs:return problems+['missing inspected references']
    registry_present=any(isinstance(r,dict) and r.get('source_kind')=='government_corporate_register' for r in refs)
    name_supported='surface' not in changes;reading_supported='reading' not in changes;identity_supported=False
    for ref in refs:
        if not isinstance(ref,dict):problems.append('invalid reference object');continue
        if discovery_only(ref.get('url')):problems.append('discovery-only directory cannot serve as dictionary evidence')
        if not _url(ref.get('url')) or not ref.get('title') or not ref.get('source_kind'):
            problems.append('reference URL, title or source type missing')
        try:datetime.fromisoformat(ref.get('checked_at',''))
        except (TypeError,ValueError):problems.append('reference inspection date missing')
        if not ref.get('name_raw') or not ref.get('excerpt'):
            problems.append('reference name or actual excerpt missing')
        bound=_reference_matches(ref,facility,entry,changes)
        if (registry_present and bound and 'reading' in changes and ref.get('reading_raw')
            and ref.get('source_kind') in ('agency','official_agency')
            and ref.get('reading_scope') in ('full_name','partial_or_absent')
            and _url(ref.get('url')) and _url(facility.get('listing_url'))
            and urlsplit(ref.get('url','')).hostname==urlsplit(facility.get('listing_url','')).hostname
            and not _agency_reading_compatible(ref['name_raw'],ref['reading_raw'],ref['reading_scope'],changes['reading'])):
            problems.append('proposed registry reading conflicts with literal agency kana; prefix agreement alone is insufficient')
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
                          'regional agency name differs from linked detail name',
                          'annotated official name requires review'}
            name_only=facility['status']=='verified' or facility.get('reason') in name_reasons
            review_is_name_only=not facility.get('review_reason') or facility['review_reason'] in {
                'regional agency name differs from linked detail name','annotated official name requires review'}
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
