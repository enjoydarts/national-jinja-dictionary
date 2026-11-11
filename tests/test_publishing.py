import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from njd.publishing import run_release
from njd.release import create_release
from njd.nationwide import save_collection
from test_changelog import GitFixture
from test_records import build,row


class FakeGitHub:
    def __init__(self):
        self.tag=None;self.release=None;self.items={};self.mutations=[];self.fail_upload=None
    def resolve_tag(self,tag):return self.tag
    def published_tags(self):return []
    def create_tag(self,tag,commit):self.tag=commit;self.mutations.append('tag')
    def find_release(self,tag):return self.release
    def create_draft(self,tag,commit,body):
        self.release=dict(id=1,draft=True,body=body,html_url='https://github.com/owner/repo/releases/tag/'+tag)
        self.mutations.append('draft');return self.release
    def assets(self,rid):return list(self.items.values())
    def upload(self,rid,path):
        if path.name==self.fail_upload:raise RuntimeError('interrupted upload')
        self.items[path.name]=dict(name=path.name,state='uploaded',digest='sha256:'+hashlib.sha256(path.read_bytes()).hexdigest())
        self.mutations.append('upload:'+path.name)
    def publish(self,rid,body):
        self.release['draft']=False;self.mutations.append('publish')


class PublishingTest(GitFixture):
    def setUp(self):
        super().setUp();self.api=FakeGitHub()
        (self.root/'njd').mkdir();(self.root/'njd/__init__.py').write_text('')
        save_collection(self.root/'data','example',build([row()]))
        self.git('add','.');self.git('commit','-m','Initial canonical data')
        self.commit=self.git('rev-parse','HEAD')
        self.output=Path(self.tmp.name)/'build-output'
        # Ignore generation just as the real repository ignores dist/.
        (self.root/'.git/info/exclude').write_text('build-output/\n')
    def run_release(self,**kwargs):
        return run_release(self.root,'owner/repo','v0.2.0',self.api,self.output,**kwargs)

    def test_generation_precedes_tag_and_all_uploads_precede_publish(self):
        def generator(*args,**kwargs):
            self.assertEqual(self.api.mutations,[])
            return create_release(*args,**kwargs)
        result=self.run_release(generator=generator)
        self.assertEqual(result['status'],'published')
        self.assertEqual(self.api.mutations[:2],['tag','draft'])
        self.assertEqual(self.api.mutations[-1],'publish')
        self.assertEqual(set(self.api.items),{'national-jinja-dictionary-v0.2.0.zip','SHA256SUMS','SOURCE.json','CHANGELOG.md'})
        with zipfile.ZipFile(result['archive']) as archive:
            self.assertEqual(archive.read('CHANGELOG.md'),(self.output/'CHANGELOG.md').read_bytes())

    def test_generation_failure_and_dry_run_do_not_create_tag_or_release(self):
        def fail(*args,**kwargs):raise ValueError('canonical data failed')
        with self.assertRaises(ValueError):self.run_release(generator=fail)
        self.assertEqual(self.api.mutations,[])
        result=self.run_release(dry_run=True)
        self.assertEqual(result['status'],'dry_run')
        self.assertEqual(self.api.mutations,[])
        self.assertTrue((self.output/'CHANGELOG.md').exists())

    def test_conflicting_tag_stops_without_mutation(self):
        self.api.tag='b'*40
        with self.assertRaisesRegex(ValueError,'tag'):self.run_release()
        self.assertEqual(self.api.mutations,[])

    def test_partial_upload_can_resume_without_replacing_assets(self):
        self.api.fail_upload='SOURCE.json'
        with self.assertRaises(RuntimeError):self.run_release()
        self.assertTrue(self.api.release['draft'])
        self.api.fail_upload=None;before=list(self.api.mutations)
        self.run_release()
        self.assertFalse(self.api.release['draft'])
        self.assertEqual(self.api.mutations.count('tag'),1)
        self.assertEqual(self.api.mutations.count('upload:SHA256SUMS'),1)
        self.assertTrue(before)

    def test_published_identical_retry_is_noop_and_mismatch_never_clobbers(self):
        self.run_release();before=list(self.api.mutations)
        self.assertEqual(self.run_release()['status'],'already_published')
        self.assertEqual(self.api.mutations,before)
        self.api.items['SOURCE.json']['digest']='sha256:'+'0'*64
        with self.assertRaisesRegex(ValueError,'asset'):self.run_release()
        self.assertEqual(self.api.mutations,before)

    def test_retry_reuses_saved_baseline_after_new_release_history_appears(self):
        self.run_release();before=list(self.api.mutations)
        self.git('tag','v0.2.1')
        self.api.published_tags=lambda:['v0.2.1']
        self.assertEqual(self.run_release()['status'],'already_published')
        self.assertEqual(self.api.mutations,before)

    def test_supported_build_suffix_generates_end_to_end(self):
        result=run_release(self.root,'owner/repo','v0.2.0+data.1',self.api,self.output,dry_run=True)
        self.assertTrue(Path(result['archive']).exists())
        sums=(self.output/'SHA256SUMS').read_text().splitlines()
        for line in sums:
            digest,name=line.split('  ',1)
            self.assertEqual(hashlib.sha256((self.output/name).read_bytes()).hexdigest(),digest)

    def test_version_without_v_uses_canonical_tag_and_can_resume(self):
        result=run_release(self.root,'owner/repo','0.1.0',self.api,self.output)
        self.assertEqual(result['status'],'published')
        self.assertEqual(self.api.release['html_url'],'https://github.com/owner/repo/releases/tag/v0.1.0')
        source=json.loads((self.output/'SOURCE.json').read_text())
        self.assertEqual(source['version'],'v0.1.0')
        self.assertIn('CHANGELOG — v0.1.0',(self.output/'CHANGELOG.md').read_text())
        before=list(self.api.mutations)
        result=run_release(self.root,'owner/repo','v0.1.0',self.api,self.output)
        self.assertEqual(result['status'],'already_published')
        self.assertEqual(self.api.mutations,before)
