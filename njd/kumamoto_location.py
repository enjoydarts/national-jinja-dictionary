"""Bind a Kumamoto agency search-area row to a documented shrine site."""
from dataclasses import dataclass
import re
from urllib.parse import urlsplit

from njd.corporate_aza import _addresses, _TOWN_TEXT
from njd.locations import _date, _hash, _plain, _raw_field, _SNAPSHOT_FIELDS, _url, raw_address


KIND = 'kumamoto_documented_shrine_site'
_AGENCY = 'kumamotokenjinjacho.jp'
_PREFECTURE_SITE = 'www.pref.kumamoto.jp'
_UBUYAMA_GUIDE = 'https://www.ubuyama-v.jp/section/iju/ubuyama_guide.pdf'
_MUNICIPAL_SITES = {
    '阿蘇郡小国町': 'www.town.kumamoto-oguni.lg.jp',
    '阿蘇郡高森町': 'www.town.kumamoto-takamori.lg.jp',
    '阿蘇郡南阿蘇村': 'www.vill.minamiaso.lg.jp',
    '阿蘇郡産山村': 'www.ubuyama-v.jp',
}
_REGISTER_URLS = {
    'https://www.houjin-bangou.nta.go.jp/download/zenken/index.html',
    'https://www.houjin-bangou.nta.go.jp/download/sabun/index.html',
}


_NISHIHARA = '阿蘇郡西原村'
_NISHIHARA_HOST = 'shirayamahime.jimdofree.com'
_HAKUSAN_URL = 'https://shirayamahime.jimdofree.com/'
_HAKUSAN_HASH = 'b7e36f19a7acfe84ee42f24ad4b0409f9349806787d42b6a8f620cb271bd5468'
_HAKUSAN_LOCATOR = 'h1#cc-m-header-12245966891 と「鎮座地」の実欄'
_HAKUSAN_ADDRESS = '熊本県阿蘇郡西原村大字河原字門出750番地'
_AFFILIATES_URL = _HAKUSAN_URL + '%E5%85%BC%E5%8B%99%E7%A5%9E%E7%A4%BE-%E6%9D%91%E5%86%85/'
_AFFILIATES_HASH = '466ef624a6c4c76a3007e30f7ad28a36a5e6ed62f3cb8a78daea160f190550c5'
_NTA_DETAIL = 'https://www.houjin-bangou.nta.go.jp/henkorireki-johoto.html?selHouzinNo='
_NTA_ADDRESS_CELL = '本店又は主たる事務所の所在地'
_FULLWIDTH_DIGITS = str.maketrans('0123456789', '０１２３４５６７８９')


@dataclass(frozen=True)
class _NishiharaRow:
    facility_id: str
    entry_id: str
    source_hash: str
    locality: str
    parcel: str
    table_row: int
    name_cell_padding: str
    agency_hash: str
    corporation: str
    office_hash: str


# The official shrine site establishes these five individually reviewed rows.
_NISHIHARA_ROWS = {
    '白山姫神社': _NishiharaRow(
        '205f8e8f-c4ba-5767-987d-c5d8584f0a77', 'eff3a564-4539-5b47-8a6a-7e53c5d9bcfb',
        'f52164800910b5d9f987119cbd8cbf2271e7d94866cfcb6aef7ab7cc4c8f90aa',
        '河原', '750', 0, '',
        'f89bb7204c2ac6579a738e400b197cac6ab10a1d5ccb417a4025146a078dba14',
        '4330005002608', 'e60675c97eebfc2af71ec45036ff1f4e66ce20192bd1617cdec42d662c7c9b36',
    ),
    '小森神社': _NishiharaRow(
        'b0b7d762-7f68-56c3-802d-54e65e528558', '0c7889a7-7c2f-5a5d-8ac0-68ce5d9e808b',
        '3f2010d69dd363de508adf1b052c892547366e47757db440176a921d308ce54a',
        '小森', '386', 2, '\u3000',
        '566991bcb74e8391224aed6a4dd532f6b2aaa14d68ba341275c0d3f1f8ffaec9',
        '2330005002601', '40b056c61d27ce67963ddb425d6eed66fe83e43c56fb92459dda448d3d447bd6',
    ),
    '龍神社': _NishiharaRow(
        '05448cbf-3e38-59f7-a41c-e3211091f2e0', '5c090955-4cdd-5a42-a815-c1872660a3a5',
        '38742db592f4a0f4807d8e3f08256465c7f6db2bae9d1fb6e75031d6411a6b92',
        '布田', '1717', 4, '\u3000\u3000\u3000\u3000',
        '05936f7aaf460b7bbcb4361b0797e551ca09bf3b286faf984f455315a07cc0fe',
        '4330005002632', '121207dd59bac1472466c9187900908844de867f9ead9f240bd4eb7db6ccf753',
    ),
    '鳥子三之宮神社': _NishiharaRow(
        '83b9836a-24f7-5fa6-9c72-28bc841e9ae7', '960d0392-9dbb-59d3-b405-165846c01f20',
        'bb552e85bf81c8632adf03cdf77069c8775d39f4d02f2f4c9038bd96644a1845',
        '鳥子', '2608', 5, '',
        '45c01ba9f382d4654ef3e99d1dbe48d6f624d084ae54c4c1a647ee0a8e9b991f',
        '8330005002612', 'e5d02fe85681c6126b1b52064f9eb43e25ca849f2488d3ea6612fcaf04ada826',
    ),
    '宮山神社': _NishiharaRow(
        'a7c2aacf-58e5-5291-bb3b-2b3e5e151b58', '420f6712-46a1-59c6-8eae-1b0c2ef4fc19',
        'b16a993b2533cc190ec580acedb1cbcebcbab994db98d2109b33ca454a16746f',
        '宮山', '439', 6, '',
        'bd70be5d66bef6918ed58f6345634e5093f444765e5e40a0a255fd7ae1db2d2f',
        '1330005002627', 'ed3abd1eb4d47359b5fde095ea2a3c369e4c819ad946567d96f4205eb5efc939',
    ),
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


def _matches_receipt(record, **fields):
    return (_source_host(record, 'fetched_at') is not None
            and all(record.get(key) == value for key, value in fields.items()))


def _kadode_locality_proven(supplement):
    hierarchy = supplement.get('cadastral_hierarchy_reference')
    if not _matches_receipt(
        hierarchy, url='https://www.vill.nishihara.kumamoto.jp/kiji003204/index.html',
        page_hash='3ae2c201922421004eeb1b25c369702bf85fa402a73ce21630d1d60de52cfaae',
        locator='調査地区の概要、平成13年度行の大字・小字列', role='municipal_cadastral_hierarchy',
        oaza_raw='河原', koaza_raw='門出', koaza_cell_raw='門出・古閑・平の一部',
        excerpt='平成13年度 ／ 河原 ／ 門出・古閑・平の一部',
    ):
        return False
    # The village's other parcel documents the locality hierarchy only.
    parcel = supplement.get('locality_reference')
    other_address = '熊本県阿蘇郡西原村大字河原字門出９１８番４'
    return (_matches_receipt(
        parcel, url='https://www.vill.nishihara.kumamoto.jp/kiji0031018/3_1018_1033_up_kzkb3zs0.pdf',
        page_hash='95bb337e3ec58905054dff5922c5c00a705eb1978ac00ba2c72ed355e1ad0333',
        locator='物件番号2の売払物件・地番欄', role='independent_hierarchy_other_parcel',
        oaza_raw='河原', koaza_raw='門出', address_raw=other_address, pdf_page=1,
    ) and isinstance(parcel.get('excerpt'), str) and other_address in parcel['excerpt'])


def _nishihara_problems(supplement, facility, office, raw, municipality):
    name = facility.get('name_raw')
    row = _NISHIHARA_ROWS.get(name) if isinstance(name, str) else None
    if (row is None or municipality != _NISHIHARA or facility.get('id') != row.facility_id
            or facility.get('source_hash') != row.source_hash or supplement.get('entry_id') != row.entry_id
            or raw != '阿蘇郡' + row.locality + row.parcel or office.get('corporate_number') != row.corporation):
        return ['Nishihara location is outside the five reviewed source rows']
    current_agency = supplement.get('agency_recheck')
    if not _matches_receipt(
        current_agency, url=facility['native_source_id'], page_hash=row.agency_hash,
        locator='氏神詳細の社名見出し・お住まいの地域欄', role='agency_search_area',
        name_raw=name, address_label='お住まいの地域', area_raw=raw,
    ):
        return ['Nishihara location needs the current original agency residential-area field']
    current_office = supplement.get('current_registry_reference')
    office_locality = '大字' + row.locality
    if name == '白山姫神社':
        office_locality += '字門出'
    office_address = '熊本県' + _NISHIHARA + office_locality + row.parcel.translate(_FULLWIDTH_DIGITS) + '番地'
    if (office.get('location_role') != 'principal_office' or office.get('address_raw') != office_address
            or not _matches_receipt(
        current_office, url=_NTA_DETAIL + row.corporation, page_hash=row.office_hash,
        locator='最新情報の商号又は名称／本店又は主たる事務所の所在地',
        corporate_number=row.corporation, name_raw=name, address_raw=office_address,
        location_role='principal_office', address_role='corporation_principal_office',
        address_column_raw=_NTA_ADDRESS_CELL,
    )):
        return ['Nishihara location needs the matching original and current registered office fields']

    site = supplement['reference']
    if site.get('name_raw') != name or site.get('address_field') != '鎮座地' or site.get('source_publisher') != '白山姫神社':
        return ['Nishihara location needs the official shrine name and enshrinement address field']
    if name == '白山姫神社':
        if (not _matches_receipt(
            site, url=_HAKUSAN_URL, page_hash=_HAKUSAN_HASH, locator=_HAKUSAN_LOCATOR,
            address_raw=_HAKUSAN_ADDRESS, source_kind='nishihara_shrine_site',
        ) or not _kadode_locality_proven(supplement)):
            return ['Hakusan Hime location needs its official full parcel and the village cadastral hierarchy']
        return []
    scope = site.get('scope_reference')
    if (not _matches_receipt(
        site, url=_AFFILIATES_URL, page_hash=_AFFILIATES_HASH,
        locator=f'西原村内の兼務神社表 tr[{row.table_row}] 神社名・鎮座地セル',
        source_kind='nishihara_affiliated_shrine_table', name_cell_raw=name + row.name_cell_padding,
        address_raw='西原村' + row.locality + row.parcel + '番地',
    ) or not _matches_receipt(
        scope, url=_HAKUSAN_URL, page_hash=_HAKUSAN_HASH, locator=_HAKUSAN_LOCATOR,
        name_raw='白山姫神社', municipality_raw='熊本県' + _NISHIHARA,
        excerpt='鎮座地　' + _HAKUSAN_ADDRESS,
    )):
        return ['Nishihara location needs the exact affiliate row and its publisher municipality context']
    return []


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
    changes = supplement.get('changes')
    municipality = changes.get('municipality') if isinstance(changes, dict) else None
    municipal_site = _MUNICIPAL_SITES.get(municipality) if isinstance(municipality, str) else None
    nishihara = site_host == _NISHIHARA_HOST
    if not site_host or site_host not in (_PREFECTURE_SITE, municipal_site, _NISHIHARA_HOST):
        return ['Kumamoto location needs an inspected official physical shrine address']
    address, site_name, excerpt = (site.get(key) for key in ('address_raw', 'name_raw', 'excerpt'))
    if (site.get('location_role') != 'shrine'
            or (not nishihara and site.get('source_kind') not in ('prefectural_shrine_tourism', 'municipal_shrine_tourism'))
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
    if nishihara:
        problems = _nishihara_problems(supplement, facility, ref, raw, municipality)
        if problems:
            return problems
    locality = re.match(r'[^0-9０-９]+', street.removeprefix('大字'))
    if not locality or not _TOWN_TEXT.fullmatch(locality[0]):
        return ['Kumamoto location needs a literal whole locality and parcel']
    places = {locality[0], '大字'+locality[0]}
    registered = _addresses(street, {''}, places)
    site_places = places
    site_prefixes = {municipality, '熊本県'+municipality}
    agency_places = places
    if site.get('url') == _UBUYAMA_GUIDE:
        # The printed guide places a space between the locality and the parcel.
        site_places = places | {place + ' ' for place in places}
    if nishihara:
        if name == '白山姫神社':
            # The agency printed the larger locality without the documented koaza.
            agency_places = {'河原'}
        else:
            # Only the reviewed rows in this table print the village without the county.
            site_prefixes.add('西原村')
    observed = _addresses(address, site_prefixes, site_places)
    listed = _addresses(raw, {county[1], '熊本県'+county[1]}, agency_places)
    numbers = [{parcel for _, parcel in group} for group in (registered, observed, listed)]
    if len(numbers[0]) != 1 or numbers[0] != numbers[1] or numbers[0] != numbers[2]:
        return ['Kumamoto agency area, shrine site and registered office must have the same entire parcel']
    return []
