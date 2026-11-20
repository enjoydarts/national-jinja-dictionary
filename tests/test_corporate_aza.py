import copy
import unittest

from njd.corrections import apply_corrections, correction_problems
from njd.corporate import BASE, FIELDS
from test_corporate import META, row, target


def example():
    t = target()
    f, e = t['facility'], t['entry']
    f['address'] = '鳥取市大覚寺裏谷76-2'
    f['source_hash'] = e['source_hash'] = 'e' * 64
    fields = dict(zip(FIELDS, row(streetNumber='大覚寺小字裏谷７６番地の２')))
    address = '鳥取県鳥取市大覚寺小字裏谷７６番地の２'
    ref = dict(META, title='国税庁法人番号公表サイト', source_kind='government_corporate_register',
               name_raw=fields['name'], reading_raw=fields['furigana'], address_raw=address,
               excerpt=f"{fields['name']} / {fields['furigana']} / {address}",
               corporate_number=fields['corporateNumber'], source_fields=fields, csv_row=1)
    ref['address_identity_proof'] = dict(
        kind='registered_abr_town_spelling', expected_source_hash=e['source_hash'],
        agency_address_raw=f['address'], registry_page_hash=ref['page_hash'],
        registry_csv_row=ref['csv_row'], town_master=dict(
            url='https://data.address-br.digital.go.jp/mt_town/mt_town_all.csv.zip',
            license_url='https://www.digital.go.jp/policies/base_registry_address_tos',
            member='mt_town_all.csv', checked_at=ref['checked_at'], page_hash='b' * 64,
            row=dict(csv_row=2, lg_code='312011', machiaza_id='0061002', machiaza_type='3',
                     pref='鳥取県', county='', city='鳥取市', ward='', oaza_cho='大覚寺',
                     chome='', koaza='裏谷', status_flg='1', efct_date='1947-01-01', ablt_date='')))
    proposal = dict(status='verified', facility_id=f['id'], expected_source_hash=e['source_hash'],
                    original=dict(name_raw=f['name_raw'], reading_raw='', address=f['address'],
                                  listing_url=f['listing_url']),
                    changes={'reading': 'まえだじんじゃ'}, references=[ref],
                    reason='同じ町字と全地番', identity_match='同名同一地番')
    return proposal, (f, e, t['source'])


class CorporateAzaTest(unittest.TestCase):
    def test_literal_kana_and_same_abr_town_and_full_parcel(self):
        proposal, target = example()
        self.assertEqual(correction_problems(proposal, *target), [])

    def test_inconsistent_address_witness_cannot_be_bypassed(self):
        proposal, target = example()
        changes = (
            ('ref', 'url', BASE + '/download/other.html'),
            ('ref', 'csv_row', 3),
            ('fields', 'cityCode', '202'),
            ('proof', 'agency_address_raw', '鳥取市大覚寺裏谷76-3'),
            ('row', 'lg_code', '312020'),
            ('row', 'koaza', '字谷'),
            ('row', 'ablt_date', '2025-01-01'),
        )
        for group, key, value in changes:
            with self.subTest(group=group, key=key):
                bad = copy.deepcopy(proposal)
                ref = bad['references'][0]
                proof = ref['address_identity_proof']
                groups = dict(ref=ref, fields=ref['source_fields'], proof=proof,
                              row=proof['town_master']['row'])
                groups[group][key] = value
                without_proof = {k: v for k, v in ref.items() if k != 'address_identity_proof'}
                without_proof.update(address_raw=target[0]['address'], excerpt='前田神社 マエダジンジャ 鳥取市大覚寺裏谷76-2')
                bad['references'].append(without_proof)
                self.assertTrue(correction_problems(bad, *target))

    def test_another_branch_is_never_the_same_address(self):
        proposal, target = example()
        ref = proposal['references'][0]
        ref['source_fields']['streetNumber'] = ref['source_fields']['streetNumber'].replace('２', '３')
        ref['address_raw'] = ref['address_raw'].replace('２', '３')
        ref['excerpt'] = ref['excerpt'].replace('２', '３')
        self.assertTrue(correction_problems(proposal, *target))

    def test_both_addresses_print_the_same_koaza(self):
        proposal, target = example()
        f, _, _ = target
        ref = proposal['references'][0]
        proof = ref['address_identity_proof']
        f['address'] = '鳥取市大覚寺小字裏谷76-2'
        proposal['original']['address'] = f['address']
        proof['agency_address_raw'] = f['address']
        proof['shared_koaza_raw'] = '小字裏谷'
        proof['town_master']['row'].update(oaza_cho='字大覚寺', koaza='', machiaza_type='1')
        ref['source_fields']['streetNumber'] = '字' + ref['source_fields']['streetNumber']
        ref['address_raw'] = ref['address_raw'].replace('大覚寺', '字大覚寺')
        ref['excerpt'] = ref['excerpt'].replace('大覚寺', '字大覚寺')
        self.assertEqual(correction_problems(proposal, *target), [])
        proof['shared_koaza_raw'] = '小字裏'
        self.assertTrue(correction_problems(proposal, *target))

    def test_unmarked_koaza_requires_a_matching_fukuchiyama_parcel(self):
        proposal, target = example()
        facility, _, _ = target
        ref = proposal['references'][0]
        proof = ref['address_identity_proof']
        facility.update(prefecture='京都府', prefecture_code='26', address='福知山市大覚寺裏谷76-2')
        proposal['original']['address'] = facility['address']
        proof['agency_address_raw'] = facility['address']
        proof['town_master']['row'].update(pref='京都府', city='福知山市', lg_code='262013',
                                          oaza_cho='字大覚寺', machiaza_type='1', koaza='')
        ref['source_fields'].update(prefectureName='京都府', prefectureCode='26', cityName='福知山市',
                                    cityCode='201', streetNumber='字大覚寺小字裏谷７６番地の２')
        ref['address_raw'] = '京都府福知山市字大覚寺小字裏谷７６番地の２'
        ref['excerpt'] = f"{ref['name_raw']} / {ref['reading_raw']} / {ref['address_raw']}"
        proof['unmarked_koaza'] = dict(
            name_raw='裏谷',
            municipality_explanation=dict(url='https://www.city.fukuchiyama.lg.jp/soshiki/5/64145.html',
                                         page_hash='c'*64, checked_at=ref['checked_at']),
            parcel_map=dict(
                url='https://habs.rad.naro.go.jp/spatial_data/amxpoly47/amxpoly_2022_26.fgb',
                catalog_url='https://habs.rad.naro.go.jp/spatial_data/amxpoly47/amxpoly_2022_26.html',
                license_url='https://www.tellusxdp.com/docs/api-service/aigid-moj/tos.pdf',
                page_hash='d'*64, checked_at=ref['checked_at'], matching_features=1,
                feature=dict(index=0, byte_offset=3, sha256='0'*64,
                             fields={'市区町村コード':'26201','市区町村名':'福知山市',
                                     '大字名':'字大覚寺','小字名':'','地番':'76-2'})))
        self.assertEqual(correction_problems(proposal, *target), [])

        for field, value in (('市区町村コード', '26202'), ('大字名','字架空'), ('地番','76-3')):
            with self.subTest(field=field):
                bad=copy.deepcopy(proposal)
                bad['references'][0]['address_identity_proof']['unmarked_koaza']['parcel_map']['feature']['fields'][field]=value
                self.assertTrue(correction_problems(bad, *target))

        proof['unmarked_koaza']['name_raw'] = '裏'
        self.assertTrue(correction_problems(proposal, *target))

        proof['unmarked_koaza'] = dict(
            name_raw='裏谷',
            shrine_site=dict(url='https://www.city.fukuchiyama.lg.jp/example.pdf',
                             source_kind='government_shrine_site', page_hash='a'*64,
                             checked_at=ref['checked_at'], locator='指定文化財一覧・対象行',
                             item_raw='前田神社本殿', address_raw='字大覚寺76-2',
                             scope_raw='福知山市内の指定文化財一覧', location_header_raw='所在地',
                             excerpt='前田神社本殿 / 所在地 / 字大覚寺76-2'))
        self.assertEqual(correction_problems(proposal, *target), [])
        proof['unmarked_koaza']['shrine_site']['location_header_raw'] = '所有者の住所'
        self.assertTrue(correction_problems(proposal, *target))

    def test_environmental_cultural_inventory_requires_the_public_shrine_row(self):
        from njd.corporate_aza import _public_shrine_parcel_matches

        site = dict(url='https://kinki.env.go.jp/recycle/H29moderu_keikaku_tangoG.pdf',
                    source_kind='government_shrine_site', page_hash='a'*64,
                    checked_at='2026-11-20', locator='宮津市文化財一覧', item_raw='吉野神社',
                    address_raw='宮津市字文珠287', location_header_raw='住所',
                    item_type_raw='寺社', excerpt='吉野神社 / 宮津市字文珠287 / 寺社')
        fields = ('吉野神社', '宮津市', {'字文珠', '文珠'}, '宮ノ谷', '287')
        self.assertTrue(_public_shrine_parcel_matches(site, *fields))
        for field, value in (('item_type_raw', '建物'), ('location_header_raw', '所有者の住所'),
                             ('url', 'https://kinki.env.go.jp/unrelated.pdf'),
                             ('address_raw', '字文珠287')):
            with self.subTest(field=field):
                self.assertFalse(_public_shrine_parcel_matches({**site, field: value}, *fields))

    def test_nankoku_historical_row_only_expands_its_documented_locality(self):
        from njd.corporate_aza import _NANKOKU_LOCALITY_REPORT, _nankoku_koaza_matches

        witness = dict(url=_NANKOKU_LOCALITY_REPORT, page_hash='a'*64,
                       checked_at='2026-11-20', pdf_page=51,
                       address_expanded_for_comparison='南国市十市字溝本',
                       location_row=dict(map_no='269', address_raw='〝 〝 字溝本'),
                       ditto_context=[dict(map_no='260', address_raw='南国市稲生字蛸の森'),
                                      dict(map_no='261', address_raw='〝 十市字\n三ツ城・里改田字三ツ城他')])
        self.assertTrue(_nankoku_koaza_matches(witness, '十市', '溝本'))
        self.assertFalse(_nankoku_koaza_matches(witness, '十市', '別の字'))
        self.assertFalse(_nankoku_koaza_matches({**witness, 'ditto_context': []}, '十市', '溝本'))

    def test_chikuma_locality_needs_the_separate_same_parcel_office_record(self):
        from njd.corporate_aza import _CHIKUMA_CULTURAL_REPORT, _NAGANO_OFFICE_REGISTER, _chikuma_koaza_matches

        locality = dict(url=_CHIKUMA_CULTURAL_REPORT, page_hash='a'*64, checked_at='2026-11-20',
                        pdf_page=49, archaeological_site_address_raw='千曲市大字杭瀬下字東沖44番3他')
        office = dict(url=_NAGANO_OFFICE_REGISTER, page_hash='b'*64, checked_at='2026-11-20',
                      address_role='corporation_principal_office', address_field='事務所所在地',
                      municipality_raw='千曲市', name_raw='千曲神社', address_field_raw='大字杭瀬下東沖１８番地')
        context = dict(reference=locality, office_register=office)
        self.assertTrue(_chikuma_koaza_matches(context, '千曲神社', '大字杭瀬下', '東沖', '18'))
        self.assertFalse(_chikuma_koaza_matches(context, '千曲神社', '大字杭瀬下', '東沖', '18-1'))
        self.assertFalse(_chikuma_koaza_matches(context, '千曲神社', '大字杭瀬下', '東', '18'))
        self.assertFalse(_chikuma_koaza_matches(dict(reference=locality), '千曲神社', '大字杭瀬下', '東沖', '18'))

    def test_an_excluded_entry_stays_excluded_after_reapplication(self):
        proposal, (facility, entry, source) = example()
        entry['status'] = 'excluded'
        entry['reason'] = 'prior exclusion'
        data = dict(facilities=[facility], entries=[entry], collection=source)
        corrections = dict(schema_version=1, entries={entry['id']: proposal})
        first = apply_corrections(data, corrections)
        second = apply_corrections(first, corrections)
        self.assertEqual(second['entries'][0]['status'], 'excluded')
        self.assertEqual(second['entries'][0]['reason'], 'prior exclusion')
