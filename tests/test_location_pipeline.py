import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from test_records import build, row
from test_corrections import correction
from njd.__main__ import _effective
from njd.nationwide import save_collection
from njd.proposals import import_proposals
from legacy_release import create_release
from njd.storage import write_json
from njd.validation import eligible, blocking_problems


def fixture(root):
    raw = build([row(address='', reading_raw='', source_id='https://shrine.example.invalid/',
                     official_url='https://shrine.example.invalid/')])
    save_collection(root, 'example', raw)
    f = raw['facilities'][0]
    address = '埼玉県架空市乙町1'
    item = dict(status='verified', facility_id=f['id'], expected_source_hash=f['source_hash'],
                original={k: f[k] for k in ('name_raw', 'address', 'municipality', 'listing_url', 'official_site_url', 'native_source_id')},
                changes=dict(address=address, municipality='架空市'),
                agency_link=dict(url=f['listing_url'], name_raw=f['name_raw'], href_raw=f['official_site_url'],
                                 locator=f['source_locator'], page_hash=f['page_hash'], fetched_at=f['fetched_at']),
                reference=dict(url='https://shrine.example.invalid/access', name_raw=f['name_raw'],
                               address_raw=address, excerpt='架空神社 / '+address, page_hash='b'*64,
                               fetched_at='2026-11-09T00:00:00+09:00', source_kind='official_shrine',
                               location_role='shrine', locator='shrine location'),
                reason='Exact agency link and named shrine location independently inspected')
    locations = dict(schema_version=1, facilities={f['id']: item})
    write_json(root/'locations.json', locations)
    readings = correction(raw, {'reading': 'かくうじんじゃ'})
    ref = readings['entries'][raw['entries'][0]['id']]['references'][0]
    ref.update(url='https://shrine.example.invalid/access', address_raw=address,
               excerpt='架空神社（かくうじんじゃ） '+address)
    return raw, locations, readings


class LocationPipelineTests(unittest.TestCase):
    def test_location_change_rechecks_cached_wikipedia_identity(self):
        from njd import wikipedia as w
        from test_wikipedia import FixtureClient, article
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            root = base/'data'
            raw, locations, readings = fixture(root)
            category = w.wiki_url('Category:埼玉県の神社')
            url = w.wiki_url('架空神社')
            client = FixtureClient({category: '<div id="mw-pages"><a href="'+url+'">架空神社</a></div>',
                                    url: article('架空神社', 'かくうじんじゃ', '島根県架空市乙町1').replace('島根県', '埼玉県')})
            first = w.research(root, base/'state', ['11'], client)
            self.assertEqual(first['proposals'], 1)
            record = locations['facilities'][raw['facilities'][0]['id']]
            record['changes']['address'] = '埼玉県架空市乙町2'
            record['reference'].update(address_raw='埼玉県架空市乙町2', excerpt='架空神社 / 埼玉県架空市乙町2')
            write_json(root/'locations.json', locations)
            again = w.research(root, base/'state', ['11'], client)
            self.assertEqual(again['articles_attempted'], 1)
            self.assertEqual(again['proposals'], 0)
    def test_corporate_research_keeps_the_original_empty_agency_address(self):
        from njd.wikipedia import pending_targets
        from njd.corporate import proposals_for_archive
        from test_corporate import row as corporate_row, archive, META
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            raw, locations, readings = fixture(root)
            targets = pending_targets(root, ['11'])
            body = archive([corporate_row(name='架空神社', furigana='カクウジンジャ',
                                        prefectureName='埼玉県', prefectureCode='11',
                                        cityName='架空市', streetNumber='乙町1')],
                           member='11_saitama_all_20261030.csv')
            proposals, pending = proposals_for_archive(body, targets, META)
            eid = raw['entries'][0]['id']
            self.assertIn(eid, proposals)
            self.assertEqual(proposals[eid]['original']['address'], '')
            self.assertEqual(proposals[eid]['identity_match']['agency_address'], '')
            self.assertEqual(proposals[eid]['identity_match']['effective_address'], '埼玉県架空市乙町1')
    def test_secondary_research_uses_location_but_keeps_the_original_snapshot(self):
        from njd.wikipedia import pending_targets, _proposal
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            raw, locations, readings = fixture(root)
            targets = pending_targets(root, ['11'])
            self.assertEqual(len(targets), 1)
            self.assertEqual(targets[0]['facility']['address'], '埼玉県架空市乙町1')
            ref = next(iter(readings['entries'].values()))['references'][0]
            proposal = _proposal(targets[0], ref)
            self.assertEqual(proposal['original']['address'], '')
            self.assertEqual(proposal['identity_match']['agency_address'], '')
            self.assertEqual(proposal['identity_match']['effective_address'], '埼玉県架空市乙町1')
    def test_effective_data_preserves_source_fingerprint_after_location_and_reading(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            raw, locations, readings = fixture(root)
            write_json(root/'corrections.json', readings)
            out = _effective(root, legacy=True)
            self.assertEqual(len(eligible(out)), 1)
            self.assertEqual(blocking_problems(out), [])
            f = out['facilities'][0]
            self.assertEqual(f['address'], '埼玉県架空市乙町1')
            self.assertEqual(f['location_supplement']['original']['address'], '')
            self.assertEqual(f['source_hash'], raw['facilities'][0]['source_hash'])
            self.assertEqual(out['entries'][0]['reading_raw'], '')

    def test_import_proposals_can_bind_to_valid_supplemented_location(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            raw, locations, readings = fixture(root)
            result = import_proposals(root, readings, apply=True)
            self.assertEqual(result['added'], 1)
            self.assertEqual(len(eligible(_effective(root, legacy=True))), 1)

    def test_offline_release_archives_location_evidence_and_is_reproducible(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            root = base/'data'
            raw, locations, readings = fixture(root)
            write_json(root/'corrections.json', readings)
            with patch('njd.http.request', side_effect=AssertionError('release stays offline')):
                result = create_release(root, base/'out', 'v0.2.0', 'a'*40)
                first = Path(result['archive']).read_bytes()
                again = create_release(root, base/'out', 'v0.2.0', 'a'*40)
            self.assertEqual(first, Path(again['archive']).read_bytes())
            with zipfile.ZipFile(result['archive']) as z:
                self.assertEqual(json.loads(z.read('locations.json')), locations)
                self.assertIn('locations.json', json.loads(z.read('SOURCE.json'))['data_files'])
                self.assertEqual(len(z.read('national/mozc.txt').splitlines()), 1)

    def test_stale_location_does_not_admit_the_saved_reading(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            raw, locations, readings = fixture(root)
            changed = copy.deepcopy(locations)
            changed['facilities'][raw['facilities'][0]['id']]['expected_source_hash'] = '0'*64
            write_json(root/'locations.json', changed)
            write_json(root/'corrections.json', readings)
            out = _effective(root, legacy=True)
            self.assertEqual(eligible(out), [])
            self.assertEqual(out['facilities'][0]['address'], '')
