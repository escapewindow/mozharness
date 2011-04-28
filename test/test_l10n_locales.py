import os
import shutil
import subprocess
import sys
import unittest

import mozharness.base.log as log
import mozharness.base.script as script
import mozharness.l10n.locales as locales

ALL_LOCALES = ['ar', 'be', 'de', 'es-ES']

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

    def test_query_locales_locales(self):
        l = LocalesTest()
        l.locales = ['a', 'b', 'c']
        self.assertEqual(l.locales, l.query_locales())

    def test_query_locales_config(self):
        l = LocalesTest()
        l.config['locales'] = ['a', 'b', 'c']
        self.assertEqual(l.config['locales'], l.query_locales())

    def test_query_locales_json(self):
        l = LocalesTest()
        l.config['locales_file'] = "test/helper_files/locales.json"
        l.config['base_work_dir'] = '.'
        l.config['work_dir'] = '.'
        locales = l.query_locales()
        locales.sort()
        self.assertEqual(ALL_LOCALES, locales)
