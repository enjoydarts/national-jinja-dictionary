"""Synthetic cases: partial agency locality is bound by its actual official link."""
import copy
import unittest
from test_records import build, row
from test_corrections import correction
from njd.corrections import apply_corrections
from njd.validation import eligible


def candidate(spaced=False,address='架空市甲町'):
    d=build([row(name='架空神社',address=address,reading_raw='')])
    f=d['facilities'][0];f['official_site_url']='https://shrine.example.invalid/one/'
    c=correction(d,{'reading':'かくうじんじゃ'});v=next(iter(c['entries'].values()))
    r=v['references'][0];r.update(url=f['official_site_url']+'access',source_kind='official_shrine',
        page_hash='b'*64,locator='main address',address_raw='埼玉県架空市甲町字岩内17-2',reading_scope='full_name')
    r['address_identity_proof']=dict(kind='agency_linked_locality_with_aza',
        listing_address_raw=f['address'],official_address_raw=r['address_raw'])
    if spaced:
        r['reading_raw']='かくう じんじゃ'
        r['reading_normalization']=['remove printed reading spaces']
    r['excerpt']=f['listed_name']+'（'+r['reading_raw']+'） '+r['address_raw']
    v['official_site_binding']=dict(agency_link=dict(url=f['listing_url'],name_raw=f['name_raw'],
        address_raw=f['address'],href_raw=f['official_site_url'],locator=f['source_locator'],
        page_hash=f['page_hash'],fetched_at=f['fetched_at']))
    return d,c,r


class OfficialLocalityReadingTests(unittest.TestCase):
    def test_linked_official_aza_marker_preserves_the_exact_parcel(self):
        d,c,r=candidate(address='架空市甲町17');r['address_raw']='埼玉県架空市字甲町17'
        r['excerpt']=r['name_raw']+'（'+r['reading_raw']+'） '+r['address_raw']
        r['address_identity_proof'].update(kind='agency_linked_aza_marker',added_marker_raw='字',official_address_raw=r['address_raw'])
        self.assertEqual(len(eligible(apply_corrections(d,c))),1)
        for mutate in [lambda q:q['address_identity_proof'].pop('added_marker_raw'),
                lambda q:q['address_identity_proof'].update(added_marker_raw='大字'),
                lambda q:q.update(address_raw='埼玉県別市字甲町17'),
                lambda q:q.update(address_raw='埼玉県架空市字甲町170'),
                lambda q:q.update(address_raw='埼玉県架空市字別町17')]:
            with self.subTest(mutation=mutate):
                altered=copy.deepcopy(c);ref=next(iter(altered['entries'].values()))['references'][0];mutate(ref)
                if ref['address_raw']!=r['address_raw']:
                    ref['address_identity_proof']['official_address_raw']=ref['address_raw']
                    ref['excerpt']=ref['name_raw']+'（'+ref['reading_raw']+'） '+ref['address_raw']
                self.assertFalse(eligible(apply_corrections(d,altered)))

    def test_bound_full_address_extends_locality_without_rewriting_either_original(self):
        d,c,r=candidate();before=copy.deepcopy((d,c))
        out=apply_corrections(d,c)
        self.assertEqual(len(eligible(out)),1)
        self.assertEqual(out['facilities'][0]['address'],'架空市甲町')
        self.assertEqual(out['entries'][0]['reading_url'],r['url'])
        self.assertEqual((d,c),before)

    def test_unbound_other_subject_or_conflicting_parcel_remains_pending(self):
        mutations=[lambda v,r:v.pop('official_site_binding'),
            lambda v,r:r.pop('address_identity_proof'),
            lambda v,r:r.update(source_kind='reference'),
            lambda v,r:r.update(url='https://shrine.example.invalid/two/access'),
            lambda v,r:r.update(address_raw='埼玉県架空市甲町隣町字岩内17-2'),
            lambda v,r:r.update(address_raw='別県架空市甲町字岩内17-2'),
            lambda v,r:r['address_identity_proof'].update(listing_address_raw='別町'),
            lambda v,r:v['official_site_binding']['agency_link'].update(page_hash='c'*64)]
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                d,c,r=candidate();mutate(next(iter(c['entries'].values())),r)
                self.assertFalse(eligible(apply_corrections(d,c)))

    def test_existing_parcel_is_never_replaced_by_locality_extension(self):
        d,c,r=candidate();f=d['facilities'][0];v=next(iter(c['entries'].values()))
        f['address']='架空市甲町1';v['original']['address']=f['address']
        v['official_site_binding']['agency_link']['address_raw']=f['address']
        r['address_identity_proof']['listing_address_raw']=f['address']
        self.assertFalse(eligible(apply_corrections(d,c)))

    def test_explicit_space_normalization_keeps_literal_source_and_sets_reading_url(self):
        d,c,r=candidate(spaced=True);out=apply_corrections(d,c)
        self.assertEqual(len(eligible(out)),1)
        self.assertEqual(out['entries'][0]['reading'],'かくうじんじゃ')
        self.assertEqual(out['entries'][0]['correction']['references'][0]['reading_raw'],'かくう じんじゃ')
        self.assertEqual(out['entries'][0]['reading_url'],r['url'])

    def test_no_implicit_space_removal_or_control_character_repair(self):
        for raw,scope,steps in [('かくう じんじゃ','full_name',None),
                ('かくう\tじんじゃ','full_name',['remove printed reading spaces']),
                ('かくう じんじゃ','partial_or_absent',['remove printed reading spaces']),
                ('かくう じんじゃ','full_name',['infer reading']),
                (' かくうじんじゃ','full_name',['remove printed reading spaces'])]:
            with self.subTest(raw=raw,scope=scope,steps=steps):
                d,c,r=candidate(spaced=True);r.update(reading_raw=raw,reading_scope=scope)
                if steps is None:r.pop('reading_normalization')
                else:r['reading_normalization']=steps
                r['excerpt']=r['name_raw']+'（'+raw+'） '+r['address_raw']
                self.assertFalse(eligible(apply_corrections(d,c)))
