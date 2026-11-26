"""Prepare individually inspected shrine records published by municipalities."""
import copy
from datetime import datetime
import re
import unicodedata
from urllib.parse import urlsplit

from njd.agency_details import _full_reading
from njd.records import build_dataset, municipality_from_address


BASIS = 'municipal_reference'
READING_KIND = 'municipal'
SOURCE_KIND = 'municipal_shrine_record'
REFERENCE_BASES = ('wikipedia_reference', 'association_reference', BASIS)
PUBLISHERS = {
    'www.city.hiroshima.lg.jp': ('広島県', '広島市'),
    'www.city.mihara.hiroshima.jp': ('広島県', '三原市'),
    'www.city.fukuyama.hiroshima.jp': ('広島県', '福山市'),
    'www.city.oita.oita.jp': ('大分県', '大分市'),
}


def _host(url):
    if not isinstance(url, str):
        return None
    try:
        parsed = urlsplit(url)
    except ValueError:
        return None
    if parsed.scheme == 'https' and not parsed.username and not parsed.password:
        return parsed.hostname
    return None


def _dated_observation(observation):
    try:
        return (re.fullmatch('[0-9a-f]{64}', observation['page_hash']) is not None
                and datetime.fromisoformat(observation['checked_at']).utcoffset() is not None)
    except (KeyError, TypeError, ValueError):
        return False


def _observation_problems(reference, prefecture):
    from njd.report import PREFECTURES

    required = ('name_raw', 'reading_raw', 'address_raw', 'municipality', 'source_publisher',
                'url', 'title', 'locator', 'excerpt', 'terms_url')
    if not isinstance(reference, dict) or any(
        not isinstance(reference.get(field), str) or not reference[field].strip() for field in required
    ):
        return ['municipal reference lacks an observed source field']

    problems = []
    name, reading, address = (reference[field] for field in ('name_raw', 'reading_raw', 'address_raw'))
    if reference['excerpt'] != f'名称 {name} / 読み {reading} / 所在地 {address}':
        problems.append('municipal excerpt differs from the observed name, reading or address')
    try:
        _full_reading(name, reading)
        if reference.get('reading_scope') != 'full_name':
            raise ValueError()
    except ValueError:
        problems.append('municipal full-name reading is absent or invalid')

    municipality = municipality_from_address(address, prefecture)
    explicit_prefecture = next((name for name in PREFECTURES if address.startswith(name)), None)
    if (not municipality or municipality != reference['municipality']
            or explicit_prefecture not in (None, prefecture)
            or not re.search(r'\d(?:番地|番|号)?$', address.strip())):
        problems.append('municipal address lacks the observed municipality and lot or house number')
    host = _host(reference['url'])
    authority = reference.get('authority_reference')
    if (PUBLISHERS.get(host) != (prefecture, reference['source_publisher'])
            or _host(reference['terms_url']) != host or not isinstance(authority, dict)
            or authority.get('url') != reference['terms_url'] or not _dated_observation(authority)
            or not isinstance(authority.get('excerpt'), str)
            or reference['source_publisher'] not in authority['excerpt']):
        problems.append('municipal publisher and terms must be evidenced on the publication host')
    if not _dated_observation(reference):
        problems.append('municipal publication hash or inspection time is invalid')
    return problems


def _address_key(address, prefecture):
    value = unicodedata.normalize('NFKC', address).removeprefix(prefecture)
    value = re.sub(r'\s+', '', value).replace('大字', '')
    value = re.sub(r'(?<=\d)(?:番地?(?:の)?|の|−|―|‐)(?=\d)', '-', value)
    return re.sub(r'(?<=\d)(?:番地|番|号)$', '', value)


def _name_key(name, municipality):
    return municipality, unicodedata.normalize('NFKC', name).strip()


def identity_conflicts(facilities, municipal_facility_ids):
    """Check potential duplicate facilities after merging source snapshots."""
    if not municipal_facility_ids:
        return []
    prefectures = {f.get('prefecture_code') for f in facilities if f.get('id') in municipal_facility_ids}
    addresses, local_names = {}, {}
    for facility in facilities:
        code = facility.get('prefecture_code')
        if code not in prefectures:
            continue
        facility_id = facility.get('id')
        if facility.get('address'):
            key = code, _address_key(facility['address'], facility.get('prefecture', ''))
            addresses.setdefault(key, set()).add(facility_id)
        if facility.get('name_raw') and facility.get('municipality'):
            key = code, _name_key(facility['name_raw'], facility['municipality'])
            local_names.setdefault(key, set()).add(facility_id)
    return sorted({facility_id for groups in (addresses, local_names) for ids in groups.values()
                   if len(ids) > 1 for facility_id in ids & municipal_facility_ids})


def reference_problems(facility, entry, source):
    from njd.canonical import _prefecture_key
    from njd.report import PREFECTURES

    reference = facility.get('source_reference')
    problems = _observation_problems(reference, facility.get('prefecture', ''))
    if problems:
        return problems
    if (source.get('listing_basis') != BASIS or facility.get('listing_basis') != BASIS
            or entry.get('listing_basis') != BASIS or facility.get('agency')
            or source.get('official_agency_listing_verified') is not False):
        problems.append('municipal reference has a conflicting listing or agency basis')
    try:
        code = facility['prefecture_code']
        if (source.get('source_key') != _prefecture_key(code) + '_municipal'
                or facility.get('source_key') != source['source_key'] or code != source.get('prefecture_code')
                or facility.get('prefecture') != PREFECTURES[int(code) - 1]
                or reference.get('source_kind') != SOURCE_KIND):
            raise ValueError()
    except (KeyError, ValueError):
        problems.append('municipal reference source and prefecture scope differ')
    observed = tuple(reference[field] for field in (
        'name_raw', 'reading_raw', 'address_raw', 'municipality', 'url', 'page_hash',
        'checked_at', 'locator', 'source_publisher',
    ))
    acquired = (facility.get('name_raw'), entry.get('reading_raw'), facility.get('address'),
                facility.get('municipality'), facility.get('listing_url'), facility.get('page_hash'),
                facility.get('fetched_at'), facility.get('source_locator'),
                facility.get('source_publisher'))
    if observed != acquired or facility.get('curated_source_record') is not True:
        problems.append('municipal reference differs from the acquired facility or registration')
    reading_kind = entry.get('reading_source_kind')
    if (reading_kind not in (READING_KIND, 'reference', 'user_review')
            or reading_kind == READING_KIND and (entry.get('reading_url') != reference['url']
                                                  or entry.get('evidence') != reference['excerpt'])):
        problems.append('municipal reading does not cite the observed publication')
    return problems


def dataset_from_references(source_key, code, references, *, existing):
    """Build a source snapshot from explicit and individually reviewed observations."""
    from njd.canonical import _prefecture_key
    from njd.report import PREFECTURES
    from njd.validation import blocking_problems

    if source_key != _prefecture_key(code) + '_municipal':
        raise ValueError('municipal source key differs from the prefecture')
    prefecture = PREFECTURES[int(code) - 1]
    references = list(references)
    same_prefecture = [facility for facility in (existing or {}).get('facilities', [])
                       if facility.get('prefecture_code') == code]
    known_addresses = {_address_key(facility['address'], prefecture) for facility in same_prefecture}
    known_names = {_name_key(facility['name_raw'], facility['municipality'])
                   for facility in same_prefecture}
    rows = []
    for reference in references:
        problems = _observation_problems(reference, prefecture)
        if problems:
            raise ValueError(', '.join(problems))
        address = _address_key(reference['address_raw'], prefecture)
        name = _name_key(reference['name_raw'], reference['municipality'])
        if address in known_addresses or name in known_names:
            raise ValueError('possible existing municipal facility requires identity review')
        known_addresses.add(address)
        known_names.add(name)
        rows.append(dict(name=reference['name_raw'], reading_raw=reference['reading_raw'],
                         address=reference['address_raw'], municipality=reference['municipality'],
                         url=reference['url'], fetched_at=reference['checked_at'],
                         page_hash=reference['page_hash'], locator=reference['locator'],
                         evidence=reference['excerpt']))

    source = dict(listing_basis=BASIS, authority_status='reference_source',
                  official_agency_listing_verified=False,
                  coverage='個別に確認した自治体の公刊資料に掲載された神社',
                  redistribution_status='参照別に利用条件を保持。本文・画像は配布対象外')
    data = build_dataset(source_key, code, prefecture, '', rows, metadata=source)
    data['collection'].pop('agency')
    for facility, entry, reference in zip(data['facilities'], data['entries'], references, strict=True):
        facility.pop('agency')
        facility.update(listing_basis=BASIS, source_publisher=reference['source_publisher'],
                        source_reference=dict(copy.deepcopy(reference), source_kind=SOURCE_KIND),
                        curated_source_record=True)
        entry.update(listing_basis=BASIS, reading_source_kind=READING_KIND)

    problems = blocking_problems(data)
    if problems:
        raise ValueError(f'municipal source validation failed: {problems[:3]}')
    return data
