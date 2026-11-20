"""Compare registered parcels using literal components of an official town row."""
import re
from urllib.parse import urlsplit

from njd.locations import _date, _hash, _plain, _url


TOWN_ARCHIVE = 'https://data.address-br.digital.go.jp/mt_town/mt_town_all.csv.zip'
TOWN_TERMS = 'https://www.digital.go.jp/policies/base_registry_address_tos'
PROOF_KIND = 'registered_abr_town_spelling'
_FUKUCHIYAMA_ADDRESS = 'https://www.city.fukuchiyama.lg.jp/soshiki/5/64145.html'
_KYOTO_PARCELS = 'https://habs.rad.naro.go.jp/spatial_data/amxpoly47/amxpoly_2022_26'
_PARCEL_TERMS = 'https://www.tellusxdp.com/docs/api-service/aigid-moj/tos.pdf'
_MIYAZU_CULTURAL_INVENTORY = 'https://kinki.env.go.jp/recycle/H29moderu_keikaku_tangoG.pdf'
_NANKOKU_LOCALITY_REPORT = (
    'https://sitereports.nabunken.go.jp/files/attach/13/13183/'
    '10246_1_%E5%8D%97%E5%9B%BD%E5%B8%82%E3%81%AE%E9%81%BA%E8%B7%A1.pdf'
)
_CHIKUMA_CULTURAL_REPORT = (
    'https://www.pref.nagano.lg.jp/bunkashinko/kyoiku/bunka/documents/bunkazaiyouran-no35-2026.pdf'
)
_NAGANO_OFFICE_REGISTER = (
    'https://www.pref.nagano.lg.jp/ken-manabi/kensei/shichoson/hojin/shukyo/documents/meibor7_1231.pdf'
)
_KYOTO_SITE_HOSTS = {
    '福知山市': {'www.city.fukuchiyama.lg.jp', 'www.pref.kyoto.jp'},
    '舞鶴市': {'www.city.maizuru.kyoto.jp', 'www.pref.kyoto.jp'},
    '宮津市': {'www.city.miyazu.kyoto.jp', 'www.pref.kyoto.jp', 'www.env.go.jp',
              'kinki.env.go.jp'},
}
_WIDTH = str.maketrans('０１２３４５６７８９', '0123456789')
_PARCEL = re.compile(r'([0-9]+(?:(?:-|番(?:地)?の?|の)[0-9]+)*)(?:番地|番|号)?')
_TOWN_TEXT = re.compile(r'[\u3400-\u9fff々〆ヶぁ-ゖァ-ヺー]*')


def _town_spellings(town, markers):
    if not town:
        return {''}
    core = town
    for marker in markers:
        if core.startswith(marker):
            core = core.removeprefix(marker)
            break
    if not core:
        return {town}
    return {core, *(marker + core for marker in markers)}


def _addresses(raw, prefixes, localities):
    pairs = set()
    for prefix in prefixes:
        if not raw.startswith(prefix):
            continue
        street = raw[len(prefix):]
        for locality in localities:
            if not street.startswith(locality):
                continue
            number = _PARCEL.fullmatch(street[len(locality):].translate(_WIDTH))
            if number:
                pairs.add((locality, re.sub(r'番(?:地)?の?|の', '-', number[1])))
    return pairs


def _documented_fukuchiyama_parcel(context, oaza, parcel):
    explanation = context.get('municipality_explanation')
    map_ref = context.get('parcel_map')
    if (not isinstance(explanation, dict) or explanation.get('url') != _FUKUCHIYAMA_ADDRESS
            or not _date(explanation.get('checked_at')) or not _hash(explanation.get('page_hash'))
            or not isinstance(map_ref, dict) or map_ref.get('url') != _KYOTO_PARCELS + '.fgb'
            or map_ref.get('catalog_url') != _KYOTO_PARCELS + '.html'
            or map_ref.get('license_url') != _PARCEL_TERMS
            or not _date(map_ref.get('checked_at')) or not _hash(map_ref.get('page_hash'))
            or type(map_ref.get('matching_features')) is not int or map_ref['matching_features'] != 1):
        return False
    feature = map_ref.get('feature')
    if (not isinstance(feature, dict) or not _hash(feature.get('sha256'))
            or type(feature.get('index')) is not int or feature['index'] < 0
            or type(feature.get('byte_offset')) is not int or feature['byte_offset'] < 0):
        return False
    fields = feature.get('fields')
    if not isinstance(fields, dict):
        return False
    expected = {'市区町村コード': '26201', '市区町村名': '福知山市', '大字名': oaza, '小字名': ''}
    number = fields.get('地番')
    return (all(fields.get(key) == value for key, value in expected.items())
            and isinstance(number, str) and number.translate(_WIDTH) == parcel)


def _public_shrine_parcel_matches(site, name, city, oaza_spellings, koaza, parcel):
    if (not isinstance(site, dict) or not _url(site.get('url'))
            or not _hash(site.get('page_hash')) or not _date(site.get('checked_at'))
            or site.get('source_kind') != 'government_shrine_site'
            or any(not _plain(site.get(key)) for key in ('item_raw', 'address_raw', 'locator', 'excerpt'))):
        return False
    url = urlsplit(site['url'])
    item, address, excerpt = (site[key] for key in ('item_raw', 'address_raw', 'excerpt'))
    if (url.scheme != 'https' or url.netloc not in _KYOTO_SITE_HOSTS.get(city, ())
            or item not in (name, name + '本殿') or item not in excerpt or address not in excerpt):
        return False
    prefixes = {city, '京都府' + city}
    scope = site.get('scope_raw')
    header = site.get('location_header_raw')
    if header in ('所在地', '所 在 地'):
        if isinstance(scope, str) and scope.startswith(city + '内の'):
            prefixes.add('')
    elif not (header == '住所' and site['url'] == _MIYAZU_CULTURAL_INVENTORY
              and city == '宮津市' and site.get('item_type_raw') == '寺社'):
        return False
    localities = {a + k for a in oaza_spellings for k in ('', koaza, '小字' + koaza)}
    observed = _addresses(address, prefixes, localities)
    return len(observed) == 1 and next(iter(observed))[1] == parcel


def _nankoku_koaza_matches(witness, oaza, koaza):
    if (not isinstance(witness, dict) or witness.get('url') != _NANKOKU_LOCALITY_REPORT
            or not _date(witness.get('checked_at')) or not _hash(witness.get('page_hash'))
            or witness.get('pdf_page') != 51
            or witness.get('address_expanded_for_comparison') != '南国市' + oaza + '字' + koaza):
        return False
    row = witness.get('location_row')
    context = witness.get('ditto_context')
    if not isinstance(row, dict) or not isinstance(context, list):
        return False
    rows = {item.get('map_no'): item.get('address_raw') for item in context
            if isinstance(item, dict) and isinstance(item.get('map_no'), str)}
    if rows.get('260') != '南国市稲生字蛸の森':
        return False
    if (oaza, koaza) == ('十市', '溝本'):
        return (rows.get('261') == '〝 十市字\n三ツ城・里改田字三ツ城他'
                and row.get('map_no') == '269' and row.get('address_raw') == '〝 〝 字' + koaza)
    return ((oaza, koaza) == ('前浜', '季重') and row.get('map_no') == '284'
            and row.get('address_raw') == '〝 前浜字' + koaza)


def _chikuma_koaza_matches(context, name, oaza, koaza, parcel):
    locality = context.get('reference')
    office = context.get('office_register')
    for evidence, url in ((locality, _CHIKUMA_CULTURAL_REPORT), (office, _NAGANO_OFFICE_REGISTER)):
        if (not isinstance(evidence, dict) or evidence.get('url') != url
                or not _date(evidence.get('checked_at')) or not _hash(evidence.get('page_hash'))):
            return False
    return (locality.get('pdf_page') == 49
            and (oaza, koaza) == ('大字杭瀬下', '東沖')
            and locality.get('archaeological_site_address_raw') == '千曲市大字杭瀬下字東沖44番3他'
            and office.get('address_role') == 'corporation_principal_office'
            and office.get('address_field') == '事務所所在地'
            and office.get('municipality_raw') == '千曲市' and office.get('name_raw') == name
            and _plain(office.get('address_field_raw'))
            and _addresses(office['address_field_raw'], {''}, {oaza + koaza}) == {(oaza + koaza, parcel)})


def registered_town_matches(ref, facility, entry, changes):
    from njd.corporate import BASE, DAILY_ARCHIVE, _reading, bound_registered_shrine_name

    proof = ref['address_identity_proof']
    if (set(changes) != {'reading'} or entry.get('status') == 'excluded'
            or ref.get('source_kind') != 'government_corporate_register'
            or ref.get('url') not in (BASE + '/download/zenken/index.html', DAILY_ARCHIVE)):
        return False
    agency = facility.get('address')
    digest = entry.get('source_hash')
    csv_row = ref.get('csv_row')
    if (not isinstance(agency, str) or not _hash(digest) or facility.get('source_hash') != digest
            or proof.get('agency_address_raw') != agency or proof.get('expected_source_hash') != digest
            or not _hash(ref.get('page_hash')) or proof.get('registry_page_hash') != ref['page_hash']
            or type(csv_row) is not int or csv_row < 1 or proof.get('registry_csv_row') != csv_row):
        return False
    master = proof.get('town_master')
    if (not isinstance(master, dict) or master.get('url') != TOWN_ARCHIVE
            or master.get('license_url') != TOWN_TERMS or master.get('member') != 'mt_town_all.csv'
            or not _date(master.get('checked_at')) or not _hash(master.get('page_hash'))):
        return False
    row = master.get('row')
    if not isinstance(row, dict):
        return False
    row_number = row.get('csv_row')
    code = row.get('lg_code', '')
    town_id = row.get('machiaza_id', '')
    if (type(row_number) is not int or row_number < 2
            or not isinstance(code, str) or not re.fullmatch(r'[0-9]{6}', code)
            or not isinstance(town_id, str) or not re.fullmatch(r'[0-9]{7}', town_id)
            or row.get('machiaza_type') not in ('1', '3') or row.get('status_flg') != '1'
            or row.get('ablt_date') != '' or not _date(row.get('efct_date'))
            or row['efct_date'] > master['checked_at'][:10] or row.get('chome') != ''):
        return False
    town_columns = ('pref', 'county', 'city', 'ward', 'oaza_cho', 'koaza')
    if any(not isinstance(row.get(k), str) or not _TOWN_TEXT.fullmatch(row[k]) for k in town_columns):
        return False
    pref, county, city, ward, oaza, koaza = (row[k] for k in town_columns)
    if (pref != facility.get('prefecture') or code[:2] != facility.get('prefecture_code')
            or not city or not oaza or bool(koaza) != (row['machiaza_type'] == '3')):
        return False
    shared_koaza = proof.get('shared_koaza_raw')
    unmarked_koaza = proof.get('unmarked_koaza')
    documented_koaza = proof.get('documented_koaza')
    koaza_spellings = _town_spellings(koaza, ('小字', '字'))
    if shared_koaza is not None:
        if (koaza or not isinstance(shared_koaza, str) or not shared_koaza.startswith('小字')
                or len(shared_koaza) <= 2 or not _TOWN_TEXT.fullmatch(shared_koaza)):
            return False
        koaza = shared_koaza
        koaza_spellings = {shared_koaza}
    if unmarked_koaza is not None:
        if (pref != '京都府' or koaza or shared_koaza is not None
                or not isinstance(unmarked_koaza, dict)):
            return False
        koaza = unmarked_koaza.get('name_raw')
        if not isinstance(koaza, str) or not koaza or not _TOWN_TEXT.fullmatch(koaza):
            return False
        koaza_spellings = {koaza, '小字' + koaza}
    if documented_koaza is not None:
        if ((code, city) not in {('392049', '南国市'), ('202185', '千曲市')}
                or koaza or not isinstance(documented_koaza, dict)):
            return False
        koaza = documented_koaza.get('name_raw')
        if not isinstance(koaza, str) or not koaza or not _TOWN_TEXT.fullmatch(koaza):
            return False
        koaza_spellings = {koaza, '字' + koaza}
    fields = ref.get('source_fields')
    required = ('name', 'furigana', 'prefectureName', 'cityName', 'cityCode', 'streetNumber', 'corporateNumber')
    if not isinstance(fields, dict) or any(not isinstance(fields.get(k), str) for k in required):
        return False
    place = city + ward
    municipality = county + place
    name, reading, number = (fields[k] for k in ('name', 'furigana', 'corporateNumber'))
    address = pref + fields['cityName'] + fields['streetNumber']
    if (fields.get('kind') != '399' or fields.get('latest') != '1' or fields.get('process') == '99'
            or fields.get('closeDate') or fields.get('hihyoji') != '0'
            or fields.get('prefectureCode') != code[:2] or fields['cityCode'] != code[2:5]
            or fields['prefectureName'] != pref or fields['cityName'] not in {municipality, place}
            or not re.fullmatch(r'[0-9]{13}', number)
            or (name, reading, number, address) != tuple(ref.get(k) for k in
                ('name_raw', 'reading_raw', 'corporate_number', 'address_raw'))
            or (name != facility.get('listed_name') and bound_registered_shrine_name(ref) != facility.get('listed_name'))):
        return False
    try:
        if _reading(name, reading) != changes['reading']:
            return False
    except ValueError:
        return False
    oaza_spellings = _town_spellings(oaza, ('大字', '字'))
    localities = {a + k for a in oaza_spellings for k in koaza_spellings}
    left = _addresses(agency, {municipality, place, pref + municipality, pref + place}, localities)
    right = _addresses(address, {pref + fields['cityName']}, localities)
    if len(left) != 1 or len(right) != 1:
        return False
    (agency_town, agency_parcel), = left
    (register_town, register_parcel), = right
    if documented_koaza is not None:
        state = ref.get('registry_state_proof')
        if (agency_parcel != register_parcel or {agency_town, register_town} != {oaza + koaza, oaza + '字' + koaza}
                or not isinstance(state, dict) or state.get('unique_active_corporate_number') != number
                or type(state.get('full_address_active_corporations')) is not int
                or state['full_address_active_corporations'] != 1):
            return False
        if city == '南国市':
            return _nankoku_koaza_matches(documented_koaza.get('reference'), oaza, koaza)
        return _chikuma_koaza_matches(documented_koaza, name, oaza, koaza, register_parcel)
    if unmarked_koaza is not None:
        if (agency_parcel != register_parcel or register_town not in {a + '小字' + koaza for a in oaza_spellings}
                or agency_town not in {a + koaza for a in oaza_spellings}):
            return False
        if 'shrine_site' in unmarked_koaza:
            return ('parcel_map' not in unmarked_koaza
                    and _public_shrine_parcel_matches(unmarked_koaza['shrine_site'], name, city,
                                                     oaza_spellings, koaza, register_parcel))
        return code == '262013' and _documented_fukuchiyama_parcel(unmarked_koaza, oaza, register_parcel)
    return (agency_town != register_town and agency_parcel == register_parcel
            and oaza + koaza in {agency_town, register_town})
