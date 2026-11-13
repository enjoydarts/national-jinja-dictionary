"""Pure, evidence-bound location supplements for addressless agency links."""
import copy
from datetime import datetime
import re
import unicodedata
from urllib.parse import unquote, urlsplit

from njd.normalize import normalize_reading
from njd.records import municipality_from_address


_MISSING_LOCATION = 'missing name, address or municipality'
_SNAPSHOT_FIELDS = ('name_raw', 'address', 'municipality', 'listing_url',
                    'official_site_url', 'native_source_id')


def _url(value):
    if (not isinstance(value, str)
            or any(unicodedata.category(c) == 'Cc' for c in value)):
        return False
    try:
        parts = urlsplit(value)
        return (parts.scheme in ('http', 'https') and bool(parts.hostname)
                and not parts.username and not parts.password)
    except ValueError:
        return False


def _scope_path(path):
    """Compare decoded URL segments; resolve dot segments before scope checks."""
    if re.search(r'%(?![0-9a-fA-F]{2})', path):
        return None
    try:
        path = unquote(path or '/', errors='strict')
    except UnicodeError:
        return None
    if '\\' in path or any(unicodedata.category(c) == 'Cc' for c in path):
        return None
    segments = []
    for segment in path.split('/'):
        if segment in ('', '.'):
            continue
        if segment == '..':
            if not segments:
                return None
            segments.pop()
        else:
            segments.append(segment)
    return '/' + '/'.join(segments)


def _reference_in_scope(native, reference):
    if not _url(native) or not _url(reference):
        return False
    origin, target = urlsplit(native), urlsplit(reference)
    if origin.hostname != target.hostname:
        return False
    base, path = _scope_path(origin.path), _scope_path(target.path)
    if base is None or path is None:
        return False
    # A query can select a different account even when host and path match.
    if origin.query:
        return base == path and origin.query == target.query
    if base.endswith(('/index.html', '/index.htm')):
        base = base.rsplit('/', 1)[0] or '/'
    return base == '/' or path == base or path.startswith(base + '/')


def _discovery(value):
    try:
        host = (urlsplit(value).hostname or '').lower().rstrip('.')
        return host == 'jinja-net.jp' or host.endswith('.jinja-net.jp')
    except (ValueError, TypeError, AttributeError):
        return False


def _redirect_authority(supplement, native):
    """Use only a continuous, recorded HTTP redirect chain as new authority."""
    if 'redirects' not in supplement:
        return native, []
    redirects = supplement['redirects']
    if not isinstance(redirects, list) or not 1 <= len(redirects) <= 6:
        return None, ['redirect evidence must contain between one and six responses']

    def request_key(url):
        parts = urlsplit(url)
        return parts.scheme, parts.netloc.lower(), _scope_path(parts.path), parts.query

    if not _url(native):
        return None, ['redirect chain has no valid acquired native URL']
    current = native
    visited = {request_key(native)}
    problems = []
    for step in redirects:
        if not isinstance(step, dict):
            return None, problems + ['invalid redirect evidence record']
        before, after = step.get('from_url'), step.get('to_url')
        if (not _url(before) or not _url(after)
                or _scope_path(urlsplit(before).path) is None
                or _scope_path(urlsplit(after).path) is None):
            return None, problems + ['invalid recorded redirect URL']
        if before != current:
            problems.append('redirect chain does not follow the acquired native href continuously')
        if step.get('status') not in (301, 302, 303, 307, 308):
            problems.append('recorded redirect status is not an allowed HTTP redirect')
        if not _hash(step.get('page_hash')) or not _date(step.get('fetched_at')):
            problems.append('redirect response hash or observation date is missing or invalid')
        if _discovery(before) or _discovery(after):
            problems.append('discovery-only directory cannot authorize a redirected shrine URL')
        key = request_key(after)
        if key in visited:
            problems.append('recorded redirect chain contains a loop')
        visited.add(key)
        current = after
    return (None if problems else current), problems


def _plain(value):
    return (isinstance(value, str) and bool(value.strip())
            and not any(unicodedata.category(c) == 'Cc' for c in value)
            and '<' not in value and '>' not in value)


def _hash(value):
    return isinstance(value, str) and bool(re.fullmatch('[0-9a-f]{64}', value))


def _date(value):
    try:
        datetime.fromisoformat(value)
        return True
    except (ValueError, TypeError):
        return False


def _raw_field(facility, field):
    supplement = facility.get('location_supplement')
    if isinstance(supplement, dict) and supplement.get('applied') is True:
        original = supplement.get('original')
        if isinstance(original, dict) and isinstance(original.get(field), str):
            return original[field]
    return facility.get(field, '')


def raw_address(facility):
    """Return the acquired address, including the original empty string."""
    return _raw_field(facility, 'address')


def location_problems(supplement, facility, source=None):
    """Validate evidence without changing or guessing any acquired field."""
    if not isinstance(supplement, dict):
        return ['invalid location supplement']
    if supplement.get('supplement_kind') == 'hyogo_cultural_building_location':
        from njd.hyogo_building_location import building_location_problems
        return building_location_problems(supplement, facility, source)
    problems = []
    if supplement.get('status') != 'verified':
        problems.append('location supplement is not verified')
    if (source or {}).get('authority_status') in ('pending', 'unconfirmed'):
        problems.append('official agency listing authority remains unconfirmed')
    if (not _plain(facility.get('name_raw'))
            or facility.get('listed_name', facility.get('name_raw')) != facility.get('name_raw')):
        problems.append('acquired facility name is missing or unresolved')
    if any(facility.get(k) for k in ('identity_review_required', 'source_conflicts', 'review_reason')):
        problems.append('facility identity still requires review')
    prior = facility.get('location_supplement', {})
    reapplied = isinstance(prior, dict) and prior.get('applied') is True
    allowed = (facility.get('status') == 'pending' and facility.get('reason') == _MISSING_LOCATION)
    allowed = allowed or (reapplied and facility.get('status') == 'verified' and not facility.get('reason'))
    if not allowed:
        problems.append('facility has a condition other than missing location')
    if supplement.get('supplement_kind') == 'hyogo_registered_municipality':
        from njd.hyogo_municipality import municipality_problems
        return problems + municipality_problems(supplement, facility)
    if raw_address(facility) != '' or _raw_field(facility, 'municipality') != '':
        problems.append('only an empty acquired address and municipality can be supplemented')
    if supplement.get('facility_id') != facility.get('id'):
        problems.append('location supplement targets another facility')
    if (not _hash(supplement.get('expected_source_hash'))
            or supplement.get('expected_source_hash') != facility.get('source_hash')):
        problems.append('location supplement is stale; acquired source changed')
    snapshot = {k: facility.get(k) for k in _SNAPSHOT_FIELDS}
    snapshot.update(address=raw_address(facility), municipality=_raw_field(facility, 'municipality'))
    if supplement.get('original') != snapshot:
        problems.append('original agency snapshot differs')
    if not _plain(supplement.get('reason')):
        problems.append('missing location supplementation reason')
    changes = supplement.get('changes')
    if not isinstance(changes, dict) or set(changes) != {'address', 'municipality'}:
        return problems + ['unsupported or missing location changes']
    if not all(_plain(changes[k]) for k in ('address', 'municipality')):
        return problems + ['location contains missing values or control/markup characters']
    address, municipality = changes['address'], changes['municipality']
    prefecture = facility.get('prefecture')
    if not _plain(prefecture) or not address.startswith(prefecture):
        problems.append('supplemental address lacks the correct prefecture prefix')
    elif municipality_from_address(address, prefecture) != municipality:
        problems.append('supplemental municipality differs from the explicit address')
    agency = supplement.get('agency_link')
    if not isinstance(agency, dict):
        problems.append('missing inspected agency link')
    else:
        if (not _url(agency.get('url')) or agency.get('url') != facility.get('listing_url')
                or agency.get('name_raw') != facility.get('name_raw')
                or not _plain(agency.get('locator')) or agency.get('locator') != facility.get('source_locator')
                or not _url(agency.get('href_raw'))
                or agency.get('href_raw') != facility.get('official_site_url')
                or agency.get('href_raw') != facility.get('native_source_id')):
            problems.append('agency link does not match the acquired name, locator and native href')
        if (not _hash(agency.get('page_hash')) or agency.get('page_hash') != facility.get('page_hash')
                or not _date(agency.get('fetched_at'))):
            problems.append('invalid agency link page hash or inspection date')
    authority, redirect_problems = _redirect_authority(supplement, facility.get('native_source_id'))
    problems.extend(redirect_problems)
    reference = supplement.get('reference')
    if not isinstance(reference, dict):
        problems.append('missing inspected shrine location reference')
    else:
        if not _reference_in_scope(authority, reference.get('url')):
            problems.append('location reference is outside the linked official shrine URL scope')
        if reference.get('source_kind') != 'official_shrine' or reference.get('location_role') != 'shrine':
            problems.append('location reference must identify the shrine, not an office or other location')
        excerpt = reference.get('excerpt')
        if (reference.get('name_raw') != facility.get('name_raw')
                or reference.get('address_raw') != address or not isinstance(excerpt, str)
                or not facility.get('name_raw') or facility['name_raw'] not in excerpt or address not in excerpt):
            problems.append('reference does not explicitly identify the exact shrine name and address')
        if (not _plain(reference.get('locator')) or not _hash(reference.get('page_hash'))
                or not _date(reference.get('fetched_at'))):
            problems.append('invalid shrine reference locator, page hash or inspection date')
    urls = [facility.get(k) for k in ('listing_url', 'official_site_url', 'native_source_id')]
    if isinstance(agency, dict):
        urls.extend(agency.get(k) for k in ('url', 'href_raw'))
    if isinstance(reference, dict):
        urls.append(reference.get('url'))
    if any(_discovery(url) for url in urls):
        problems.append('discovery-only directory cannot serve as location evidence')
    return problems


def apply_locations(data, document):
    """Apply independently stored evidence while retaining acquired snapshots."""
    if (not isinstance(document, dict) or document.get('schema_version') != 1
            or not isinstance(document.get('facilities'), dict)):
        raise ValueError('unsupported location supplement document')
    research = None
    if 'research' in document:
        container = document['research']
        if not isinstance(container, dict) or not isinstance(container.get('facilities'), dict):
            raise ValueError('unsupported location research document')
        research = container['facilities']
        if any(not isinstance(record, dict) for record in research.values()):
            raise ValueError('location research records must be objects')
    result = copy.deepcopy(data)
    supplements = document['facilities']
    if not supplements and research is None:
        return result
    if research is not None:
        for facility in result['facilities']:
            if facility['id'] in research:
                facility['location_research'] = copy.deepcopy(research[facility['id']])
    applied, pending, seen = [], [], set()
    for facility in result['facilities']:
        fid = facility['id']
        if fid not in supplements:
            continue
        seen.add(fid)
        supplement = supplements[fid]
        entries = [e for e in result['entries'] if e.get('facility_id') == fid]
        source = result['collection'].get('sources', {}).get(facility.get('source_key'), result['collection'])
        problems = location_problems(supplement, facility, source)
        building = isinstance(supplement, dict) and supplement.get('supplement_kind') == 'hyogo_cultural_building_location'
        if building:
            from njd.hyogo_building_location import building_entry_problems
            if len(entries) != 1:
                problems.append('building location requires a single original registration')
            for entry in entries:
                problems.extend(building_entry_problems(supplement, facility, entry))
        if any(e.get('identity_review_required') for e in entries):
            problems.append('entry facility identity still requires review')
        address, municipality = raw_address(facility), _raw_field(facility, 'municipality')
        record = copy.deepcopy(supplement) if isinstance(supplement, dict) else {'submitted': copy.deepcopy(supplement)}
        record['applied'] = not problems
        facility['location_supplement'] = record
        if problems:
            record['validation_problems'] = problems
            facility['address'], facility['municipality'] = address, municipality
            if facility.get('status') != 'excluded':
                facility['status'] = 'pending'
            facility['reason'] = '; '.join(problems)
            for entry in entries:
                if entry.get('status') != 'excluded':
                    entry['status'] = 'pending'
                    entry['reason'] = '; '.join(problems + ([entry['reason']] if entry.get('reason') else []))
            pending.append(fid)
            continue
        facility.update(supplement['changes'])
        facility.update(status='verified', reason='', checked_at=supplement['reference']['fetched_at'])
        for entry in entries:
            if building:
                entry.update(reading=normalize_reading(entry['reading_raw']), status='verified', reason='')
                continue
            if (entry.get('status') not in ('pending', 'verified') or entry.get('identity_review_required')
                    or entry.get('reason') not in ('', _MISSING_LOCATION, 'missing agency reading')):
                continue
            raw = entry.get('reading_raw', '')
            try:
                valid = normalize_reading(raw) == entry.get('reading')
            except (TypeError, ValueError):
                valid = False
            if valid:
                entry.update(status='verified', reason='')
            elif not raw:
                entry.update(status='pending', reason='missing agency reading')
            else:
                entry.update(status='pending', reason='acquired reading still requires evidence')
        applied.append(fid)
    result['collection']['location_supplements'] = dict(applied=sorted(applied), pending=sorted(pending),
                                                       unmatched=sorted(set(supplements) - seen))
    if research is not None:
        facility_ids = {facility['id'] for facility in result['facilities']}
        result['collection']['location_supplements']['research_unmatched'] = sorted(set(research) - facility_ids)
    return result

