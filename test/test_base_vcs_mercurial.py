import os
import shutil
import subprocess
import sys
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

class TestMercurialScript(unittest.TestCase):
    def setUp(self):
        cleanup()

    def tearDown(self):
        cleanup()

    def test_mercurial_script(self):
        s = mercurial.MercurialScript(initial_config_file='test/test.json')
        s.mkdir_p('test_dir')
        s.run_command("touch test_dir/tools")
        s.scm_checkout("http://hg.mozilla.org/build/tools",
                      parent_dir="test_dir", clobber=True)
        self.assertTrue(os.path.isdir("test_dir/tools"))
        s.scm_checkout("http://hg.mozilla.org/build/tools",
                      dir_name="test_dir/tools", halt_on_failure=False)

def get_mercurial_vcs_obj():
    m = mercurial.MercurialVCS()
    return m

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
