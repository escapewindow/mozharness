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
