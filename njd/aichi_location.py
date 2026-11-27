"""Bind the acquired Oguchi Tenjinsha row to its documented shrine parcel."""

from datetime import datetime

from njd.locations import _MISSING_LOCATION, _hash, _plain, raw_address


KIND = 'aichi_documented_street'
_API = 'https://aichi-jinjacho.or.jp/index.php/search/shrine'
_MUNICIPALITY = '丹羽郡大口町'
_NAME = '天神社'
_READING = 'てんじんしゃ'
_FACILITY_ID = 'eda99f26-cbf0-5817-89c2-8f217bf74bbf'
_ENTRY_ID = 'd6e5cbf8-11c9-5906-9cdf-506a279d0d7a'
_SOURCE_HASH = 'd11bc38ba5087519627c0abf47fe4900100903cb4d11746127fe40622c6ae0c0'
_PARTIAL_ADDRESS = '愛知県丹羽郡大口町2丁目305番地'
_VISIT_URL = 'https://owari-nagoya55.hatenablog.com/entry/2025/10/31/000000'
_VISIT_ADDRESS = '丹羽郡大口町替地2-305'
_CORPORATE_NUMBER = '3180005009256'
_REGISTRY_URL = 'https://www.houjin-bangou.nta.go.jp/henkorireki-johoto.html?selHouzinNo=' + _CORPORATE_NUMBER
_OFFICE_ADDRESS = '愛知県丹羽郡大口町替地２丁目３０５番地'
_API_ROWS = {
    '297f0651-b055-4a25-a48d-1cb2ff73e202': {
        'name': _NAME, 'kana': _READING, 'pref': '愛知県', 'city': _MUNICIPALITY,
        'addr': '', 'house_num': '2丁目305番地',
    },
    '96a1005c-5242-4978-93d9-aeadbcb6a1ce': {
        'name': _NAME, 'kana': 'てんじんじゃ', 'pref': '愛知県', 'city': _MUNICIPALITY,
        'addr': '秋田', 'house_num': '3',
    },
}
_TARGET_ID = '297f0651-b055-4a25-a48d-1cb2ff73e202'
_ORIGINAL = dict(name_raw=_NAME, address='', municipality=_MUNICIPALITY, listing_url=_API,
                 official_site_url=None, native_source_id=_TARGET_ID)


def _matches(record, **fields):
    return isinstance(record, dict) and all(key in record and record[key] == value for key, value in fields.items())


def _observation_time(value):
    try:
        observed = datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None
    return observed if observed.tzinfo is not None else None


def _excerpt_has(record, *facts):
    excerpt = record.get('excerpt')
    return _plain(excerpt) and all(text in excerpt for text in facts)


def aichi_location_problems(supplement, facility):
    if (not _matches(facility, id=_FACILITY_ID, source_key='aichi', prefecture_code='23',
                     prefecture='愛知県', municipality=_MUNICIPALITY, listing_url=_API,
                     official_site_url=None, native_source_id=_TARGET_ID, name_raw=_NAME,
                     listed_name=_NAME, source_hash=_SOURCE_HASH, address_raw=_PARTIAL_ADDRESS)
            or not _hash(facility.get('page_hash')) or raw_address(facility) != ''
            or facility.get('address') not in ('', _VISIT_ADDRESS)
            or not _plain(facility.get('source_locator'))
            or _TARGET_ID not in facility['source_locator']):
        return ['Oguchi location requires the original Aichi API facility and partial address']
    if (not _matches(supplement, supplement_kind=KIND, status='verified', facility_id=_FACILITY_ID,
                     entry_id=_ENTRY_ID, expected_source_hash=_SOURCE_HASH, original=_ORIGINAL,
                     changes={'address': _VISIT_ADDRESS})
            or not _plain(supplement.get('reason'))):
        return ['Oguchi location must preserve the original snapshot and change only the address']

    recheck = supplement.get('agency_recheck')
    if (not _matches(recheck, url=_API, request_method='POST',
                     request_body={'addr': '大口町', 'limit': -1}, retrieved_rows=20,
                     page_hash='2ce3ac22a94dc8313d0095bb8a58a3cc28184162c9a8639e3e0b1869908569d0')
            or not _plain(recheck.get('locator'))):
        return ['Oguchi location requires the complete inspected municipal API response']
    same_name_rows = recheck.get('corresponding_name_rows')
    expected_rows = [fields | {'id': source_id} for source_id, fields in _API_ROWS.items()]
    if (not isinstance(same_name_rows, list) or len(same_name_rows) != len(expected_rows)
            or any(row not in same_name_rows for row in expected_rows)):
        return ['Oguchi location must distinguish the two original same-name API rows']

    visit = supplement.get('reference')
    if (not _matches(visit, url=_VISIT_URL,
                     page_hash='b44adb1f042d13ca1cc5f2431c32adc192bc58d2da0aa1d044c19b088615ffea',
                     source_kind='independent_visit_article', location_role='shrine',
                     name_raw=_NAME, address_raw=_VISIT_ADDRESS)
            or not _plain(visit.get('locator')) or not _excerpt_has(visit, _NAME, '所在地', _VISIT_ADDRESS)):
        return ['Oguchi location requires the inspected on-site article and its printed full shrine address']
    registry = supplement.get('registry_reference')
    if (not _matches(registry, url=_REGISTRY_URL,
                     page_hash='f1d7d64aa9905c8989dc629de98c224a38a4e0c2e076406e07cb93779ea7571d',
                     source_kind='government_corporate_profile', location_role='principal_office',
                     name_raw=_NAME, corporate_number=_CORPORATE_NUMBER, address_raw=_OFFICE_ADDRESS)
            or not _plain(registry.get('locator'))
            or not _excerpt_has(registry, '最新情報', _NAME, _CORPORATE_NUMBER, _OFFICE_ADDRESS)):
        return ['Oguchi location requires the current corporate profile and its identical complete parcel']

    acquired = _observation_time(facility.get('fetched_at'))
    checked = _observation_time(recheck.get('checked_at'))
    visited = _observation_time(visit.get('fetched_at'))
    registered = _observation_time(registry.get('checked_at'))
    recorded = _observation_time(supplement.get('recorded_at'))
    if (None in (acquired, checked, visited, registered, recorded)
            or not acquired <= min(checked, visited, registered)
            or not max(checked, visited, registered) <= recorded):
        return ['Oguchi location requires dated observations consistent with the acquired API row']
    return []


def aichi_location_entry_problems(facility, entries):
    """Allow the location proof to resolve only the original agency reading."""
    if len(entries) == 1 and isinstance(entries[0], dict):
        entry = entries[0]
        status = (entry.get('status'), entry.get('reason'))
        if (status in (('pending', _MISSING_LOCATION), ('verified', ''))
                and _matches(entry, id=_ENTRY_ID, facility_id=_FACILITY_ID, name_raw=_NAME, surface=_NAME,
                             page_hash=facility.get('page_hash'), source_hash=_SOURCE_HASH,
                             listing_url=_API, reading_url=_API, reading_source_kind='agency',
                             reading_raw=_READING, reading=_READING)
                and entry.get('source_reading_raw', _READING) == _READING
                and not entry.get('identity_review_required')):
            return []
    return ['Oguchi location requires the single acquired Aichi registration and its original full reading']
