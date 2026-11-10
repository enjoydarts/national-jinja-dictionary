"""Synthetic agency tables: literal fields, durable legacy IDs, no guessed kana."""
import unittest
from njd.http import Page,FetchError
from njd.records import build_dataset
from njd.adapters import nagasaki as n

ORIGIN='https://nagasaki-jinjacho.or.jp/'
HOME='<a href="search.html"><img alt="神社を探す"></a>'
INDEX='<div id="a-main"><a href="sasebo.html#甲">甲町</a><a href="sasebo.html#乙">乙町</a><a href="iki.html">壱岐</a></div>'
LEGACY='<div id="bk17860131"><a href="https://shrine.example.invalid/">旧掲載神社</a><a href="https://social.example.invalid/one">未対応神社</a></div>'
HEADER='<tr>'+''.join('<td>'+v+'</td>' for v in ['番号','神社名','祭神名','旧社格','例祭日','郵便番号','鎮座地'])+'</tr>'
def table(rows):
    return '<table>'+HEADER+''.join('<tr>'+''.join('<td>'+v+'</td>' for v in r)+'</tr>' for r in rows)+'</table>'
def row(number,name,address):return [number,name,'DEITY DO NOT COLLECT','旧社格','9月1日','850-0000',address]
def page(url,text):return Page(url,200,{},text.encode(),'2026-11-10T00:00:00+00:00')
class Client:
    def __init__(self,pages):self.pages=pages;self.calls=[]
    def fetch(self,url):
        self.calls.append(url)
        if url not in self.pages:raise FetchError('missing fixture')
        return page(url,self.pages[url])
def client():
    return Client({ORIGIN:HOME,ORIGIN+'search.html':INDEX,ORIGIN+'link.html':LEGACY,
        ORIGIN+'sasebo.html':table([row('1','<a href="https://shrine.example.invalid">現掲載神社</a>','佐世保市甲町1'),row('2','同名神社','佐世保市乙町2')]),
        ORIGIN+'iki.html':table([row('1','同名神社','壱岐市甲町3')])})

class NagasakiRegionsTests(unittest.TestCase):
    def test_image_link_and_real_index_hrefs_are_followed_once(self):
        c=client();d=n.collect_nagasaki(c)
        self.assertEqual(c.calls,[ORIGIN,ORIGIN+'search.html',ORIGIN+'link.html',ORIGIN+'sasebo.html',ORIGIN+'iki.html'])
        self.assertEqual(len(d['facilities']),4)
        self.assertTrue(d['collection']['traversal_complete'])
        self.assertEqual(d['collection']['source_rows_observed'],5)
        self.assertTrue(all(e['reading_raw']=='' and e['status']=='pending' for e in d['entries']))
        self.assertNotIn('DEITY DO NOT COLLECT',str(d))

    def test_unique_website_link_preserves_legacy_id_but_keeps_both_source_names(self):
        d=n.collect_nagasaki(client());f=next(f for f in d['facilities'] if f['listed_name']=='現掲載神社')
        from uuid import uuid5,NAMESPACE_URL
        self.assertEqual(f['id'],str(uuid5(NAMESPACE_URL,'nagasaki|native|https://shrine.example.invalid/')))
        self.assertEqual(f['legacy_link_observation']['name_raw'],'旧掲載神社')
        self.assertEqual(f['address'],'佐世保市甲町1')
        self.assertEqual(len([f for f in d['facilities'] if f['listed_name']=='同名神社']),2)

    def test_same_name_without_an_exact_link_is_never_used_for_merging(self):
        c=client();c.pages[ORIGIN+'sasebo.html']=table([row('1','旧掲載神社','佐世保市甲町1')])
        d=n.collect_nagasaki(c)
        self.assertEqual(len([f for f in d['facilities'] if f['listed_name']=='旧掲載神社']),2)

    def test_duplicate_name_and_address_in_different_sections_are_held_separately(self):
        c=client();c.pages[ORIGIN+'iki.html']=table([row('1','同名神社','佐世保市乙町2')])
        d=n.collect_nagasaki(c);fs=[f for f in d['facilities'] if f['listed_name']=='同名神社']
        self.assertEqual(len(fs),2);self.assertEqual(len({f['id'] for f in fs}),2)
        self.assertTrue(all(f['status']=='pending' for f in fs))
        self.assertTrue(all(e.get('identity_review_required') for e in d['entries'] if e['facility_id'] in {f['id'] for f in fs}))

    def test_duplicate_identity_cannot_consume_a_preserved_legacy_link_id(self):
        c=client();c.pages[ORIGIN+'iki.html']=table([row('1','<a href="https://shrine.example.invalid">現掲載神社</a>','佐世保市甲町1')])
        # Only one of the duplicate observations links to the old website.
        c.pages[ORIGIN+'sasebo.html']=table([row('1','現掲載神社','佐世保市甲町1')])
        d=n.collect_nagasaki(c)
        from uuid import uuid5,NAMESPACE_URL
        old_id=str(uuid5(NAMESPACE_URL,'nagasaki|native|https://shrine.example.invalid/'))
        self.assertIn(old_id,{f['id'] for f in d['facilities']})
        self.assertEqual(d['collection']['matched_legacy_links'],0)

    def test_glyph_annotation_cannot_attach_across_table_boundaries(self):
        c=client();c.pages[ORIGIN+'iki.html']=table([row('1','甲神社','壱岐市甲町1')])+table([['','(外字注記)','','','','','']])
        with self.assertRaises(ValueError):n.collect_nagasaki(c)

    def test_external_glyph_note_is_preserved_without_creating_or_guessing_a_shrine(self):
        c=client();c.pages[ORIGIN+'iki.html']=table([row('1','阿麻テ留神社','対馬市甲町1'),['','(テは氏に下線=テイ)','','','','','']])
        d=n.collect_nagasaki(c);f=next(f for f in d['facilities'] if f['name_raw']=='阿麻テ留神社')
        self.assertEqual(f['status'],'pending');self.assertEqual(f['name_annotation_raw'],'(テは氏に下線=テイ)')
        self.assertFalse(any('氏' in f['listed_name'] for f in d['facilities']))

    def test_acquisition_failure_keeps_previous_snapshot_and_never_fetches_later_pages(self):
        c=client();c.pages.pop(ORIGIN+'sasebo.html')
        with self.assertRaises(FetchError):n.collect_nagasaki(c)
        self.assertNotIn(ORIGIN+'iki.html',c.calls)

    def test_limit_is_a_facility_limit_and_marks_unselected_scope(self):
        d=n.collect_nagasaki(client(),limit=2)
        self.assertEqual(len(d['facilities']),2)
        self.assertFalse(d['collection']['collection_complete'])
        self.assertTrue(d['collection']['remaining_scope'])

    def test_external_index_target_and_ambiguous_table_structure_are_rejected(self):
        c=client();c.pages[ORIGIN+'search.html']=INDEX.replace('iki.html','https://elsewhere.example.invalid/iki.html')
        with self.assertRaises(ValueError):n.collect_nagasaki(c)
        self.assertFalse(any('elsewhere' in u for u in c.calls))
        c=client();c.pages[ORIGIN+'sasebo.html']=c.pages[ORIGIN+'sasebo.html'].replace('鎮座地','説明')
        with self.assertRaises(ValueError):n.collect_nagasaki(c)
