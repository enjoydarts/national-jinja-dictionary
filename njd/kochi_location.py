"""Reconcile two Kochi agency search rows with their own full-address cards."""
from urllib.parse import urlsplit

from njd.locations import _SNAPSHOT_FIELDS, _date, _hash, _plain, _raw_field, _url, raw_address


KIND = 'kochi_agency_documented_municipality'
_AGENCY = 'www.kochi-jinjyacho.com'
_ACQUIRED_CONTEXT = '高知県高岡郡'
_MUNICIPALITY = '高知市'
_CASES = {
    'bcf2b020-e99b-41cd-984f-b6f0be9b4a71': (
        '朝倉神社', '朝倉丙2100番地ｲ', '高知県高知市朝倉丙2100-イ',
        'https://asakurajinja.yamanoha.com/', '5490005000776', '高知県高知市朝倉丙２１００番地イ',
    ),
    '3dd3fee8-131e-495b-a327-b72789618382': (
        '土佐神社', '一宮しなね二丁目16番1号', '高知県高知市一宮しなね2-16-1',
        'https://tosajinja.com/', '5490005001196', '高知県高知市一宮しなね２丁目１６番１号',
    ),
}


def _observed(record, **fields):
    return (isinstance(record, dict) and _hash(record.get('page_hash'))
            and _date(record.get('fetched_at')) and _plain(record.get('locator'))
            and all(record.get(key) == value for key, value in fields.items()))


def _identifies_site(record):
    excerpt = record.get('excerpt')
    return (isinstance(excerpt, str) and record['name_raw'] in excerpt
            and record['address_raw'] in excerpt)


def kochi_location_problems(supplement, facility):
    native = facility.get('native_source_id')
    case = _CASES.get(native) if isinstance(native, str) else None
    listing = facility.get('listing_url')
    if (not case or facility.get('source_key') != 'kochi' or facility.get('prefecture_code') != '39'
            or facility.get('prefecture') != '高知県' or not _url(listing)
            or urlsplit(listing).netloc != _AGENCY or urlsplit(listing).scheme != 'https'):
        return ['Kochi location requires the documented agency search row']
    name, street, address, shrine_href, number, registered = case
    acquired = raw_address(facility)
    digest = facility.get('source_hash')
    snapshot = {key: _raw_field(facility, key) if key == 'municipality' else facility.get(key)
                for key in _SNAPSHOT_FIELDS}
    snapshot['address'] = acquired
    if (facility.get('name_raw') != name or acquired != _ACQUIRED_CONTEXT + street
            or snapshot['municipality'] != '' or not _hash(digest)
            or supplement.get('facility_id') != facility.get('id')
            or supplement.get('expected_source_hash') != digest or supplement.get('original') != snapshot
            or supplement.get('changes') != {'address': address, 'municipality': _MUNICIPALITY}
            or not _plain(supplement.get('reason'))):
        return ['Kochi location requires the acquired name, whole address and source hash']

    row = supplement.get('agency_cms_reference')
    card = supplement.get('reference')
    if (not _observed(row, url=listing, name_raw=name, native_source_id=native, source_kind='agency',
                      address_context_raw=_ACQUIRED_CONTEXT, address_raw=street, branch_raw='高知市支部')
            or not _observed(card, url=listing, name_raw=name, source_kind='agency', location_role='shrine',
                             address_raw=address, href_raw=shrine_href, page_hash=row['page_hash'],
                             fetched_at=row['fetched_at'])
            or card['locator'] == row['locator'] or not _identifies_site(card)
            or not _hash(row.get('institutional_phone_sha256'))
            or row['institutional_phone_sha256'] != card.get('institutional_phone_sha256')):
        return ['Kochi search row and same-page shrine card do not identify the same whole location']

    registry = supplement.get('registry_reference')
    if (not _observed(registry, name_raw=name, address_raw=registered, corporate_number=number,
                      location_role='principal_office',
                      url='https://www.houjin-bangou.nta.go.jp/henkorireki-johoto.html?selHouzinNo=' + number)
            or not _identifies_site(registry)):
        return ['Kochi location requires an inspected registry entry for the same whole location']
    return []
