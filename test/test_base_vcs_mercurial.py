import os
import shutil
import subprocess
import sys
import tempfile
import unittest

try:
    import simplejson as json
except ImportError:
    import json

import mozharness.base.errors as errors
import mozharness.base.vcs.mercurial as mercurial

test_string = '''foo
bar
baz'''

def cleanup():
    if os.path.exists('test_logs'):
        shutil.rmtree('test_logs')
    if os.path.exists('test_dir'):
        if os.path.isdir('test_dir'):
            shutil.rmtree('test_dir')
        else:
            os.remove('test_dir')
    for filename in ('localconfig.json', 'localconfig.json.bak'):
        if os.path.exists(filename):
            os.remove(filename)

def get_mercurial_vcs_obj():
    m = mercurial.MercurialVCS()
    m.config = {}
    return m

def get_revisions(dest):
    m = get_mercurial_vcs_obj()
    retval = []
    for rev in m.get_output_from_command(['hg', 'log', '-R', dest, '--template', '{node|short}\n']).split('\n'):
        rev = rev.strip()
        if not rev:
            continue
        retval.append(rev)
    return retval

class TestMakeAbsolute(unittest.TestCase):
    def testAbsolutePath(self):
        m = get_mercurial_vcs_obj()
        self.assertEquals(m._make_absolute("/foo/bar"), "/foo/bar")

    def testRelativePath(self):
        m = get_mercurial_vcs_obj()
        self.assertEquals(m._make_absolute("foo/bar"), os.path.abspath("foo/bar"))

    def testHTTPPaths(self):
        m = get_mercurial_vcs_obj()
        self.assertEquals(m._make_absolute("http://foo/bar"), "http://foo/bar")

    def testAbsoluteFilePath(self):
        m = get_mercurial_vcs_obj()
        self.assertEquals(m._make_absolute("file:///foo/bar"), "file:///foo/bar")

    def testRelativeFilePath(self):
        m = get_mercurial_vcs_obj()
        self.assertEquals(m._make_absolute("file://foo/bar"), "file://%s/foo/bar" % os.getcwd())



class TestHg(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.repodir = os.path.join(self.tmpdir, 'repo')
        m = get_mercurial_vcs_obj()
        m.run_command("%s/helper_files/init_hgrepo.sh %s" % (os.path.dirname(__file__),
                      self.repodir))
        self.revisions = get_revisions(self.repodir)
        self.wc = os.path.join(self.tmpdir, 'wc')
        self.pwd = os.getcwd()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)
        os.chdir(self.pwd)

    def testGetBranch(self):
        m = get_mercurial_vcs_obj()
        m.clone(self.repodir, self.wc)
        b = m.get_branch_from_path(self.wc)
        self.assertEquals(b, 'default')

    def testGetBranches(self):
        m = get_mercurial_vcs_obj()
        m.clone(self.repodir, self.wc)
        branches = m.get_branches_from_path(self.wc)
        self.assertEquals(sorted(branches), sorted(["branch2", "default"]))

    def testClone(self):
        m = get_mercurial_vcs_obj()
        rev = m.clone(self.repodir, self.wc, update_dest=False)
        self.assertEquals(rev, None)
        self.assertEquals(self.revisions, get_revisions(self.wc))
        self.assertEquals(sorted(os.listdir(self.wc)), ['.hg'])

    def testCloneIntoNonEmptyDir(self):
        m = get_mercurial_vcs_obj()
        m.mkdir_p(self.wc)
        open(os.path.join(self.wc, 'test.txt'), 'w').write('hello')
        m.clone(self.repodir, self.wc, update_dest=False)
        self.failUnless(not os.path.exists(os.path.join(self.wc, 'test.txt')))

    def testCloneUpdate(self):
        m = get_mercurial_vcs_obj()
        rev = m.clone(self.repodir, self.wc, update_dest=True)
        self.assertEquals(rev, self.revisions[0])

    def testCloneBranch(self):
        m = get_mercurial_vcs_obj()
        m.clone(self.repodir, self.wc, branch='branch2',
                update_dest=False)
        # On hg 1.6, we should only have a subset of the revisions
        if m.hg_ver() >= (1,6,0):
            self.assertEquals(self.revisions[1:],
                              get_revisions(self.wc))
        else:
            self.assertEquals(self.revisions,
                              get_revisions(self.wc))

    def testCloneUpdateBranch(self):
        m = get_mercurial_vcs_obj()
        rev = m.clone(self.repodir, os.path.join(self.tmpdir, 'wc'),
                      branch="branch2", update_dest=True)
        self.assertEquals(rev, self.revisions[1], self.revisions)

    def testCloneRevision(self):
        m = get_mercurial_vcs_obj()
        m.clone(self.repodir, self.wc,
                revision=self.revisions[0], update_dest=False)
        # We'll only get a subset of the revisions
        self.assertEquals(self.revisions[:1] + self.revisions[2:],
                          get_revisions(self.wc))

    def testUpdateRevision(self):
        m = get_mercurial_vcs_obj()
        rev = m.clone(self.repodir, self.wc, update_dest=False)
        self.assertEquals(rev, None)

        rev = m.update(self.wc, revision=self.revisions[1])
        self.assertEquals(rev, self.revisions[1])

    def testPull(self):
        m = get_mercurial_vcs_obj()
        # Clone just the first rev
        m.clone(self.repodir, self.wc, revision=self.revisions[-1], update_dest=False)
        self.assertEquals(get_revisions(self.wc), self.revisions[-1:])

        # Now pull in new changes
        rev = m.pull(self.repodir, self.wc, update_dest=False)
        self.assertEquals(rev, None)
        self.assertEquals(get_revisions(self.wc), self.revisions)

    def testPullRevision(self):
        m = get_mercurial_vcs_obj()
        # Clone just the first rev
        m.clone(self.repodir, self.wc, revision=self.revisions[-1], update_dest=False)
        self.assertEquals(get_revisions(self.wc), self.revisions[-1:])

        # Now pull in just the last revision
        rev = m.pull(self.repodir, self.wc, revision=self.revisions[0], update_dest=False)
        self.assertEquals(rev, None)

        # We'll be missing the middle revision (on another branch)
        self.assertEquals(get_revisions(self.wc), self.revisions[:1] + self.revisions[2:])

    def testPullBranch(self):
        m = get_mercurial_vcs_obj()
        # Clone just the first rev
        m.clone(self.repodir, self.wc, revision=self.revisions[-1], update_dest=False)
        self.assertEquals(get_revisions(self.wc), self.revisions[-1:])

        # Now pull in the other branch
        rev = m.pull(self.repodir, self.wc, branch="branch2", update_dest=False)
        self.assertEquals(rev, None)

        # On hg 1.6, we'll be missing the last revision (on another branch)
        if m.hg_ver() >= (1,6,0):
            self.assertEquals(get_revisions(self.wc), self.revisions[1:])
        else:
            self.assertEquals(get_revisions(self.wc), self.revisions)

    def testPullUnrelated(self):
        m = get_mercurial_vcs_obj()
        # Create a new repo
        repo2 = os.path.join(self.tmpdir, 'repo2')
        m.run_command(['%s/helper_files/init_hgrepo.sh' % os.path.dirname(__file__), repo2])

        self.assertNotEqual(self.revisions, get_revisions(repo2))

        # Clone the original repo
        m.clone(self.repodir, self.wc, update_dest=False)

        # Try and pull in changes from the new repo
        self.assertNotEqual(0, m.pull(repo2, self.wc, update_dest=False))

