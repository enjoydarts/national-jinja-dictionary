"""Bind a Kumamoto agency search-area row to a documented shrine site."""
import re
from urllib.parse import urlsplit

from njd.corporate_aza import _addresses, _TOWN_TEXT
from njd.locations import _date, _hash, _plain, _raw_field, _SNAPSHOT_FIELDS, _url, raw_address


KIND = 'kumamoto_documented_shrine_site'
_AGENCY = 'kumamotokenjinjacho.jp'
_PREFECTURE_SITE = 'www.pref.kumamoto.jp'
_TOWN_SITE = 'www.town.kumamoto-oguni.lg.jp'
_REGISTER_URLS = {
    'https://www.houjin-bangou.nta.go.jp/download/zenken/index.html',
    'https://www.houjin-bangou.nta.go.jp/download/sabun/index.html',
}


def _source_host(record, date_field):
    if (not isinstance(record, dict) or not _url(record.get('url'))
            or not _hash(record.get('page_hash')) or not _date(record.get(date_field))
            or not _plain(record.get('locator'))):
        return None
    url = urlsplit(record['url'])
    return url.netloc if url.scheme == 'https' else None


def _explicit_alias(reference, name, site_name):
    if _source_host(reference, 'checked_at') not in ('www.env.go.jp', 'www.gsj.jp'):
        return False
    excerpt = reference.get('excerpt')
    return (reference.get('name_raw') == name and reference.get('alias_raw') == site_name
            and _plain(excerpt)
            and excerpt in (site_name+'('+name+')', name+'(通称，'+site_name+')'))


def kumamoto_location_problems(supplement, facility):
    name = facility.get('name_raw')
    raw = raw_address(facility)
    native = facility.get('native_source_id')
    if (facility.get('source_key') != 'kumamoto' or facility.get('prefecture_code') != '43'
            or facility.get('prefecture') != '熊本県' or not _plain(raw)
            or _raw_field(facility, 'municipality') != '' or not _url(native)
            or urlsplit(native).netloc != _AGENCY or not urlsplit(native).path.startswith('/patron-god/')):
        return ['Kumamoto location requires a county-only agency search-area row']
    snapshot = {key: facility.get(key) for key in _SNAPSHOT_FIELDS}
    snapshot.update(address=raw, municipality='')
    digest = facility.get('source_hash')
    if (supplement.get('original') != snapshot or supplement.get('facility_id') != facility.get('id')
            or not _hash(digest) or supplement.get('expected_source_hash') != digest
            or not _plain(supplement.get('reason'))):
        return ['Kumamoto location must preserve the acquired row and its hash']
    agency = supplement.get('agency_link')
    expected = dict(url=facility.get('listing_url'), href_raw=native, name_raw=name,
                    locator=facility.get('source_locator'), page_hash=facility.get('page_hash'),
                    address_label='お住まいの地域', area_raw=raw)
    if (_source_host(agency, 'fetched_at') != _AGENCY
            or any(agency.get(key) != value for key, value in expected.items())):
        return ['Kumamoto agency witness differs from the original search-area row']

    site = supplement.get('reference')
    site_host = _source_host(site, 'fetched_at')
    if site_host not in (_PREFECTURE_SITE, _TOWN_SITE):
        return ['Kumamoto location needs an inspected official physical shrine address']
    changes = supplement.get('changes')
    address, site_name, excerpt = (site.get(key) for key in ('address_raw', 'name_raw', 'excerpt'))
    if (site.get('location_role') != 'shrine' or site.get('source_kind') not in
            ('prefectural_shrine_tourism', 'municipal_shrine_tourism')
            or not all(_plain(value) for value in (address, site_name, excerpt))
            or address not in excerpt or site_name not in excerpt
            or not isinstance(changes, dict) or set(changes) != {'address', 'municipality'}
            or changes['address'] != address or not _plain(changes['municipality'])
            or (site_name != name and not _explicit_alias(supplement.get('alias_reference'), name, site_name))):
        return ['Kumamoto location must identify the same shrine and retain the printed site address']

    ref = supplement.get('registry_reference')
    if (not isinstance(ref, dict) or ref.get('url') not in _REGISTER_URLS
            or not _hash(ref.get('page_hash')) or not _date(ref.get('checked_at'))
            or type(ref.get('csv_row')) is not int or ref['csv_row'] < 1):
        return ['Kumamoto location requires an official registry row']
    fields = ref.get('source_fields')
    state = ref.get('registry_state_proof')
    municipality = changes['municipality']
    county = re.fullmatch(r'([^0-9]+?郡)[^郡0-9]+[町村]', municipality)
    number = ref.get('corporate_number')
    if (not county or not isinstance(fields, dict) or not isinstance(state, dict)
            or not isinstance(number, str) or not re.fullmatch('[0-9]{13}', number)
            or state.get('unique_active_corporate_number') != number
            or type(state.get('full_address_active_corporations')) is not int
            or state['full_address_active_corporations'] != 1):
        return ['Kumamoto location lacks a unique active same-name registered office']
    expected = dict(name=name, corporateNumber=number, prefectureCode='43', prefectureName='熊本県',
                    cityName=municipality, kind='399', latest='1', hihyoji='0', closeDate='',
                    nameImageId='', addressImageId='')
    street = fields.get('streetNumber')
    if (any(fields.get(key) != value for key, value in expected.items())
            or fields.get('process') == '99' or not _plain(street)
            or ref.get('address_raw') != '熊本県'+municipality+street):
        return ['Kumamoto registered office differs from the active literal CSV row']
    locality = re.match(r'[^0-9０-９]+', street.removeprefix('大字'))
    if not locality or not _TOWN_TEXT.fullmatch(locality[0]):
        return ['Kumamoto location needs a literal whole locality and parcel']
    places = {locality[0], '大字'+locality[0]}
    registered = _addresses(street, {''}, places)
    observed = _addresses(address, {municipality, '熊本県'+municipality}, places)
    listed = _addresses(raw, {county[1], '熊本県'+county[1]}, places)
    numbers = [{parcel for _, parcel in group} for group in (registered, observed, listed)]
    if len(numbers[0]) != 1 or numbers[0] != numbers[1] or numbers[0] != numbers[2]:
        return ['Kumamoto agency area, shrine site and registered office must have the same entire parcel']
    return []
