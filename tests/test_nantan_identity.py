import unittest

from njd.corrections import apply_corrections
from njd.records import build_dataset
from njd.validation import eligible
from test_corrections import correction
from test_records import row


def observation(url, **values):
    return dict(url=url, page_hash='a' * 64, checked_at='2026-11-27T10:50:00+09:00',
                locator='掲載欄', **values)


def case(name, address, reading, reference, **support):
    data = build_dataset('kyoto', '26', '京都府', '京都府神社庁',
                         [row(name=name, address=address, reading_raw='')])
    facility, entry = data['facilities'][0], data['entries'][0]
    proposal = correction(data, {'reading': reading})
    record = proposal['entries'][entry['id']]
    reference['address_identity_proof'] = dict(kind='nantan_shrine_identity',
        facility_id=facility['id'], entry_id=entry['id'], expected_source_hash=entry['source_hash'],
        agency_address_raw=address, reference_url=reference['url'],
        reference_page_hash=reference['page_hash'], **support)
    record['references'] = [reference]
    return data, proposal, record, reference


def arai():
    reference = observation('https://info.gbiz.go.jp/hojin/ichiran?hojinBango=8130005007433',
        title='Gビズインフォ', source_kind='government_corporate_profile', name_raw='荒井神社',
        reading_raw='アライジンジャ', reading_scope='full_name', corporate_number_raw='8130005007433',
        address_raw='京都府南丹市八木町美里荒井１番地',
        excerpt='荒井神社／アライジンジャ／本店所在地 京都府南丹市八木町美里荒井１番地')
    designation = observation('https://www.kyoto-be.ne.jp/soumu/bunkazai/bunkazai41.pdf',
        pdf_page=5, image_sha256='d' * 64, designation_name_raw='荒井神社本殿',
        address_raw='南丹市八木町美里荒井', former_reference_raw='旧神田村の北西に所在し、神宮寺であった西光寺に隣接する。',
        inscriptions_raw=['上葺永正十六年己卯九月八日の記があるもの 一',
                          '上葺明暦三丁酉九月二十四日の記があるもの 一', '永禄九年十月吉日の記があるもの 一'])
    history = observation('https://upload.wikimedia.org/wikipedia/commons/8/87/NDL950928_%E8%88%B9%E4%BA%95%E9%83%A1%E8%AA%8C_part2.pdf',
        pdf_page=4, printed_page=184, image_sha256='e' * 64,
        name_raw='荒井神社', address_raw='大字神田小字荒井',
        inscriptions_dates_raw=['永正十六年九月', '永禄九年十月', '明暦三年八月屋根葺替同年九月二十四日正遷宮'])
    return case('荒井神社', '南丹市八木町神田小字荒井1', 'あらいじんじゃ', reference,
                designation=designation, history=history)


def suzunami():
    booklet = 'https://www.nancla.jp/wp-content/uploads/2020/11/tsurugaoka-kyokasho-2.pdf'
    reference = observation(booklet, title='暮らしのてびき編', source_kind='local_community_booklet',
        name_raw='鈴波神社', reading_raw='すずなみじんじゃ', reading_scope='full_name', address_raw='',
        excerpt='【 鈴波神社（すずなみじんじゃ） 】', map_label_raw='鈴波神社', district_raw='松尾区',
        pdf_page=52, printed_page=49, image_sha256='b' * 64)
    caption = observation(booklet, pdf_page=51, printed_page=48, image_sha256='c' * 64,
        caption_raw='鈴波神社のスギ（南丹市指定文化財）', section_raw='鈴波神社例祭（10月6日）')
    designation = observation('https://www.pref.kyoto.jp/kankyo/rdb/eco/sd/sd026.html',
        designation_name_raw='松尾鈴波神社のスギ', designation_status_raw='南丹市指定天然記念物',
        address_raw='南丹市美山町豊郷宮ノ谷11番地')
    corporate = observation('https://info.gbiz.go.jp/hojin/ichiran?hojinBango=5130005007642',
        name_raw='鈴波神社', corporate_number_raw='5130005007642', reading_raw=None,
        address_raw='京都府南丹市美山町豊郷宮ノ谷１１番地')
    return case('鈴波神社', '南丹市豊郷宮ノ谷11', 'すずなみじんじゃ', reference,
                caption=caption, designation=designation, corporate=corporate)


class NantanIdentityTest(unittest.TestCase):
    def test_independent_identity_and_literal_reading_preserve_the_acquired_fields(self):
        for fixture in (arai, suzunami):
            with self.subTest(site=fixture.__name__):
                data, proposal, record, reference = fixture()
                out = apply_corrections(data, proposal)
                self.assertEqual(len(eligible(out)), 1)
                self.assertEqual(out['entries'][0]['reading'], record['changes']['reading'])
                self.assertEqual(out['entries'][0]['reading_url'], reference['url'])
                self.assertEqual(out['entries'][0]['reading_raw'], '')
                self.assertEqual(out['facilities'], data['facilities'])

    def test_wrong_parcels_or_mismatched_documents_do_not_resolve_the_reading(self):
        for fixture, witness, field, value in (
            (arai, 'history', 'address_raw', '大字廣垣内小字荒井'),
            (arai, 'designation', 'inscriptions_raw', ['上葺永正十六年己卯九月九日の記があるもの 一']),
            (suzunami, 'designation', 'address_raw', '南丹市美山町豊郷宮ノ谷111番地'),
            (suzunami, 'corporate', 'address_raw', '京都府南丹市美山町豊郷宮ノ谷１１番地１'),
            (suzunami, 'caption', 'page_hash', 'f' * 64),
        ):
            with self.subTest(site=fixture.__name__, witness=witness, field=field):
                data, proposal, _, reference = fixture()
                reference['address_identity_proof'][witness][field] = value
                self.assertEqual(eligible(apply_corrections(data, proposal)), [])

    def test_context_does_not_alter_a_surface_or_clear_exclusion(self):
        data, proposal, record, _ = suzunami()
        record['changes']['surface'] = '鈴波神社社'
        self.assertEqual(eligible(apply_corrections(data, proposal)), [])
        record['changes'].pop('surface')
        data['entries'][0]['status'] = 'excluded'
        out = apply_corrections(data, proposal)
        self.assertEqual(out['entries'][0]['status'], 'excluded')
        self.assertEqual(eligible(out), [])
