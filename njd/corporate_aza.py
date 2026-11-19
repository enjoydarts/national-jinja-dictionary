"""Compare registered parcels using literal components of an official town row."""
import re

from njd.locations import _date, _hash


TOWN_ARCHIVE = 'https://data.address-br.digital.go.jp/mt_town/mt_town_all.csv.zip'
TOWN_TERMS = 'https://www.digital.go.jp/policies/base_registry_address_tos'
PROOF_KIND = 'registered_abr_town_spelling'
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
    koaza_spellings = _town_spellings(koaza, ('小字', '字'))
    if shared_koaza is not None:
        if (koaza or not isinstance(shared_koaza, str) or not shared_koaza.startswith('小字')
                or len(shared_koaza) <= 2 or not _TOWN_TEXT.fullmatch(shared_koaza)):
            return False
        koaza = shared_koaza
        koaza_spellings = {shared_koaza}
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
    localities = {a + k for a in _town_spellings(oaza, ('大字', '字')) for k in koaza_spellings}
    left = _addresses(agency, {municipality, place, pref + municipality, pref + place}, localities)
    right = _addresses(address, {pref + fields['cityName']}, localities)
    if len(left) != 1 or len(right) != 1:
        return False
    (agency_town, agency_parcel), = left
    (register_town, register_parcel), = right
    return (agency_town != register_town and agency_parcel == register_parcel
            and oaza + koaza in {agency_town, register_town})
