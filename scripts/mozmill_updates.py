#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****
"""mozmill_updates.py

Download and update Firefox against a specific channel.
"""

import os
import re
import sys
try:
    import simplejson as json
except ImportError:
    import json

sys.path.insert(1, os.path.dirname(sys.path[0]))

from mozharness.base.errors import PythonErrorList
from mozharness.base.python import virtualenv_config_options, VirtualenvMixin
from mozharness.base.vcs.vcsbase import MercurialScript

# MozmillUpdate {{{1
class MozmillUpdate(VirtualenvMixin, MercurialScript):
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
    ]] + virtualenv_config_options

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
                      'summary',
                      ],
         default_actions=['preclean',
                          'pull',
                          'download',
                          'run-mozmill',
                          'summary',
                          ],
         require_config_file=require_config_file,
         config={"virtualenv_modules": ["mercurial", "mozmill"]},
        )

    def _pre_config_lock(self, rw_config):
        if not self.config.get("channels") and 'run-mozmill' in self.actions:
            self.fatal("Must specify --channel !")

    def query_versions(self):
        # TODO this needs to go in options + configs.
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

    def download(self):
        dirs = self.query_abs_dirs()
        python = self.query_python_path()
        version_dict = self.query_versions()
        for version in version_dict.keys():
            # TODO platform hash; version map in configs
            # TODO ability to download file(s) that are sendchanged or
            # specified; download.py scrapes
            self.run_command(
             "%s download.py -p mac -v %s" % (python, version),
             cwd="%s/mozmill-automation" % dirs['abs_work_dir'],
             error_list=PythonErrorList,
            )

    def run_mozmill(self):
        dirs = self.query_abs_dirs()
        python = self.query_python_path()
        version_dict = self.query_versions()
        MozmillErrorList = PythonErrorList[:]
        MozmillErrorList.extend([
         {'substr': r'''ERROR''', 'level': 'error'},
         {'substr': r'''UNEXPECTED''', 'level': 'error'},
         {'substr': r'''failed''', 'level': 'error'},
         {'regex': re.compile(r'''Failed[:]? [^0]'''), 'level': 'error'},
         {'substr': r'''Sorry, cannot connect''', 'level': 'error'},
         {'substr': r'''DeprecationWarning''', 'level': 'warning'},
        ])
        # TODO preflight_run_mozmill that checks to make sure we have the binaries.
        # TODO channel/version map in configs; map that to binaries
        for channel in self.config['channels']:
            for version in version_dict.keys():
                self.info("Testing %s on %s channel" % (version, channel))
                report_json = os.path.join(dirs['abs_work_dir'], "report_%s_%s.json" % (version, channel))
                self.run_command(
                 [python, 'testrun_update.py',
                  '--channel=%s' % channel,
                  '--report=file://%s' % report_json,
                  version_dict[version],
                 ],
                 cwd="%s/mozmill-automation" % dirs['abs_work_dir'],
                 error_list=MozmillErrorList,
                )
                if os.path.exists(report_json):
                    raw_json = self.read_from_file(report_json, verbose=False)
                    try:
                        contents = json.loads(raw_json)
                        passed = contents['tests_passed']
                        failed = contents['tests_failed']
                        skipped = contents['tests_skipped']
                        level = "info"
                        if failed:
                            level = "error"
                            self.return_code += failed
                        self.add_summary("%s on %s channel: %d passed, %d failed, %d skipped" % (version, channel, passed, failed, skipped),
                                         level=level)
                    except ValueError:
                        self.add_summary("%s is invalid json!", level="error")
                    finally:
                        self.copy_to_upload_dir(report_json)
                else:
                    self.add_summary("%s on %s channel didn't create report json!" % (version, channel), level="error")
                    self.return_code += 1

# __main__ {{{1
if __name__ == '__main__':
    mozmill_update = MozmillUpdate()
    mozmill_update.run_and_exit()
