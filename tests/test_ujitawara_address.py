"""Synthetic tests for a documented omission of address markers."""
import copy
import unittest

from njd.corrections import apply_corrections
from njd.records import build_dataset
from njd.validation import eligible
from test_corrections import correction
from test_records import row


def fixture():
    printed = '綴喜郡宇治田原町大字架空小字月丘39-1'
    data = build_dataset('kyoto', '26', '京都府', 'Synthetic agency', [
        row(name='架空神社', reading_raw='', address=printed)])
    doc = correction(data, {'reading': 'かくうじんじゃ'})
    entry = data['entries'][0]
    ref = doc['entries'][entry['id']]['references'][0]
    ref.update(
        page_hash='b'*64, reading_scope='full_name', locator='訪問記の見出しと住所',
        address_raw='宇治田原町架空月丘３９－１',
        excerpt='架空神社（かくうじんじゃ） / 宇治田原町架空月丘３９－１',
    )
    ref['address_identity_proof'] = dict(
        kind='ujitawara_documented_koaza_marker', expected_source_hash=entry['source_hash'],
        reference_page_hash=ref['page_hash'], agency_address_raw=printed,
        municipality_witness=dict(
            url='https://ujitawara-kyoto.com/example/', page_hash='c'*64,
            checked_at=ref['checked_at'], name_raw='架空神社',
            address_raw='宇治田原町大字架空小字月丘', locator='個別の社名と所在地',
            excerpt='架空神社 / 宇治田原町大字架空小字月丘',
        ),
    )
    return data, doc, ref


class UjitawaraAddressTest(unittest.TestCase):
    def test_markers_can_be_omitted_when_the_locality_and_entire_parcel_match(self):
        data, doc, ref = fixture()
        before = copy.deepcopy((data, doc))
        out = apply_corrections(data, doc)
        self.assertEqual(len(eligible(out)), 1)
        self.assertEqual(out['entries'][0]['reading'], 'かくうじんじゃ')
        self.assertEqual(out['facilities'], data['facilities'])
        self.assertEqual(ref['address_raw'], '宇治田原町架空月丘３９－１')
        self.assertEqual((data, doc), before)

    def test_uncorroborated_or_different_addresses_are_held(self):
        for field, value in (
            ('address_raw', '宇治田原町架空月丘39'),
            ('address_raw', '宇治田原町架空月丘39-11'),
            ('address_raw', '宇治田原町架空別丘39-1'),
            ('address_raw', '架空町架空月丘39-1'),
            ('address_raw', '宇治田原町架空月丘'),
        ):
            with self.subTest(field=field, value=value):
                data, doc, ref = fixture()
                ref[field] = value
                ref['excerpt'] = '架空神社（かくうじんじゃ） / ' + value
                self.assertEqual(eligible(apply_corrections(data, doc)), [])

        for field, value in (
            ('address_raw', '宇治田原町大字架空小字月丘39-2'),
            ('address_raw', '宇治田原町大字架空小字別丘'),
            ('name_raw', '別神社'),
            ('page_hash', 'not-a-hash'),
            ('url', 'https://unrelated.example.invalid/example/'),
        ):
            with self.subTest(witness_field=field, value=value):
                data, doc, ref = fixture()
                witness = ref['address_identity_proof']['municipality_witness']
                witness[field] = value
                witness['excerpt'] = witness['name_raw']+' / '+witness['address_raw']
                self.assertEqual(eligible(apply_corrections(data, doc)), [])

    def test_invalid_proof_cannot_be_hidden_with_another_reference(self):
        data, doc, ref = fixture()
        alternate = correction(data, {'reading': 'かくうじんじゃ'})
        next(iter(doc['entries'].values()))['references'].extend(
            next(iter(alternate['entries'].values()))['references'])
        ref['address_identity_proof']['reference_page_hash'] = 'd'*64
        self.assertEqual(eligible(apply_corrections(data, doc)), [])

    def test_witness_must_be_a_separate_page(self):
        data, doc, ref = fixture()
        ref['url'] = ref['address_identity_proof']['municipality_witness']['url']
        self.assertEqual(eligible(apply_corrections(data, doc)), [])

    def test_existing_exclusion_remains_excluded(self):
        data, doc, _ = fixture()
        data['entries'][0].update(status='excluded', reason='existing exclusion')
        for _ in range(2):
            data = apply_corrections(data, doc)
            self.assertEqual(data['entries'][0]['status'], 'excluded')
