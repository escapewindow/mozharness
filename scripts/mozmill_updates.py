#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
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

from mozharness.base.vcs.vcsbase import MercurialScript

# MozmillUpdate {{{1
class MozmillUpdate(MercurialScript):
    config_options = [[
     ["--ma-repo", "--mozmill-automation-repo"],
     {"action": "store",
      "dest": "mozmill_automation_repo",
      "default": "http://hg.mozilla.org/qa/mozmill-automation",
      "help": "Specify the mozmill-automation repo"
     }
    ],[
     ["--ma-tag", "--mozmill-automation-tag"],
     {"action": "store",
      "dest": "mozmill_automation_tag",
      "default": "default",
      "help": "Specify the mozmill-automation tag"
     }
    ],[
     ["--venv", "--virtualenv"],
     {"action": "store",
      "dest": "virtualenv",
# TODO remove this default
      "default": "/Users/asasaki/wrk/virtualenv/mh",
      "help": "Specify the virtualenv"
     }
    ]]

    def __init__(self, require_config_file=False):
        self.python = None
        super(MozmillUpdate, self).__init__(
         config_options=self.config_options,
         all_actions=['pull',
                      'download',
                      'run-mozmill',
# TODO
#                      'upload',
#                      'notify',
# TODO clobber.
# Hm, I wonder, since this is a list, if I could clobber at the top and at
# the end, using the same action, or if I'm best served with
# preclean/postclean.
                      ],
         require_config_file=require_config_file,
        )

    def query_python(self):
        if not self.python:
            if self.config.get('virtualenv'):
                self.python = "%s/bin/python" % self.config['virtualenv']
            else:
                self.python = "python"
        return self.python

    def pull(self):
        c = self.config
        self.vcs_checkout_repos([{
         "repo": c['mozmill_automation_repo'],
         "tag": c['mozmill_automation_tag'],
         "dest": "mozmill-automation"
        }])

    def download(self):
        dirs = self.query_abs_dirs()
        python = self.query_python()
        # TODO platform hash; version map in configs
        self.run_command("%s download.py -p mac -v 5.0b7" % python,
                         cwd="%s/mozmill-automation" % dirs['abs_work_dir'])

    def run_mozmill(self):
        dirs = self.query_abs_dirs()
        python = self.query_python()
        # TODO preflight_run_mozmill that checks to make sure we have the binaries.
        # TODO channel/version map in configs; map that to binaries
        self.run_command("%s testrun_update.py --channel=beta --report=file://%s/report.json firefox-5.0b7.en-US.mac.dmg" % (python, dirs['abs_upload_dir']),
                         cwd="%s/mozmill-automation" % dirs['abs_work_dir'])
        # TODO get status (from output? from report.json?) and add to summary

# __main__ {{{1
if __name__ == '__main__':
    mozmill_update = MozmillUpdate()
    mozmill_update.run()
