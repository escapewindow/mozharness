#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****
"""mozpooltest.py

"""

import os
import pprint
import sys

sys.path.insert(1, os.path.dirname(sys.path[0]))

from mozharness.base.python import VirtualenvMixin, virtualenv_config_options
from mozharness.base.script import BaseScript
from mozharness.mozilla.testing.mozpool import MozpoolMixin

# MozpoolTest {{{1
class MozpoolTest(VirtualenvMixin, MozpoolMixin, BaseScript):
    def __init__(self, require_config_file=False):
        BaseScript.__init__(
            self, config_options=virtualenv_config_options,
            all_actions=[
                'create-virtualenv',
                'run-tests',
            ],
            default_actions=[
                'run-tests',
            ],
            config={
                'virtualenv_modules': ['requests'],
                'mozpool_api_url': "http://localhost:8080",
            },
            require_config_file=require_config_file)

    def run_tests(self):
        mph = self.query_mozpool_handler()
        pprint.pprint(mph.query_full_device_list())

# __main__ {{{1
if __name__ == '__main__':
    mozpool_test = MozpoolTest()
    mozpool_test.run()
