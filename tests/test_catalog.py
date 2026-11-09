import unittest

from njd.catalog import registry


class CatalogTests(unittest.TestCase):
    def test_mie_collection_is_available_through_the_public_registry(self):
        sources = registry()
        self.assertIn('mie', sources)
        self.assertEqual(sources['mie']['code'], '24')
        self.assertEqual(sources['mie']['agency'], '三重県神社庁')
        self.assertTrue(callable(sources['mie']['collect']))
