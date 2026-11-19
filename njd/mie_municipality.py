"""Evidence for the missing municipality in one acquired Mie agency row."""
from datetime import datetime

from njd.locations import _hash, _MISSING_LOCATION, _plain, _raw_field, raw_address
from njd.normalize import normalize_reading


_FACILITY_ID = '854451cc-c896-5a37-bfd7-9360567bebec'
_ENTRY_ID = '623ef6a4-bf2c-5f25-84f0-094a945b6606'
_SOURCE_HASH = '655360a1447028841f395f503213c13b467fc08a0b25333fb9a4db9714aa0b67'
_NAME = '東外城田神社'
_PREFECTURE = '三重県'
_TOWN = '度会郡玉城町'
_ADDRESS = '三重県度会郡玉城蚊野2218-2'
_REGISTERED_ADDRESS = '度会郡玉城町蚊野2218-2'
_READING = 'ひがしときだじんじゃ'
_CODE = '4208002'
_PROFILE = ('https://kyoka.mie-jinjacho.or.jp/shrine/'
            '%e6%9d%b1%e5%a4%96%e5%9f%8e%e7%94%b0%e7%a5%9e%e7%a4%be/')
_PROFILE_LOCATOR = 'div.shrine_detail h2; span.furigana; table.table_03 th=神社コード/鎮座地'
_NTA_BASE = 'https://www.houjin-bangou.nta.go.jp/download/'
_DAILY_RESOURCES = (
    (2, '28508', 2346), (4, '28511', 2156), (5, '28514', 2183),
    (6, '28517', 2617), (9, '28520', 2362), (10, '28523', 2642),
    (11, '28526', 2692), (12, '28529', 2180), (13, '28532', 2548),
    (16, '28535', 2372), (17, '28538', 2183), (18, '28541', 2483),
    (19, '28544', 2035),
)


def _matches(record, **fields):
    return isinstance(record, dict) and all(
        type(record.get(key)) is type(value) and record.get(key) == value
        for key, value in fields.items())


def _observations_in_order(*values):
    try:
        dates = [datetime.fromisoformat(value) for value in values]
    except (TypeError, ValueError):
        return False
    return all(date.tzinfo is not None for date in dates) and dates == sorted(dates)


def _excerpt_includes(reference, *values):
    excerpt = reference.get('excerpt')
    return _plain(excerpt) and all(value in excerpt for value in values)


def _registry_matches(registry, recorded_at):
    if not _matches(registry, as_of='20261119', daily_rows=30799, related_daily_events=0):
        return False
    monthly = registry.get('monthly')
    member = '24_mie_all_20261030.csv'
    monthly_url = _NTA_BASE + 'zenken/index.html'
    if not _matches(monthly, url=monthly_url, response_url=monthly_url, snapshot='20261030',
                    file_id='28429', member=member, prefecture_code='24', rows=57194,
                    page_hash='8afbf798651c6d2057b0cde1a30004e342857b10ae73b9425dd72a3a2fe96131'):
        return False
    checked = registry.get('checked_at')
    if not _observations_in_order('2026-11-19T00:00:00+00:00', checked, recorded_at):
        return False
    if not _observations_in_order('2026-10-30T00:00:00+00:00', monthly.get('checked_at'), checked):
        return False
    daily = registry.get('daily')
    if not isinstance(daily, list) or len(daily) != len(_DAILY_RESOURCES):
        return False
    daily_url = _NTA_BASE + 'sabun/index.html'
    for resource, (day, file_id, count) in zip(daily, _DAILY_RESOURCES):
        snapshot = f'202611{day:02}'
        if (not _matches(resource, url=daily_url, response_url=daily_url, snapshot=snapshot,
                         member=f'diff_{snapshot}.csv', file_id=file_id, rows=count)
                or not _hash(resource.get('page_hash'))
                or not _observations_in_order(f'2026-11-{day:02}T00:00:00+00:00',
                                              resource.get('checked_at'), checked)):
            return False
    rows = registry.get('related_monthly_active_rows')
    return (isinstance(rows, list) and len(rows) == 1
            and _matches(rows[0], csv_row=43732, zip_member=member)
            and _matches(rows[0].get('source_fields'), sequenceNumber='43732', corporateNumber='7190005004962',
                         name=_NAME, prefectureName=_PREFECTURE, prefectureCode='24', cityCode='461', cityName=_TOWN,
                         streetNumber='蚊野２２１８番地の２', postCode='5190431', kind='399', latest='1', process='01',
                         closeDate='', hihyoji='0', nameImageId='', addressImageId='', furigana=''))


def municipality_problems(supplement, facility):
    if (not _matches(facility, id=_FACILITY_ID, source_key='mie', prefecture_code='24', prefecture=_PREFECTURE,
                     listing_url=_PROFILE, source_locator=_PROFILE_LOCATOR, name_raw=_NAME, listed_name=_NAME,
                     native_source_id=_CODE, source_hash=_SOURCE_HASH, address_raw=_ADDRESS, address=_ADDRESS,
                     official_site_url=None)
            or not _hash(facility.get('page_hash'))
            or raw_address(facility) != _ADDRESS or _raw_field(facility, 'municipality') != ''
            or facility.get('municipality') not in ('', _TOWN)
            or facility.get('name_rendering_status') in ('external_glyph', 'unrenderable')):
        return ['municipality selection requires the unchanged Mie agency row and its original address']
    if (not _matches(supplement, facility_id=_FACILITY_ID, entry_id=_ENTRY_ID, expected_source_hash=_SOURCE_HASH,
                     changes={'municipality': _TOWN},
                     original=dict(name_raw=_NAME, address=_ADDRESS, municipality='', listing_url=_PROFILE,
                                   native_source_id=_CODE, official_site_url=None))
            or not _plain(supplement.get('reason'))):
        return ['municipality selection differs from the acquired snapshot or would change another field']

    original = supplement.get('profile_original')
    rechecked = supplement.get('profile_rechecked')
    recorded = supplement.get('recorded_at')
    profile_fields = dict(name_raw=_NAME, reading_raw=_READING, native_source_id=_CODE, address_raw=_ADDRESS)
    if (not _matches(original, **profile_fields, listing_url=_PROFILE, source_locator=_PROFILE_LOCATOR,
                     source_hash=_SOURCE_HASH,
                     page_hash='f8236e7e84a02fef101e23ae23d6b80922ccdd78973caaf7b0ad2014098bfdb3')
            or not _matches(rechecked, **profile_fields, url=_PROFILE, locator=_PROFILE_LOCATOR, source_kind='agency',
                            page_hash='6f82da1d989ec039f3dcd433e2fb46cf49f4208cd6899c3154af965d71bb0f85')
            or not _observations_in_order(original.get('fetched_at'), rechecked.get('checked_at'), recorded)
            or any(not _excerpt_includes(ref, *profile_fields.values()) for ref in (original, rechecked))):
        return ['municipality selection requires the matching acquired and rechecked Mie profile fields']

    reference = supplement.get('reference')
    if (not _matches(reference, url='https://www.pref.mie.lg.jp/common/content/001217775.pdf',
                     page_hash='3807c96fd1480bc36e508b1e5102d9c6cfa1749c34ba7321cdeb155747e71830',
                     source_kind='government_religious_corporation_register', source_publisher='三重県環境生活部文化振興課',
                     name_raw=_NAME, address_raw=_REGISTERED_ADDRESS, municipality_raw=_TOWN, as_of='2026-05-01',
                     prefectural_heading_raw='玉城町', pdf_page_index=113, printed_page=111, printed_record_number=2,
                     locator='PDF 114枚目 / 印刷111頁 / 玉城町 / 番号2 / 宗教法人名・所在地列')
            or not _observations_in_order(reference.get('fetched_at'), reference.get('checked_at'), recorded)
            or not _excerpt_includes(reference, '番号2', _NAME, _REGISTERED_ADDRESS)):
        return ['municipality selection requires the inspected prefectural register row and full parcel']

    tourism = supplement.get('tourism_reference')
    if (not _matches(tourism, url='https://www.kankomie.or.jp/spot/23890',
                     page_hash='c6a9c970827298b304ff78760aac5e9607ebd8bc9aef03e8e4a239d0e567fe26',
                     source_kind='tourism_organization', source_publisher='公益社団法人三重県観光連盟',
                     name_raw=_NAME, address_raw=_REGISTERED_ADDRESS, reading_raw='ヒガシトキダジンジャ')
            or not _plain(tourism.get('locator'))
            or not _observations_in_order(tourism.get('checked_at'), recorded)
            or not _excerpt_includes(tourism, _NAME, tourism['reading_raw'], '519-0431', _REGISTERED_ADDRESS)
            or not _registry_matches(supplement.get('national_registry_reference'), recorded)):
        return ['municipality selection lacks matching tourism and active national-register parcel evidence']

    booklet = supplement.get('unresolved_other_address')
    if (not _matches(booklet, url='https://kizuna.town.tamaki.mie.jp/chosei/shokai/documents/goriyaku.pdf',
                     source_kind='government_tourism_booklet', address_raw='玉城町野篠 2218-2')
            or not _plain(booklet.get('scope'))):
        return ['municipality selection must retain the separate conflicting locality observation']
    return []


def municipality_entry_problems(facility, entries):
    if len(entries) == 1:
        entry = entries[0]
        status = (entry.get('status'), entry.get('reason'))
        if (status in (('pending', _MISSING_LOCATION), ('verified', ''))
                and _matches(entry, id=_ENTRY_ID, facility_id=_FACILITY_ID, name_raw=_NAME, surface=_NAME,
                             page_hash=facility.get('page_hash'), source_hash=_SOURCE_HASH, listing_url=_PROFILE,
                             reading_url=_PROFILE, reading_source_kind='agency', source_reading_raw=_READING,
                             reading_raw=_READING, reading=normalize_reading(_READING))):
            return []
    return ['municipality selection requires the single original Mie agency registration and reading']
