import unittest

from njd.catalog import registry


class CatalogTests(unittest.TestCase):
    def test_niigata_registry_selects_only_its_reviewed_html_origin(self):
        sources=registry()
        self.assertIn('niigata',sources)
        self.assertEqual(sources['niigata']['code'],'15')
        self.assertEqual(sources['niigata']['reviewed_html_robots'],('https://niigata-jinjacho.jp',))
        self.assertTrue(callable(sources['niigata']['collect']))
    def test_mie_collection_is_available_through_the_public_registry(self):
        sources = registry()
        self.assertIn('mie', sources)
        self.assertEqual(sources['mie']['code'], '24')
        self.assertEqual(sources['mie']['agency'], '三重県神社庁')
        self.assertTrue(callable(sources['mie']['collect']))
