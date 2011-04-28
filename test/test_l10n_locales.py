import os
import shutil
import subprocess
import sys
import unittest

import mozharness.base.log as log
import mozharness.base.script as script
import mozharness.l10n.locales as locales

def cleanup():
    pass

class LocalesTest(locales.LocalesMixin, log.LogMixin, script.OSMixin,
                  script.ShellMixin):
    def __init__(self):
        super(LocalesTest, self).__init__()
        self.config = {}

class TestLocalesMixin(unittest.TestCase):
    def setUp(self):
        cleanup()

    def tearDown(self):
        cleanup()

    def test_query_locales_config(self):
        l = LocalesTest()
        l.config['locales'] = ['a', 'b', 'c']
        self.assertEqual(l.config['locales'], l.query_locales())
