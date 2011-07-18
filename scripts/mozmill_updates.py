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
"""mozmill_updates.py

Download and update Firefox against a specific channel.
"""

import os
import pprint
import sys
try:
    import simplejson as json
except ImportError:
    import json

sys.path.insert(1, os.path.dirname(sys.path[0]))

from mozharness.base.errors import PythonErrorList
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
     ["--channel"],
     {"action": "extend",
      "dest": "channels",
      "help": "Specify the channel"
     }
    ],[
     ["--venv", "--virtualenv"],
     {"action": "store",
      "dest": "virtualenv",
      "help": "Specify the virtualenv path"
     }
    ],[
     ["--mercurial-url", "--mercurial-url"],
     {"action": "store",
      "dest": "mercurial_url",
      "default": "http://mercurial.selenic.com/release/mercurial-1.7.3.tar.gz",
      "help": "Specify the mercurial pip url"
     }
    ],[
     ["--mozmill-url", "--mozmill-url"],
     {"action": "store",
      "dest": "mozmill_url",
      "default": "http://pypi.python.org/packages/source/m/mozmill/mozmill-1.5.4b6.tar.gz#md5=ac0b0710f90012991e8cc54cf01d1010",
      "help": "Specify the mozmill pip url"
     }
    ]]

    def __init__(self, require_config_file=False):
        self.python = None
        super(MozmillUpdate, self).__init__(
         config_options=self.config_options,
         all_actions=['preclean',
                      'pull',
                      'create-virtualenv',
                      'download',
                      'run-mozmill',
# TODO
#                      'upload',
#                      'notify',
                      ],
         default_actions=['preclean',
                          'pull',
                          'download',
                          'run-mozmill',
                          ],
         require_config_file=require_config_file,
        )

    def _pre_config_lock(self, rw_config):
        if not self.config.get("channels") and 'run-mozmill' in self.actions:
            self.fatal("Must specify --channel !")

    def query_python(self):
        if not self.python:
            if self.config.get('virtualenv'):
                self.python = "%s/bin/python" % self.config['virtualenv']
            else:
                self.python = "python"
        return self.python

    def query_versions(self):
        return {
                '5.0b6': 'firefox-5.0b6.en-US.mac.dmg',
                '5.0b7': 'firefox-5.0b7.en-US.mac.dmg',
                }

    def _clobber(self):
        dirs = self.query_abs_dirs()
        self.rmtree(dirs['abs_work_dir'])

    def preclean(self):
        self._clobber()

    def pull(self):
        c = self.config
        self.vcs_checkout_repos([{
         "repo": c['mozmill_automation_repo'],
         "tag": c['mozmill_automation_tag'],
         "dest": "mozmill-automation"
        }])

    def create_virtualenv(self):
        c = self.config
        if not c.get('virtualenv'):
            self.add_summary("No virtualenv specified; not creating virtualenv!", level="warning")
            return -1
        self.run_command("virtualenv --no-site-packages %s" % c['virtualenv'],
                         error_list=PythonErrorList)
        self.run_command("%s/bin/pip install %s" % (c['virtualenv'],
                                                    c['mercurial_url']),
                         error_list=PythonErrorList)
        self.run_command("%s/bin/pip install %s" % (c['virtualenv'],
                                                    c['mozmill_url']),
                         error_list=PythonErrorList)

    def download(self):
        dirs = self.query_abs_dirs()
        python = self.query_python()
        version_dict = self.query_versions()
        for version in version_dict.keys():
            # TODO platform hash; version map in configs
            # TODO ability to download file(s) that are sendchanged or
            # specified; download.py scrapes
            self.run_command("%s download.py -p mac -v %s" % (python, version),
                         cwd="%s/mozmill-automation" % dirs['abs_work_dir'])

    def run_mozmill(self):
        dirs = self.query_abs_dirs()
        python = self.query_python()
        version_dict = self.query_versions()
        # TODO preflight_run_mozmill that checks to make sure we have the binaries.
        # TODO channel/version map in configs; map that to binaries
        for channel in self.config['channels']:
            for version in version_dict.keys():
                self.info("Testing %s on %s channel" % (version, channel))
                status = self.run_command(
                 [python, 'testrun_update.py',
                  '--channel=%s' % channel,
                  '--report=file://%s/report_%s_%s.json' % (dirs['abs_upload_dir'], version, channel),
                  version_dict[version],
                 ],
                 cwd="%s/mozmill-automation" % dirs['abs_work_dir']
                )
                self.add_summary("%s on %s : exited %d" % (version, channel, status))
        # TODO get status (from output? from report.json?) and add to summary

# __main__ {{{1
if __name__ == '__main__':
    mozmill_update = MozmillUpdate()
    mozmill_update.run()
