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
    def test_absolute_path(self):
        m = get_mercurial_vcs_obj()
        self.assertEquals(m._make_absolute("/foo/bar"), "/foo/bar")

    def test_relative_path(self):
        m = get_mercurial_vcs_obj()
        self.assertEquals(m._make_absolute("foo/bar"), os.path.abspath("foo/bar"))

    def test_HTTP_paths(self):
        m = get_mercurial_vcs_obj()
        self.assertEquals(m._make_absolute("http://foo/bar"), "http://foo/bar")

    def test_absolute_file_path(self):
        m = get_mercurial_vcs_obj()
        self.assertEquals(m._make_absolute("file:///foo/bar"), "file:///foo/bar")

    def test_relative_file_path(self):
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

    def test_get_branch(self):
        m = get_mercurial_vcs_obj()
        m.clone(self.repodir, self.wc)
        b = m.get_branch_from_path(self.wc)
        self.assertEquals(b, 'default')

    def test_get_branches(self):
        m = get_mercurial_vcs_obj()
        m.clone(self.repodir, self.wc)
        branches = m.get_branches_from_path(self.wc)
        self.assertEquals(sorted(branches), sorted(["branch2", "default"]))

    def test_clone(self):
        m = get_mercurial_vcs_obj()
        rev = m.clone(self.repodir, self.wc, update_dest=False)
        self.assertEquals(rev, None)
        self.assertEquals(self.revisions, get_revisions(self.wc))
        self.assertEquals(sorted(os.listdir(self.wc)), ['.hg'])

    def test_clone_into_non_empty_dir(self):
        m = get_mercurial_vcs_obj()
        m.mkdir_p(self.wc)
        open(os.path.join(self.wc, 'test.txt'), 'w').write('hello')
        m.clone(self.repodir, self.wc, update_dest=False)
        self.failUnless(not os.path.exists(os.path.join(self.wc, 'test.txt')))

    def test_clone_update(self):
        m = get_mercurial_vcs_obj()
        rev = m.clone(self.repodir, self.wc, update_dest=True)
        self.assertEquals(rev, self.revisions[0])

    def test_clone_branch(self):
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

    def test_clone_update_branch(self):
        m = get_mercurial_vcs_obj()
        rev = m.clone(self.repodir, os.path.join(self.tmpdir, 'wc'),
                      branch="branch2", update_dest=True)
        self.assertEquals(rev, self.revisions[1], self.revisions)

    def test_clone_revision(self):
        m = get_mercurial_vcs_obj()
        m.clone(self.repodir, self.wc,
                revision=self.revisions[0], update_dest=False)
        # We'll only get a subset of the revisions
        self.assertEquals(self.revisions[:1] + self.revisions[2:],
                          get_revisions(self.wc))

    def test_update_revision(self):
        m = get_mercurial_vcs_obj()
        rev = m.clone(self.repodir, self.wc, update_dest=False)
        self.assertEquals(rev, None)

        rev = m.update(self.wc, revision=self.revisions[1])
        self.assertEquals(rev, self.revisions[1])

    def test_pull(self):
        m = get_mercurial_vcs_obj()
        # Clone just the first rev
        m.clone(self.repodir, self.wc, revision=self.revisions[-1], update_dest=False)
        self.assertEquals(get_revisions(self.wc), self.revisions[-1:])

        # Now pull in new changes
        rev = m.pull(self.repodir, self.wc, update_dest=False)
        self.assertEquals(rev, None)
        self.assertEquals(get_revisions(self.wc), self.revisions)

    def test_pull_revision(self):
        m = get_mercurial_vcs_obj()
        # Clone just the first rev
        m.clone(self.repodir, self.wc, revision=self.revisions[-1], update_dest=False)
        self.assertEquals(get_revisions(self.wc), self.revisions[-1:])

        # Now pull in just the last revision
        rev = m.pull(self.repodir, self.wc, revision=self.revisions[0], update_dest=False)
        self.assertEquals(rev, None)

        # We'll be missing the middle revision (on another branch)
        self.assertEquals(get_revisions(self.wc), self.revisions[:1] + self.revisions[2:])

    def test_pull_branch(self):
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

    def test_pull_unrelated(self):
        m = get_mercurial_vcs_obj()
        # Create a new repo
        repo2 = os.path.join(self.tmpdir, 'repo2')
        m.run_command(['%s/helper_files/init_hgrepo.sh' % os.path.dirname(__file__), repo2])

        self.assertNotEqual(self.revisions, get_revisions(repo2))

        # Clone the original repo
        m.clone(self.repodir, self.wc, update_dest=False)

        # Try and pull in changes from the new repo
        self.assertNotEqual(0, m.pull(repo2, self.wc, update_dest=False))

    def test_share_unrelated(self):
        m = get_mercurial_vcs_obj()
        # Create a new repo
        repo2 = os.path.join(self.tmpdir, 'repo2')
        m.run_command(['%s/helper_files/init_hgrepo.sh' % os.path.dirname(__file__), repo2])

        self.assertNotEqual(self.revisions, get_revisions(repo2))

        share_base = os.path.join(self.tmpdir, 'share')

        # Clone the original repo
        m.vcs_config = {'repo': self.repodir, 'dest': self.wc, 'share_base': share_base}
        m._ensure_shared_repo_and_revision(share_base)

        # Clone the new repo
        m = get_mercurial_vcs_obj()
        m.vcs_config = {'repo': repo2, 'dest': self.wc, 'share_base': share_base}
        m._ensure_shared_repo_and_revision(share_base)

        self.assertEquals(get_revisions(self.wc), get_revisions(repo2))

# TODO
    def test_share_reset(self):
        m = get_mercurial_vcs_obj()
        share_base = os.path.join(self.tmpdir, 'share')
        m.vcs_config = {'repo': self.repodir, 'dest': self.wc, 'share_base': share_base}

        # Clone the original repo
        m.ensure_repo_and_revision()

        old_revs = self.revisions[:]

        # Reset the repo
        m.run_command(['%s/helper_files/init_hgrepo.sh' % os.path.dirname(__file__), self.repodir])

        self.assertNotEqual(old_revs, get_revisions(self.repodir))

        # Try and update our working copy
        m.ensure_repo_and_revision()

        self.assertEquals(get_revisions(self.repodir), get_revisions(self.wc))
        self.assertNotEqual(old_revs, get_revisions(self.wc))

#    def test_push(self):
#        m = get_mercurial_vcs_obj()
#        clone(self.repodir, self.wc, revision=self.revisions[-2])
#        push(src=self.repodir, remote=self.wc)
#        self.assertEquals(get_revisions(self.wc), self.revisions)
#
#    def test_push_with_branch(self):
#        m = get_mercurial_vcs_obj()
#        clone(self.repodir, self.wc, revision=self.revisions[-1])
#        push(src=self.repodir, remote=self.wc, branch='branch2')
#        push(src=self.repodir, remote=self.wc, branch='default')
#        self.assertEquals(get_revisions(self.wc), self.revisions)
#
#    def test_push_with_revision(self):
#        clone(self.repodir, self.wc, revision=self.revisions[-2])
#        push(src=self.repodir, remote=self.wc, revision=self.revisions[-1])
#        self.assertEquals(get_revisions(self.wc), self.revisions[-2:])
#
#    def test_mercurial(self):
#        rev = mercurial(self.repodir, self.wc)
#        self.assertEquals(rev, self.revisions[0])
#
#    def test_push_new_branches_not_allowed(self):
#        clone(self.repodir, self.wc, revision=self.revisions[0])
#        self.assertRaises(Exception, push, self.repodir, self.wc,
#                          push_new_branches=False)
#
#    def test_mercurial_with_new_share(self):
#        share_base = os.path.join(self.tmpdir, 'share')
#        sharerepo = os.path.join(share_base, self.repodir.lstrip("/"))
#        os.mkdir(share_base)
#        mercurial(self.repodir, self.wc, share_base=share_base)
#        self.assertEquals(get_revisions(self.repodir), get_revisions(self.wc))
#        self.assertEquals(get_revisions(self.repodir), get_revisions(sharerepo))
#
#    def test_mercurial_with_share_base_in_env(self):
#        share_base = os.path.join(self.tmpdir, 'share')
#        sharerepo = os.path.join(share_base, self.repodir.lstrip("/"))
#        os.mkdir(share_base)
#        try:
#            os.environ['HG_SHARE_BASE_DIR'] = share_base
#            mercurial(self.repodir, self.wc)
#            self.assertEquals(get_revisions(self.repodir), get_revisions(self.wc))
#            self.assertEquals(get_revisions(self.repodir), get_revisions(sharerepo))
#        finally:
#            del os.environ['HG_SHARE_BASE_DIR']
#
#    def test_mercurial_with_existing_share(self):
#        share_base = os.path.join(self.tmpdir, 'share')
#        sharerepo = os.path.join(share_base, self.repodir.lstrip("/"))
#        os.mkdir(share_base)
#        mercurial(self.repodir, sharerepo)
#        open(os.path.join(self.repodir, 'test.txt'), 'w').write('hello!')
#        run_cmd(['hg', 'add', 'test.txt'], cwd=self.repodir)
#        run_cmd(['hg', 'commit', '-m', 'adding changeset'], cwd=self.repodir)
#        mercurial(self.repodir, self.wc, share_base=share_base)
#        self.assertEquals(get_revisions(self.repodir), get_revisions(self.wc))
#        self.assertEquals(get_revisions(self.repodir), get_revisions(sharerepo))
#
#
#    def test_mercurial_relative_dir(self):
#        os.chdir(os.path.dirname(self.repodir))
#
#        repo = os.path.basename(self.repodir)
#        wc = os.path.basename(self.wc)
#
#        rev = mercurial(repo, wc, revision=self.revisions[-1])
#        self.assertEquals(rev, self.revisions[-1])
#        open(os.path.join(self.wc, 'test.txt'), 'w').write("hello!")
#
#        rev = mercurial(repo, wc)
#        self.assertEquals(rev, self.revisions[0])
#        # Make sure our local file didn't go away
#        self.failUnless(os.path.exists(os.path.join(self.wc, 'test.txt')))
#
#    def test_mercurial_update_tip(self):
#        rev = mercurial(self.repodir, self.wc, revision=self.revisions[-1])
#        self.assertEquals(rev, self.revisions[-1])
#        open(os.path.join(self.wc, 'test.txt'), 'w').write("hello!")
#
#        rev = mercurial(self.repodir, self.wc)
#        self.assertEquals(rev, self.revisions[0])
#        # Make sure our local file didn't go away
#        self.failUnless(os.path.exists(os.path.join(self.wc, 'test.txt')))
#
#    def test_mercurial_update_rev(self):
#        rev = mercurial(self.repodir, self.wc, revision=self.revisions[-1])
#        self.assertEquals(rev, self.revisions[-1])
#        open(os.path.join(self.wc, 'test.txt'), 'w').write("hello!")
#
#        rev = mercurial(self.repodir, self.wc, revision=self.revisions[0])
#        self.assertEquals(rev, self.revisions[0])
#        # Make sure our local file didn't go away
#        self.failUnless(os.path.exists(os.path.join(self.wc, 'test.txt')))
#
#    # TODO: this test doesn't seem to be compatible with mercurial()'s
#    # share() usage, and fails when HG_SHARE_BASE_DIR is set
#    def test_mercurial_change_repo(self):
#        # Create a new repo
#        old_env = os.environ.copy()
#        if 'HG_SHARE_BASE_DIR' in os.environ:
#            del os.environ['HG_SHARE_BASE_DIR']
#
#        try:
#            repo2 = os.path.join(self.tmpdir, 'repo2')
#            run_cmd(['%s/helper_files/init_hgrepo.sh' % os.path.dirname(__file__), repo2])
#
#            self.assertNotEqual(self.revisions, get_revisions(repo2))
#
#            # Clone the original repo
#            mercurial(self.repodir, self.wc)
#            self.assertEquals(get_revisions(self.wc), self.revisions)
#            open(os.path.join(self.wc, 'test.txt'), 'w').write("hello!")
#
#            # Clone the new one
#            mercurial(repo2, self.wc)
#            self.assertEquals(get_revisions(self.wc), get_revisions(repo2))
#            # Make sure our local file went away
#            self.failUnless(not os.path.exists(os.path.join(self.wc, 'test.txt')))
#        finally:
#            os.environ.clear()
#            os.environ.update(old_env)
#
#    def test_make_hg_url(self):
#        #construct an hg url specific to revision, branch and filename and try to pull it down
#        file_url = make_hg_url(
#                "hg.mozilla.org",
#                '//build/tools/',
#                revision='FIREFOX_3_6_12_RELEASE',
#                filename="/lib/python/util/hg.py"
#                )
#        expected_url = "http://hg.mozilla.org/build/tools/raw-file/FIREFOX_3_6_12_RELEASE/lib/python/util/hg.py"
#        self.assertEquals(file_url, expected_url)
#
#    def test_make_hg_url_no_filename(self):
#        file_url = make_hg_url(
#                "hg.mozilla.org",
#                "/build/tools",
#                revision="default"
#        )
#        expected_url = "http://hg.mozilla.org/build/tools/rev/default"
#        self.assertEquals(file_url, expected_url)
#
#    def test_make_hg_url_no_revision_no_filename(self):
#        repo_url = make_hg_url(
#                "hg.mozilla.org",
#                "/build/tools"
#        )
#        expected_url = "http://hg.mozilla.org/build/tools"
#        self.assertEquals(repo_url, expected_url)
#
#    def test_make_hg_url_different_protocol(self):
#        repo_url = make_hg_url(
#                "hg.mozilla.org",
#                "/build/tools",
#                protocol='ssh'
#        )
#        expected_url = "ssh://hg.mozilla.org/build/tools"
#        self.assertEquals(repo_url, expected_url)
#
#    def test_share_repo(self):
#        repo3 = os.path.join(self.tmpdir, 'repo3')
#        share(self.repodir, repo3)
#        # make sure shared history is identical
#        self.assertEquals(self.revisions, get_revisions(repo3))
#
#    def test_mercurial_share_outgoing(self):
#        # ensure that outgoing changesets in a shared clone affect the shared history
#        repo5 = os.path.join(self.tmpdir, 'repo5')
#        repo6 = os.path.join(self.tmpdir, 'repo6')
#        mercurial(self.repodir, repo5)
#        share(repo5, repo6)
#        open(os.path.join(repo6, 'test.txt'), 'w').write("hello!")
#        # modify the history of the new clone
#        run_cmd(['hg', 'add', 'test.txt'], cwd=repo6)
#        run_cmd(['hg', 'commit', '-m', 'adding changeset'], cwd=repo6)
#        self.assertNotEquals(self.revisions, get_revisions(repo6))
#        self.assertNotEquals(self.revisions, get_revisions(repo5))
#        self.assertEquals(get_revisions(repo5), get_revisions(repo6))
#
#    def test_apply_and_push(self):
#        clone(self.repodir, self.wc)
#        def c(repo, attempt):
#            run_cmd(['hg', 'tag', '-f', 'TEST'], cwd=repo)
#        apply_and_push(self.wc, self.repodir, c)
#        self.assertEquals(get_revisions(self.wc), get_revisions(self.repodir))
#
#    def test_apply_and_push_fail(self):
#        clone(self.repodir, self.wc)
#        def c(repo, attempt, remote):
#            run_cmd(['hg', 'tag', '-f', 'TEST'], cwd=repo)
#            run_cmd(['hg', 'tag', '-f', 'CONFLICTING_TAG'], cwd=remote)
#        self.assertRaises(HgUtilError, apply_and_push, self.wc, self.repodir,
#                          lambda r, a: c(r, a, self.repodir), max_attempts=2)
#
#    def test_apply_and_push_with_rebase(self):
#        clone(self.repodir, self.wc)
#        def c(repo, attempt, remote):
#            run_cmd(['hg', 'tag', '-f', 'TEST'], cwd=repo)
#            if attempt == 1:
#                run_cmd(['hg', 'rm', 'hello.txt'], cwd=remote)
#                run_cmd(['hg', 'commit', '-m', 'test'], cwd=remote)
#        apply_and_push(self.wc, self.repodir,
#                       lambda r, a: c(r, a, self.repodir), max_attempts=2)
#        self.assertEquals(get_revisions(self.wc), get_revisions(self.repodir))
#
#    def test_apply_and_push_rebase_fails(self):
#        clone(self.repodir, self.wc)
#        def c(repo, attempt, remote):
#            run_cmd(['hg', 'tag', '-f', 'TEST'], cwd=repo)
#            if attempt in (1,2):
#                run_cmd(['hg', 'tag', '-f', 'CONFLICTING_TAG'], cwd=remote)
#        apply_and_push(self.wc, self.repodir,
#                       lambda r, a: c(r, a, self.repodir), max_attempts=3)
#        self.assertEquals(get_revisions(self.wc), get_revisions(self.repodir))
#
#    def test_apply_and_push_on_branch(self):
#        clone(self.repodir, self.wc)
#        def c(repo, attempt):
#            run_cmd(['hg', 'branch', 'branch3'], cwd=repo)
#            run_cmd(['hg', 'tag', '-f', 'TEST'], cwd=repo)
#        apply_and_push(self.wc, self.repodir, c)
#        self.assertEquals(get_revisions(self.wc), get_revisions(self.repodir))
#
#    def test_apply_and_push_with_no_change(self):
#        clone(self.repodir, self.wc)
#        def c(r,a):
#            pass
#        self.assertRaises(HgUtilError, apply_and_push, self.wc, self.repodir, c)
