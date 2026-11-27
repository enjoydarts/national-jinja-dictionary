"""Validate the reviewed Nagasaki regional rows and their link-only observations."""

from dataclasses import dataclass
from datetime import datetime

from njd.source_aliases import FIELDS

KIND = 'nagasaki_explicit_shared_official_link'
_AGENCY_URL = 'https://nagasaki-jinjacho.or.jp/'


@dataclass(frozen=True)
class Observation:
    facility_id: str
    entry_id: str
    name: str
    source_hash: str
    href: str
    locator: str


@dataclass(frozen=True)
class Alias:
    primary: Observation
    duplicate: Observation
    regional_path: str
    municipality: str
    address: str
    proof_kind: str


# These pairs were reviewed individually. A new pair or a changed source row
# needs its own documentary review before it can use this resolution.
_ALIASES = (
    Alias(
        Observation(
            'd9975756-7562-556b-bc8f-8061f50a67ac',
            '98894a79-bb3e-5cc3-9b96-e9656f4a9297',
            '阿蘇神社',
            'b691f7fc1c86c040b3b846cebb162988302f378250a1feb4684d84d827e84f09',
            'http://asojinja.jp/',
            'table[5] tr[6]',
        ),
        Observation(
            'e21c64ca-c91f-59f5-91ca-3a7460c6690c',
            'de900201-e788-526a-a9f4-95f1be2abac5',
            '阿蘇神社',
            '9d2343c011e312e4ed43b754c7bf9fe03599253ce28f3216b3162456a9542a00',
            'http://www.asojinja.jp/',
            'div#bk17860131 a[href="http://www.asojinja.jp/"]',
        ),
        'seihi.html', '諫早市', '諫早市多良見町化屋861番地',
        'same_endpoint_body',
    ),
    Alias(
        Observation(
            '782ac20c-5a69-5b3e-8559-7ba4ff58e1ee',
            'd4cfe00d-745c-5997-9920-8d9a4ac0c43b',
            '國片主神社',
            'bd0d83deeb4d01023d2d7478fbc54f61c86bb474f8d045c936cbc7701b07eeab',
            'http://kunikatanushijinja.com/',
            'table[2] tr[13]',
        ),
        Observation(
            '80538e05-9096-56de-b9a2-51fb2161dba1',
            '89e70648-9f8e-5fd6-be32-a2094022218c',
            '国片主神社',
            '729e65462151a7a17035535e24a0b2d71351324e9a6c82dab6cc48449e3f9626',
            'https://kunikatanushijinja.com/',
            'div#bk17860132 a[href="https://kunikatanushijinja.com/"]',
        ),
        'iki.html', '壱岐市', '壱岐市芦辺町国分東触766番地',
        'same_publisher_navigation',
    ),
    Alias(
        Observation(
            'b8267108-4c84-573c-89f1-a567d3f0e4a9',
            '27daee3c-0fdb-53db-9611-94e1ee0750d7',
            '月讀神社',
            'fc66ac15e5e3429c53d5833e953f74d716241560cac18fa736f164ffbcd8cc83',
            'http://tsukiyomijinja.com/',
            'table[2] tr[9]',
        ),
        Observation(
            '8c1ed1ad-fcf7-599c-a546-219448733472',
            '78f1e281-1ca9-54c5-bb59-369fab9e4cec',
            '月読神社',
            '8996fc0a23b69eac21063ffb9eab0221c413d0a331812e868579896324ba814c',
            'https://tsukiyomijinja.com/',
            'div#bk17860132 a[href="https://tsukiyomijinja.com/"]',
        ),
        'iki.html', '壱岐市', '壱岐市芦辺町国分東触464番地',
        'same_publisher_navigation',
    ),
    Alias(
        Observation(
            'b82ff87a-c4cd-5440-9686-1def4f7f9451',
            '84303b58-eb4c-510b-ac84-8cb2dc08bf6e',
            '温泉神社',
            'a6ce456613119fda4278d2b04576f043f789f71dc2899d911c877c77c21d223c',
            'https://www.facebook.com/onsenjinjya/?eid=ARB5h5sSgFtuJS7VO9Hv-2_L-j-PWZZDGa87tbXVUcEJNkAbWS0YKjgNWwdXGIb5crN60asM36jwChIp',
            'table[1] tr[25]',
        ),
        Observation(
            'cdda7af6-dab0-5f19-8382-0877edb338d1',
            '909cb4e1-3d7d-50b9-b492-fc603b84b24b',
            '温泉神社',
            '62b5f0de7626bf0d24046a5a6b781857cfa5dfc4ff40d6aeb00a8b47e54ee3ef',
            'https://www.instagram.com/onsenjinjya.official/',
            'div#bk17860132 a[href="https://www.instagram.com/onsenjinjya.official/"]',
        ),
        'shimabara.html', '島原市', '島原市有明町湯江甲989番地',
        'agency_social_profile_link',
    ),
)


# The selected receipts include the literal fields that establish each connection:
# matching response bodies, shared publisher content, or the association's
# named profile link.
_LINK_RECEIPTS = {
    '阿蘇神社': (
        dict(
            status=200,
            url='http://www.asojinja.jp/',
            page_hash='48b210005e0b5f19985e2c0691d904541a7b37f713f68aa91db54abca51ffaca',
            name_raw='阿蘇神社',
            address_raw='長崎県諫早市多良見町化屋862',
            address_role='shrine_office',
            title='阿蘇神社（諫早市多良見町）',
        ),
        dict(
            status=200,
            url='http://asojinja.jp/',
            page_hash='48b210005e0b5f19985e2c0691d904541a7b37f713f68aa91db54abca51ffaca',
            name_raw='阿蘇神社',
            address_raw='長崎県諫早市多良見町化屋862',
            address_role='shrine_office',
            title='阿蘇神社（諫早市多良見町）',
        ),
    ),
    '國片主神社': (
        dict(
            status=200,
            url='http://kunikatanushijinja.com/',
            page_hash='c53bb77c8d5163570d306d5c7c73256ff919e9d63c4cd29c7301a5eb9729daf8',
            source_publisher='國片主神社',
            name_raw='國片主神社',
            address_raw='長崎県壱岐市芦辺町国分東触766',
            href_raw='http://kunikatanushijinja.com/access/',
            address_role='footer_published_address',
            title='國片主神社',
        ),
        dict(
            status=200,
            url='https://kunikatanushijinja.com/',
            page_hash='ce16451e0f7a0ebb7be707b5eb56cd64d6486d06a0cfef5135f6410b94fd13ae',
            source_publisher='國片主神社',
            name_raw='國片主神社',
            address_raw='長崎県壱岐市芦辺町国分東触766',
            href_raw='https://kunikatanushijinja.com/access/',
            address_role='footer_published_address',
            title='國片主神社',
        ),
    ),
    '月讀神社': (
        dict(
            status=200,
            url='http://tsukiyomijinja.com/',
            page_hash='eb4de2b77aee09f559e8c0e4fd3f65944d3be21b85ed442f2538fb875b83cf6b',
            source_publisher='月讀神社',
            name_raw='月讀神社',
            address_raw='長崎県壱岐市芦辺町国分東触464',
            href_raw='http://tsukiyomijinja.com/%e3%82%a2%e3%82%af%e3%82%bb%e3%82%b9/',
            address_role='footer_published_address',
            title='月讀神社 – 神道発祥の地に鎮座する月の神',
        ),
        dict(
            status=200,
            url='https://tsukiyomijinja.com/',
            page_hash='7e29fc7d7b16e687f3f56fcc57e07c092424611a89f056a7c46f7b65d4110908',
            source_publisher='月讀神社',
            name_raw='月讀神社',
            address_raw='長崎県壱岐市芦辺町国分東触464',
            href_raw='https://tsukiyomijinja.com/%e3%82%a2%e3%82%af%e3%82%bb%e3%82%b9/',
            address_role='footer_published_address',
            title='月讀神社 – 神道発祥の地に鎮座する月の神',
        ),
    ),
    '温泉神社': (
        dict(
            status=200,
            url='https://shimengu-jinja.jp/',
            page_hash='cb38412e837cdf7b5dff601b51abb5bb114c05e1776e37257d4d364fbd890843',
            role='publisher_social_link_witness',
            source_publisher='四面宮会',
            name_raw='湯江\u3000温泉神社',
            href_raw='https://www.instagram.com/onsenjinjya.official/',
            profile_name_raw='onsenjinjya.official',
        ),
        dict(
            status=200,
            url='https://shimengu-jinja.jp/%E5%9B%9B%E9%9D%A2%E5%AE%AE%E7%A5%9E%E7%A4%BE%E4%B8%80%E8%A6%A7/',
            page_hash='e5ddda11272f0f3211f6388e0d34dfe012a95fe4833705fe793ad9b410047ee0',
            role='publisher_shrine_address_witness',
            source_publisher='四面宮会',
            name_raw='湯江温泉神社',
            address_raw='長崎県島原市有明町湯江甲989番地',
            href_raw='https://shimengu-jinja.jp/10yue/',
        ),
        dict(
            status=200,
            url='https://shimengu-jinja.jp/10yue/',
            page_hash='4457692f668591f53363d9a6afa0cff15d55a9d3a6b69a87f4162defd2e29166',
            role='publisher_shrine_detail',
            source_publisher='四面宮会',
            name_raw='⑩ 湯江温泉神社',
            address_raw='長崎県島原市有明町湯江甲989番地',
        ),
    ),
}

# The office or access-map parcel can differ. These sources give the precinct
# or the full parcel used in the reviewed regional row.
_ADDRESS_RECEIPTS = {
    '阿蘇神社': dict(
        status=200,
        url='https://www.pref.nagasaki.jp/uploads/2025/02/1739522392.pdf',
        page_hash='53fea64fdca3d3a74c25787807507baf42d162c6ba28762b9a534706e5df96f3',
        source_publisher='長崎県',
        name_raw='忠魂碑',
        address_raw='諫早市多良見町化屋 861',
        address_role='monument_inside_shrine_precinct',
        pdf_page=17,
    ),
    '國片主神社': dict(
        status=200,
        url='https://www.ikikankou.com/storage/files/shares/Pamphlet/Japanese_heritage_Iki_map.pdf',
        page_hash='13e096910a8c027c07342b0c98b90662c9cd103decce619773acbc9fae3e1eac',
        source_publisher='壱岐市観光連盟掲載の日本遺産冊子',
        name_raw='國片主神社',
        address_raw='長崎県壱岐市芦辺町国分東触766',
    ),
    '月讀神社': dict(
        status=200,
        url='https://jl-db.nfaj.go.jp/location/420111153/',
        page_hash='925ea0742d12fb7872d2b27ebffc375b664a34cc8aa1694abed7178af5887f92',
        source_publisher='国立映画アーカイブ「全国ロケーションデータベース」',
        name_raw='月読神社',
        address_raw='長崎県壱岐市芦辺町国分東触464',
    ),
}

_REGIONAL_PAGES = {
    'seihi.html': '3533c16893b5756f34c4c93b68d6a771d88f132c7109becca2fe0c958489bdd5',
    'iki.html': '3bb54700bb5080fb2b46f1dd35fc5ee1699abfaa59cad74b3b1cdf7e9e3d932a',
    'shimabara.html': '1d3edf4d025b0f27a6e6b20c4a49d9e085a8af851d6debc8407764b32583b799',
}
_LEGACY_PAGE_HASH = '307091be9b409e579a3163b03f301e3972c3ceabf9fd1ea5dfd375fcfad11b04'
_LEGACY_BRANCHES = {
    '阿蘇神社': '西彼支部',
    '国片主神社': '壱岐支部',
    '月読神社': '壱岐支部',
    '温泉神社': '島原南高支部',
}


def _review_date(value):
    try:
        date = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    return date if date.utcoffset() is not None else None


def _matches(record, expected):
    return isinstance(record, dict) and all(key in record and record[key] == value
                                            for key, value in expected.items())


def _has_text(value):
    return isinstance(value, str) and bool(value.strip())


def _receipt_matches(receipt, expected, checked_at):
    if not _matches(receipt, expected) or not _has_text(receipt.get('locator')):
        return False
    fetched_at = _review_date(receipt.get('fetched_at'))
    return fetched_at is not None and fetched_at <= checked_at


def _original_matches(facility, observation, *, path, address, municipality, native_id, page_hash):
    return _matches(facility, dict(
        id=observation.facility_id,
        source_key='nagasaki',
        prefecture='長崎県',
        prefecture_code='42',
        name_raw=observation.name,
        address=address,
        municipality=municipality,
        listing_url=_AGENCY_URL + path,
        source_locator=observation.locator,
        native_source_id=native_id,
        official_site_url=observation.href,
        source_hash=observation.source_hash,
        page_hash=page_hash,
    )) and facility.get('address_raw') is None and facility.get('address_context') is None


def _agency_receipt_matches(receipt, facility, checked_at, *, legacy):
    first_fetched = _review_date(facility.get('fetched_at'))
    if first_fetched is None:
        return False
    expected = dict(
        url=facility['listing_url'],
        locator=facility['source_locator'],
        page_hash=facility['page_hash'],
        source_record_fetched_at=facility['fetched_at'],
        source_publisher='長崎県神社庁',
        status=200,
        native_source_id=facility['native_source_id'],
        name_raw=facility['name_raw'],
        address_raw=facility['address'],
        href_raw=facility['official_site_url'],
        official_site_url=facility['official_site_url'],
    )
    if legacy:
        expected.update(role='original_agency_link_observation',
                        branch_raw=_LEGACY_BRANCHES[facility['name_raw']])
    else:
        locator = facility['source_locator']
        expected.update(role='regional_agency_shrine_row', name_column_raw='神社名',
                        address_column_raw='鎮座地', address_locator=locator + ' td[7]',
                        href_locator=locator + ' td[2] a[href]')
    if not _receipt_matches(receipt, expected, checked_at):
        return False
    return first_fetched <= _review_date(receipt['fetched_at'])


def _documentary_proof_matches(record, alias, checked_at):
    proof = record.get('link_proof')
    if not _matches(proof, dict(kind=alias.proof_kind)):
        return False
    receipts = proof.get('references')
    expected = _LINK_RECEIPTS[alias.primary.name]
    if not isinstance(receipts, list) or len(receipts) != len(expected):
        return False
    if not all(_receipt_matches(receipt, witness, checked_at)
               for receipt, witness in zip(receipts, expected)):
        return False
    address_witness = _ADDRESS_RECEIPTS.get(alias.primary.name)
    if address_witness is None:
        return True
    supporting = record.get('corroboration')
    return isinstance(supporting, list) and any(
        _receipt_matches(receipt, address_witness, checked_at) for receipt in supporting
    )


def resolution_problems(record, primary, duplicate):
    """Report mismatches against the two original facilities and the reviewed receipts."""
    if not all(isinstance(item, dict) for item in (record, primary, duplicate)):
        return ['Nagasaki alias resolution or original observation missing']
    alias = next((pair for pair in _ALIASES if pair.duplicate.facility_id == duplicate.get('id')), None)
    if alias is None or not _matches(record, dict(
        kind=KIND, primary_id=alias.primary.facility_id, duplicate_id=alias.duplicate.facility_id,
        primary_entry_id=alias.primary.entry_id, duplicate_entry_id=alias.duplicate.entry_id,
    )):
        return ['Nagasaki alias identity is outside the reviewed pairs']

    if not (_original_matches(primary, alias.primary, path=alias.regional_path,
                              address=alias.address, municipality=alias.municipality,
                              native_id=None, page_hash=_REGIONAL_PAGES[alias.regional_path])
            and _original_matches(duplicate, alias.duplicate, path='link.html',
                                  address='', municipality='', native_id=alias.duplicate.href,
                                  page_hash=_LEGACY_PAGE_HASH)):
        return ['Nagasaki alias original source row, locator, name, address or href differs']
    snapshots = dict(primary={key: primary.get(key) for key in FIELDS},
                     duplicate={key: duplicate.get(key) for key in FIELDS})
    if record.get('snapshots') != snapshots:
        return ['Nagasaki alias original snapshots differ']

    checked_at = _review_date(record.get('checked_at'))
    if checked_at is None or not _has_text(record.get('reason')):
        return ['Nagasaki alias review date or reason missing']
    witnesses = record.get('evidence')
    if (not isinstance(witnesses, list) or len(witnesses) != 2
            or not _agency_receipt_matches(witnesses[0], duplicate, checked_at, legacy=True)
            or not _agency_receipt_matches(witnesses[1], primary, checked_at, legacy=False)):
        return ['Nagasaki alias needs the exact legacy link and regional shrine row observations']
    if not _documentary_proof_matches(record, alias, checked_at):
        return ['Nagasaki alias documentary link or full parcel witness differs']
    return []
