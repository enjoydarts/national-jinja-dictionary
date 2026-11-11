import subprocess
import tempfile
import unittest
from pathlib import Path
from njd.changelog import generate_changelog, previous_release_tag, validate_version


class GitFixture(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.git('init','-b','main')

    def git(self,*args):
        return subprocess.run(['git','-c','user.name=Fixture','-c','user.email=fixture@example.invalid',
            '-c','commit.gpgsign=false',*args],cwd=self.root,check=True,capture_output=True,text=True).stdout.strip()


class HistoryTest(GitFixture):
    def test_initial_release_includes_history_and_referenced_pr(self):
        self.git('commit','--allow-empty','-m','Initial data')
        self.git('commit','--allow-empty','-m','Preserve [variant] characters (#12)')
        head=self.git('rev-parse','HEAD')
        text=generate_changelog(self.root,'owner/repo','v0.2.0',head,None)
        self.assertIn('Initial data',text)
        self.assertIn('Preserve \\[variant\\]',text)
        self.assertIn('https://github.com/owner/repo/pull/12',text)
        self.assertEqual(text,generate_changelog(self.root,'owner/repo','v0.2.0',head,None))

    def test_previous_published_reachable_tag_bounds_history(self):
        self.git('commit','--allow-empty','-m','Old release');self.git('tag','v0.1.0')
        self.git('checkout','-b','other');self.git('commit','--allow-empty','-m','Other branch');self.git('tag','v9.0.0')
        self.git('checkout','main');self.git('commit','--allow-empty','-m','New dictionary')
        head=self.git('rev-parse','HEAD')
        prev=previous_release_tag(self.root,head,['v0.1.0','v9.0.0'],'v0.2.0')
        self.assertEqual(prev,'v0.1.0')
        text=generate_changelog(self.root,'owner/repo','v0.2.0',head,prev)
        self.assertIn('New dictionary',text);self.assertNotIn('Old release',text)
        self.assertNotIn('Other branch',text)
        self.assertIn('compare/v0.1.0...v0.2.0',text)

    def test_version_input_cannot_inject_paths_flags_or_shell(self):
        for version in ['v1.2.3','v1.2.3-rc.1','v1.2.3+data.1']:validate_version(version)
        for version in ['../tag','--notes','v1.2','v01.2.3','v1.2.3;pwd','v1.2.3\nother']:
            with self.subTest(version=version),self.assertRaises(ValueError):validate_version(version)
