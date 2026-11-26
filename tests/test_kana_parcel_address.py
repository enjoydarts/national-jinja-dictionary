import unittest

from njd.corrections import apply_corrections
from njd.records import build_dataset
from njd.validation import eligible
from test_corrections import correction
from test_records import row


class KanaParcelAddressTest(unittest.TestCase):
    def fixture(self, address):
        dataset = build_dataset('nagano', '20', '長野県', '長野県神社庁', [
            row(name='佐良志奈神社', reading_raw='', address='千曲市大字若宮2番地－ｲ'),
        ])
        proposal = correction(dataset, {'reading': 'さらしなじんじゃ'})
        reference = proposal['entries'][dataset['entries'][0]['id']]['references'][0]
        reference.update(
            address_raw=address, excerpt='佐良志奈神社（さらしなじんじゃ） '+address,
        )
        return dataset, proposal

    def test_same_kana_branch_matches_with_both_published_forms_preserved(self):
        address = '〒389-0813 長野県千曲市若宮２−イ'
        dataset, proposal = self.fixture(address)
        updated = apply_corrections(dataset, proposal)
        self.assertEqual(len(eligible(updated)), 1)
        self.assertEqual(updated['facilities'], dataset['facilities'])
        self.assertEqual(updated['entries'][0]['correction']['references'][0]['address_raw'], address)

    def test_other_branch_or_parcel_remains_pending(self):
        for address in (
            '千曲市若宮2-1', '千曲市若宮2-ロ', '千曲市若宮20-イ',
            '千曲市若宮2-イ1', '千曲市中若宮2-イ', '千曲市若宮2',
        ):
            with self.subTest(address=address):
                dataset, proposal = self.fixture(address)
                self.assertEqual(eligible(apply_corrections(dataset, proposal)), [])
