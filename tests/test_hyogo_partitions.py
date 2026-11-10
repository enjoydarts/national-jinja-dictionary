"""Four explicit public-map searches compare observations, never certify a census."""
import unittest
from test_hyogo import Client,page
from njd.adapters import hyogo as h
from njd.http import FetchError

QUERIES=[h.ORIGIN+'/data/xml.php?ne_lat='+n+'&sw_lat='+s+'&ne_lng='+e+'&sw_lng='+w
    for s,n in [('34','35.01'),('34.99','36')]
    for w,e in [('134','135.01'),('134.99','136')]]
POINTS=[('6301001','34.5','134.5'),('6301002','34.5','135.5'),
        ('6301003','35.5','134.5'),('6301004','35.5','135.5'),('6301005','35','135')]


def xml(points):
    return '<Locations>'+''.join('<Locate><code>'+c+'</code><name>架空神社</name><place>架空市1</place><lat>'+lat+'</lat><lng>'+lng+'</lng></Locate>' for c,lat,lng in points)+'</Locations>'


def client():
    pages={h.PROTOCOL_URL:'var bounds = map.getBounds(); var url="data/xml.php?ne_lat=";',h.INDEX:xml(POINTS)}
    pages.update({u:xml([POINTS[i],POINTS[-1]]) for i,u in enumerate(QUERIES)})
    return Client(pages)


class HyogoPartitionTests(unittest.TestCase):
    def test_overlapping_responses_keep_native_identity_without_claiming_site_completeness(self):
        c=client();r=h.audit_map_partitions(c)
        self.assertEqual(r['partition_union_unique_codes'],5)
        self.assertEqual(r['overlap_observations'],3)
        self.assertTrue(r['consistent_comparison'])
        self.assertFalse(r['whole_site_inventory_confirmed'])
        self.assertFalse(r['api_cap_confirmed'])
        self.assertEqual(c.calls,[h.PROTOCOL_URL,h.INDEX]+QUERIES)

    def test_ignored_bounds_and_conflicting_names_are_not_silently_certified(self):
        c=client();c.pages[QUERIES[0]]=xml(POINTS).replace('架空神社','別神社',1)
        r=h.audit_map_partitions(c)
        self.assertFalse(r['consistent_comparison'])
        self.assertTrue(r['partitions'][0]['out_of_bounds_codes'])
        self.assertTrue(r['changed_codes'])

    def test_unrecognized_protocol_stops_before_api_requests(self):
        c=client();c.pages[h.PROTOCOL_URL]='changed protocol'
        with self.assertRaises(ValueError):h.audit_map_partitions(c)
        self.assertEqual(c.calls,[h.PROTOCOL_URL])

    def test_first_failed_partition_stops_later_requests(self):
        c=client();c.pages.pop(QUERIES[0])
        with self.assertRaises(FetchError):h.audit_map_partitions(c)
        self.assertEqual(c.calls,[h.PROTOCOL_URL,h.INDEX,QUERIES[0]])
