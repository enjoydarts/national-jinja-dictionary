"""Synthetic document facts; never evidence for real shrine readings."""
import copy
import unittest
from test_records import build, row
from test_corrections import correction
from njd.corrections import apply_corrections
from njd.validation import eligible, validate


def fixture():
    data = build([row(reading_raw='', address='架空市乙町1061')])
    doc = correction(data, {'reading': 'かくうじんじゃ'})
    ref = next(iter(doc['entries'].values()))['references'][0]
    ref.update(url='https://city.example.invalid/report.pdf', page_hash='b'*64,
               source_kind='municipality_hosted_citizen_university_report',
               reading_scope='full_name', address_raw='乙町 1061', pdf_pages=10,
               source_page_index=3, source_card_number=18,
               table_heading_raw='架空の神社一覧表（50音順）',
               locator='PDF index3, card18',
               excerpt='架空神社 / かくうじんじゃ / 乙町 1061')
    ref['document_address_context'] = dict(kind='same_document_explicit_municipality',
        url=ref['url'], page_hash=ref['page_hash'], checked_at=ref['checked_at'],
        municipality_raw='架空市', scope_raw='架空市の神社',
        excerpt='テーマ「架空市の神社」を確認', locator='PDF index2, activity3',
        source_page_index=2, table_heading_raw=ref['table_heading_raw'], record_number=18,
        table_heading_page_index=3, table_heading_locator='PDF index3, table heading',
        table_heading_excerpt=ref['table_heading_raw'])
    return data, doc, ref


class DocumentContextTest(unittest.TestCase):
    def test_repeated_context_correction_keeps_exclusion_and_its_reason(self):
        for corrupt in (False, True):
            with self.subTest(corrupt=corrupt):
                data, doc, ref = fixture()
                data['entries'][0].update(status='excluded', reason='Explicit existing exclusion')
                before = copy.deepcopy(data)
                if corrupt: ref['document_address_context']['page_hash'] = 'c'*64
                out = data
                for _ in range(3):
                    out = apply_corrections(out, doc)
                    self.assertEqual(out['entries'][0]['status'], 'excluded')
                    self.assertEqual(out['entries'][0]['reason'], 'Explicit existing exclusion')
                    self.assertEqual(eligible(out), [])
                self.assertEqual(data, before)

    def test_legacy_descriptive_address_context_keeps_ordinary_reference_behavior(self):
        data = build([row(reading_raw='')])
        doc = correction(data, {'reading': 'かくうじんじゃ'})
        ref = next(iter(doc['entries'].values()))['references'][0]
        ref['address_context'] = 'Existing descriptive note; not a structured document proof.'
        self.assertEqual(len(eligible(apply_corrections(data, doc))), 1)

    def test_literal_locality_with_digit_width_and_explicit_units(self):
        data, doc, ref = fixture()
        ref['address_raw'] = '乙町 １０６１番地'
        ref['excerpt'] = '架空神社 / かくうじんじゃ / 乙町 １０６１番地'
        self.assertEqual(len(eligible(apply_corrections(data, doc))), 1)

    def test_continuation_page_binds_earlier_heading_without_inventing_a_quote(self):
        data, doc, ref = fixture()
        ref.update(source_page_index=4, excerpt='架空神社 / かくうじんじゃ / 乙町 1061')
        ref['document_address_context'].update(table_heading_page_index=3,
            table_heading_locator='PDF index3, table heading',
            table_heading_excerpt='架空の神社一覧表（50音順）')
        out = apply_corrections(data, doc)
        self.assertEqual(len(eligible(out)), 1)
        self.assertEqual(ref['excerpt'], '架空神社 / かくうじんじゃ / 乙町 1061')

    def test_explicit_context_resolves_without_rewriting_raw_fields(self):
        data, doc, ref = fixture(); before = copy.deepcopy(data); evidence = copy.deepcopy(doc)
        out = apply_corrections(data, doc)
        self.assertEqual(len(eligible(out)), 1)
        self.assertEqual(out['entries'][0]['reading'], 'かくうじんじゃ')
        self.assertEqual(out['entries'][0]['reading_url'], ref['url'])
        self.assertEqual(out['entries'][0]['reading_raw'], '')
        self.assertEqual(out['facilities'], data['facilities'])
        self.assertEqual(ref['address_raw'], '乙町 1061')
        self.assertEqual(data, before); self.assertEqual(doc, evidence)
        self.assertEqual(validate(out), [])
        self.assertEqual(apply_corrections(out, doc), out)

    def test_document_and_table_binding_is_required(self):
        edits = [
            lambda r: r.pop('document_address_context'),
            lambda r: r.update(source_kind='official_agency'),
            lambda r: r.update(reading_scope='partial_or_absent'),
            lambda r: r.update(page_hash='c'*64),
            lambda r: r.update(source_page_index=10),
            lambda r: r.update(source_page_index=True),
            lambda r: r.update(source_card_number=19),
            lambda r: r.pop('locator'),
            lambda r: r['document_address_context'].update(table_heading_excerpt='別の表'),
            lambda r: r['document_address_context'].update(table_heading_page_index=4),
            lambda r: r['document_address_context'].pop('table_heading_locator'),
            lambda r: r['document_address_context'].update(kind='municipality_guess'),
            lambda r: r['document_address_context'].update(url='https://other.example.invalid/report.pdf'),
            lambda r: r['document_address_context'].update(page_hash='c'*64),
            lambda r: r['document_address_context'].update(checked_at='2026-11-09'),
            lambda r: r['document_address_context'].update(municipality_raw='別市'),
            lambda r: r['document_address_context'].update(scope_raw='周辺の神社'),
            lambda r: r['document_address_context'].update(excerpt='市内の神社'),
            lambda r: r['document_address_context'].update(locator=''),
            lambda r: r['document_address_context'].update(source_page_index=4),
            lambda r: r['document_address_context'].update(source_page_index=-1),
            lambda r: r['document_address_context'].update(table_heading_raw='別の一覧表'),
            lambda r: r['document_address_context'].update(record_number=17),
        ]
        for i, edit in enumerate(edits):
            with self.subTest(case=i):
                data, doc, ref = fixture(); edit(ref)
                self.assertEqual(eligible(apply_corrections(data, doc)), [])

    def test_same_name_never_supplies_another_locality_or_parcel(self):
        for address in ['乙町1061-1', '乙町106', '乙町10610', '甲町1061',
                        '乙町字岩内1061', '別市乙町1061', '乙町', '']:
            with self.subTest(address=address):
                data, doc, ref = fixture(); ref['address_raw'] = address
                ref['excerpt'] = ref['table_heading_raw']+' / 架空神社 / かくうじんじゃ / '+address
                self.assertEqual(eligible(apply_corrections(data, doc)), [])

    def test_invalid_context_cannot_fall_back_to_a_complete_address(self):
        data, doc, ref = fixture()
        ref['address_raw'] = '架空市乙町1061'; ref['excerpt'] += ' / 架空市乙町1061'
        ref['document_address_context']['page_hash'] = 'c'*64
        self.assertEqual(eligible(apply_corrections(data, doc)), [])

    def test_context_cannot_resolve_other_holds_or_change_name(self):
        for hold in ['identity', 'excluded', 'facility', 'authority', 'surface']:
            with self.subTest(hold=hold):
                data, doc, ref = fixture()
                if hold == 'identity': data['entries'][0]['identity_review_required'] = True
                if hold == 'excluded': data['entries'][0]['status'] = 'excluded'
                if hold == 'facility': data['facilities'][0].update(status='pending', reason='identity unresolved')
                if hold == 'authority': data['collection']['authority_status'] = 'unconfirmed'
                if hold == 'surface': next(iter(doc['entries'].values()))['changes']['surface'] = '架空神社'
                self.assertEqual(eligible(apply_corrections(data, doc)), [])

    def test_malformed_context_is_held_and_applied_corruption_stops_output(self):
        bad = [None, [], 7, '', True]
        for value in bad:
            data, doc, ref = fixture(); ref['document_address_context'] = value
            self.assertEqual(eligible(apply_corrections(data, doc)), [])
        data, doc, ref = fixture()
        for field in ref['document_address_context']:
            for value in bad:
                with self.subTest(field=field, value=value):
                    data, doc, ref = fixture(); ref['document_address_context'][field] = value
                    self.assertEqual(eligible(apply_corrections(data, doc)), [])
        data, doc, ref = fixture(); out = apply_corrections(data, doc)
        self.assertEqual(len(eligible(out)), 1)
        out['entries'][0]['correction']['references'][0]['document_address_context']['page_hash'] = 'c'*64
        self.assertTrue(validate(out)); self.assertEqual(eligible(out), [])
        ref['document_address_context']['page_hash'] = 'c'*64
        self.assertEqual(eligible(apply_corrections(out, doc)), [])
