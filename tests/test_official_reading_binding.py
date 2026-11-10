"""Reading and location on separate official pages retain separate evidence."""
import copy
import unittest
from test_records import build,row
from test_corrections import correction
from njd.corrections import apply_corrections
from njd.validation import eligible


def candidate():
    d=build([row(name='架空神社',reading_raw='')]);f=d['facilities'][0]
    f['official_site_url']='https://shrine.example.invalid/one/'
    c=correction(d,{'reading':'かくうじんじゃ'});v=c['entries'][d['entries'][0]['id']]
    reading=v['references'][0];reading.update(url='https://shrine.example.invalid/one/about',source_kind='official_shrine',
        excerpt='架空神社（かくうじんじゃ）',page_hash='b'*64,locator='main p full-name reading')
    reading.pop('address_raw')
    address=copy.deepcopy(reading);address.update(url='https://shrine.example.invalid/one/access',
        address_raw=f['address'],excerpt=f['listed_name']+' / '+f['address'],page_hash='c'*64,locator='main address')
    address.pop('reading_raw')
    v['references'].append(address)
    v['official_site_binding']=dict(agency_link=dict(url=f['listing_url'],name_raw=f['name_raw'],
        address_raw=f['address'],href_raw=f['official_site_url'],locator=f['source_locator'],
        page_hash=f['page_hash'],fetched_at=f['fetched_at']))
    return d,c


class OfficialReadingBindingTests(unittest.TestCase):
    def test_separate_address_and_reading_need_the_bound_agency_link(self):
        d,c=candidate();old=copy.deepcopy(c)
        result=apply_corrections(d,c)
        self.assertEqual(len(eligible(result)),1)
        self.assertEqual(result['entries'][0]['reading'],'かくうじんじゃ')
        self.assertEqual(result['entries'][0]['reading_url'],'https://shrine.example.invalid/one/about')
        self.assertNotIn('address_raw',c['entries'][d['entries'][0]['id']]['references'][0])
        self.assertEqual(c,old)
        c['entries'][d['entries'][0]['id']].pop('official_site_binding')
        self.assertFalse(eligible(apply_corrections(d,c)))

    def test_other_account_wrong_address_or_corrupt_link_evidence_are_not_joined(self):
        mutations=[
            lambda v:v['references'][0].update(url='https://other.example.invalid/one/about'),
            lambda v:v['references'][0].update(url='https://shrine.example.invalid/two/about'),
            lambda v:v['references'][0].update(url='https://shrine.example.invalid/one/about?account=two'),
            lambda v:v['references'][0].update(url='https://shrine.example.invalid/one/../two/about'),
            lambda v:v['references'][0].update(address_raw='架空市別町9'),
            lambda v:v['references'][1].update(address_raw='架空市別町9'),
            lambda v:v['references'][0].update(name_raw='別神社'),
            lambda v:v['references'][0].update(source_kind='encyclopedia'),
            lambda v:v['official_site_binding']['agency_link'].update(page_hash='d'*64),
            lambda v:v['official_site_binding']['agency_link'].update(href_raw='https://shrine.example.invalid/two/'),
            lambda v:v['official_site_binding']['agency_link'].update(locator='wrong row'),
            lambda v:v['official_site_binding']['agency_link'].pop('fetched_at'),
            lambda v:v['official_site_binding'].update(agency_link=[]),
            lambda v:v.update(official_site_binding=[]),
            lambda v:v['references'][0].pop('locator'),
            lambda v:v['references'][1].pop('page_hash'),
        ]
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                d,c=candidate();v=c['entries'][d['entries'][0]['id']];mutate(v)
                self.assertFalse(eligible(apply_corrections(d,c)))

    def test_observed_continuous_redirect_can_authorize_a_changed_official_origin(self):
        d,c=candidate();v=c['entries'][d['entries'][0]['id']]
        for r in v['references']:r['url']=r['url'].replace('shrine.example.invalid','new.example.invalid')
        v['official_site_binding']['redirects']=[dict(from_url=d['facilities'][0]['official_site_url'],to_url='https://new.example.invalid/one/',status=301,page_hash='d'*64,fetched_at='2026-11-10T00:00:00+09:00')]
        self.assertEqual(len(eligible(apply_corrections(d,c))),1)
        v['official_site_binding']['redirects'][0]['from_url']='https://unrelated.example.invalid/'
        self.assertFalse(eligible(apply_corrections(d,c)))
