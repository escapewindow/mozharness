#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is Mozilla.
#
# The Initial Developer of the Original Code is
# the Mozilla Foundation <http://www.mozilla.org/>.
# Portions created by the Initial Developer are Copyright (C) 2011
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   Aki Sasaki <aki@mozilla.com>
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****
"""test.py

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

# MozmillUpdate {{{1
class MozmillUpdate(BaseScript):
#    config_options = [[
#     ["--test-file",],
#     {"action": "extend",
#      "dest": "test_files",
#      "help": "Specify which config files to test"
#     }
#    ]]

    def __init__(self, require_config_file=False):
        self.config_files = []
        BaseScript.__init__(self, #config_options=self.config_options,
                            all_actions=['run-mozmill',
                                         ],
                            default_actions=['run-mozmill',
                                             ],
                            require_config_file=require_config_file)

    def run_mozmill(self):
        self.run_command("python testrun_update.py --channel=beta --report=file://report.json firefox-5.0b7.en-US.mac.dmg",
                         cwd="/Users/asasaki/src/talosrunner/mozmill-automation")

# __main__ {{{1
if __name__ == '__main__':
    mozmill_update = MozmillUpdate()
    mozmill_update.run()
