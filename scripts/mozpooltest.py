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
try:
    import simplejson as json
except ImportError:
    import json

sys.path.insert(1, os.path.dirname(sys.path[0]))

from mozharness.base.script import BaseScript
from mozharness.mozilla.testing.mozpool import MozpoolMixin

# MozpoolTest {{{1
class MozpoolTest(MozpoolMixin, BaseScript):
    def __init__(self, require_config_file=False):
        BaseScript.__init__(self,
                            all_actions=['run-tests',
                                         ],
                            require_config_file=require_config_file)
        self.mozpool_api_url = "http://localhost:8080"

    def run_tests(self):
        pprint.pprint(self.query_full_device_list())

# __main__ {{{1
if __name__ == '__main__':
    mozpool_test = MozpoolTest()
    mozpool_test.run()
