"""Validate the inspected sources identifying two Nantan shrine readings."""

from njd.locations import _date, _hash, _plain

PROOF_KIND = 'nantan_shrine_identity'
_GBIZ = 'https://info.gbiz.go.jp/hojin/ichiran?hojinBango='
_BOOKLET = 'https://www.nancla.jp/wp-content/uploads/2020/11/tsurugaoka-kyokasho-2.pdf'
_HISTORY = ('https://upload.wikimedia.org/wikipedia/commons/8/87/'
            'NDL950928_%E8%88%B9%E4%BA%95%E9%83%A1%E8%AA%8C_part2.pdf')


def _observed(record, url, **fields):
    return (isinstance(record, dict) and record.get('url') == url
            and _hash(record.get('page_hash')) and _date(record.get('checked_at'))
            and _plain(record.get('locator')) and all(record.get(k) == v for k, v in fields.items()))


def _arai(ref, proof):
    address = '京都府南丹市八木町美里荒井１番地'
    corp = '8130005007433'
    designation, history = proof.get('designation'), proof.get('history')
    # Both cultural records identify the same building by the attached plaques.
    return (
        _observed(ref, _GBIZ+corp, source_kind='government_corporate_profile', corporate_number_raw=corp,
                  address_raw=address, reading_raw='アライジンジャ')
        and address in ref['excerpt']
        and _observed(designation, 'https://www.kyoto-be.ne.jp/soumu/bunkazai/bunkazai41.pdf',
            pdf_page=5, address_raw='南丹市八木町美里荒井', designation_name_raw='荒井神社本殿',
            former_reference_raw='旧神田村の北西に所在し、神宮寺であった西光寺に隣接する。',
            inscriptions_raw=['上葺永正十六年己卯九月八日の記があるもの 一',
                              '上葺明暦三丁酉九月二十四日の記があるもの 一',
                              '永禄九年十月吉日の記があるもの 一'])
        and _hash(designation.get('image_sha256'))
        and _observed(history, _HISTORY, pdf_page=4, printed_page=184, name_raw='荒井神社',
            address_raw='大字神田小字荒井',
            inscriptions_dates_raw=['永正十六年九月', '永禄九年十月', '明暦三年八月屋根葺替同年九月二十四日正遷宮'])
        and _hash(history.get('image_sha256'))
    )


def _suzunami(ref, proof):
    caption, designation, corporate = (proof.get(k) for k in ('caption', 'designation', 'corporate'))
    corp = '5130005007642'
    # The booklet names the tree in the same district as the reading. The
    # prefectural designation and corporate record each state the full parcel.
    return (
        _observed(ref, _BOOKLET, source_kind='local_community_booklet', map_label_raw='鈴波神社',
                  district_raw='松尾区', pdf_page=52, printed_page=49, address_raw='', reading_raw='すずなみじんじゃ')
        and _hash(ref.get('image_sha256'))
        and _observed(caption, _BOOKLET, pdf_page=51, printed_page=48,
                      caption_raw='鈴波神社のスギ（南丹市指定文化財）', section_raw='鈴波神社例祭（10月6日）')
        and caption['page_hash'] == ref['page_hash'] and caption['checked_at'] == ref['checked_at']
        and _hash(caption.get('image_sha256')) and caption['image_sha256'] != ref['image_sha256']
        and _observed(designation, 'https://www.pref.kyoto.jp/kankyo/rdb/eco/sd/sd026.html',
            designation_name_raw='松尾鈴波神社のスギ', designation_status_raw='南丹市指定天然記念物',
            address_raw='南丹市美山町豊郷宮ノ谷11番地')
        and _observed(corporate, _GBIZ+corp, name_raw='鈴波神社', corporate_number_raw=corp,
                      address_raw='京都府南丹市美山町豊郷宮ノ谷１１番地')
        and 'reading_raw' in corporate and corporate['reading_raw'] is None
    )


def nantan_reference_matches(ref, facility, entry, changes):
    """Bind the exact acquired rows and accept only reading corrections."""
    if (set(changes) != {'reading'} or entry.get('status') == 'excluded'
        or (facility.get('source_key'), facility.get('prefecture_code'), facility.get('municipality'))
        != ('kyoto', '26', '南丹市') or ref.get('reading_scope') != 'full_name'):
        return False
    name, address, digest = (facility.get(k) for k in ('listed_name', 'address', 'source_hash'))
    proof = ref['address_identity_proof']
    if (not _plain(name) or name != ref.get('name_raw') or name != entry.get('surface')
        or not _plain(ref.get('excerpt')) or name not in ref['excerpt']
        or not _hash(digest) or digest != entry.get('source_hash')
        or entry.get('facility_id') != facility.get('id')
        or (proof.get('facility_id'), proof.get('entry_id')) != (facility.get('id'), entry.get('id'))
        or proof.get('expected_source_hash') != digest or proof.get('agency_address_raw') != address
        or proof.get('reference_url') != ref.get('url') or proof.get('reference_page_hash') != ref.get('page_hash')):
        return False
    if (name, address) == ('荒井神社', '南丹市八木町神田小字荒井1'):
        return _arai(ref, proof)
    if (name, address) == ('鈴波神社', '南丹市豊郷宮ノ谷11'):
        return _suzunami(ref, proof)
    return False
