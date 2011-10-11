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
"""device_talosrunner.py

Set up and run talos against a device running SUT Agent or ADBD.

WIP.
"""

import os
import re
import sys
import time

sys.path.insert(1, os.path.dirname(sys.path[0]))

from mozharness.base.errors import PythonErrorList, ADBErrorList
from mozharness.base.log import DEBUG, INFO, WARNING, ERROR, CRITICAL, FATAL, IGNORE
from mozharness.base.python import virtualenv_config_options, VirtualenvMixin
from mozharness.base.vcs.vcsbase import MercurialScript
from mozharness.test.device import device_config_options, DeviceMixin

# Stop buffering!
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)

KNOWN_SUITES = (
    'ts',
    'tdhtml',
    'tgfx',
    'tp4m',
    'tpan',
    'tsspider',
    'tsvg',
    'twinopen',
    'tzoom',
)

# DeviceTalosRunner {{{1
class DeviceTalosRunner(VirtualenvMixin, DeviceMixin, MercurialScript):
    config_options = [[
     ["--talos-zip"],
     {"action": "store",
      "dest": "talos_zip",
      "help": "Specify a talos zipfile."
     }
    ],[
     ["--talos-repo"],
     {"action": "store",
      "dest": "talos_repo",
      "default": "http://hg.mozilla.org/build/talos",
      "help": "Specify the talos repo. This is unused if --talos-zip is set."
     }
    ],[
     ["--talos-tag"],
     {"action": "store",
      "dest": "talos_tag",
      "default": "default",
      "help": "Specify the talos tag for the talos repo."
     }
    ],[
     ["--talos-suite",],
     {"action": "extend",
      "dest": "talos_suites",
      "type": "string",
      "help": "Specify the talos suite(s) to run."
     }
    ],[
     ["--tp-zip",],
     {"action": "store",
      "dest": "tp_zip",
      "type": "string",
      "help": "Specify the a page load test zip if setting up a local webserver."
     }
    ],[
     ["--enable-automation"],
     {"action": "store_true",
      "dest": "enable_automation",
      "default": "default",
      "help": "Integrate with clientproxy automation (non-developer setting)."
     }
    ],[
     ["--installer-url", "--url"],
     {"action": "store",
      "dest": "installer_url",
      # TODO: wildcard download?
      "help": "Specify the url to the installer."
     }
    ],[
     ["--yaml-url"],
     {"action": "store",
      "dest": "yaml_url",
      "default": "http://pypi.python.org/packages/source/P/PyYAML/PyYAML-3.10.tar.gz#md5=74c94a383886519e9e7b3dd1ee540247",
      "help": "Specify the yaml pip url for the virtualenv."
     }
    ]] + virtualenv_config_options + device_config_options

    def __init__(self, require_config_file=False):
        self.python = None
        self.download_file_name = None
        super(DeviceTalosRunner, self).__init__(
         config_options=self.config_options,
         all_actions=['preclean',
                      'pull',
                      'check-device',
                      'create-virtualenv',
                      'cleanup-device',
                      'download',
                      'unpack',
                      'install-app',
                      'configure',
# create profile
                      'run-talos',
# reboot device
#                      'upload',
#                      'notify',
                      ],
         default_actions=['preclean',
                          'pull',
                          'check-device',
                          'cleanup-device',
                          'download',
                          'unpack',
                          'install-app',
                          'configure',
                          'run-talos',
                         ],
         require_config_file=require_config_file,
         config={"virtualenv_modules": ["PyYAML"],
                 "device_protocol": "adb",
                 "browser_dir": "fennec",
                },
        )

    # Helper methods {{{2

    def _pre_config_lock(self, rw_config):
        c = self.config
        if 'talos_suites' not in c:
            self.fatal("Must specify --talos-suites!")
        for suite in c['talos_suites']:
            if suite not in KNOWN_SUITES:
                self.fatal("Unknown suite %s! Choose from %s" % (suite, KNOWN_SUITES))

    def query_abs_dirs(self):
        if self.abs_dirs:
            return self.abs_dirs
        abs_dirs = super(DeviceTalosRunner, self).query_abs_dirs()
        c = self.config
        dirs = {}
        dirs['abs_talos_dir'] = os.path.join(abs_dirs['abs_work_dir'],
                                             'talos')
        dirs['abs_browser_dir'] = os.path.join(abs_dirs['abs_work_dir'],
                                               c.get('browser_dir', 'browser'))
        dirs['abs_device_flag_dir'] = c.get('device_flag_dir', c['base_work_dir'])
        for key in dirs.keys():
            if key not in abs_dirs:
                abs_dirs[key] = dirs[key]
        self.abs_dirs = abs_dirs
        return self.abs_dirs

    def query_download_file_name(self):
        if self.download_file_name:
            return self.download_file_name
        c = self.config
        download_file_name = os.path.basename(c['installer_url'])
        m = re.match(r'([a-zA-Z0-9]*).*\.([^.]*)', download_file_name)
        if m.group(1) and m.group(2):
            download_file_name = '%s.%s' % (m.group(1), m.group(2))
        self.download_file_name = download_file_name
        return self.download_file_name

    def _clobber(self):
        dirs = self.query_abs_dirs()
        self.rmtree(dirs['abs_work_dir'])

    # Actions {{{2

    def preclean(self):
        self._clobber()

    def pull(self):
        c = self.config
        dirs = self.query_abs_dirs()
        if c.get('talos_zip'):
            self.mkdir_p(dirs['abs_work_dir'])
            status = self.download_file(
                c['talos_zip'],
                file_name=os.path.join(dirs['abs_work_dir'],
                                       "talos.zip")
            )
            self.rmtree(os.path.join(dirs['abs_work_dir'], "talos"))
            self.run_command("unzip talos.zip", cwd=dirs['abs_work_dir'],
                             halt_on_failure=True)
        self.vcs_checkout_repos(c['repos'], parent_dir=dirs['abs_work_dir'])

    # check_device defined in DeviceMixin
    # create_virtualenv defined in VirtualenvMixin
    # cleanup_device defined in DeviceMixin

    def download(self):
        # TODO: a user friendly way to do this without specifying a url?
        c = self.config
        dirs = self.query_abs_dirs()
        orig_dir = os.getcwd()
        self.mkdir_p(dirs["abs_work_dir"])
        self.chdir(dirs["abs_work_dir"])
        file_name = self.query_download_file_name()
        self.download_file(c['installer_url'], file_name=file_name,
                           error_level="fatal")
        self.chdir(orig_dir)

    def unpack(self):
        dirs = self.query_abs_dirs()
        file_name = self.query_download_file_name()
        self.mkdir_p(dirs['abs_browser_dir'])
        self.run_command("unzip -o %s" % os.path.join(dirs['abs_work_dir'],
                                                      file_name),
                         cwd=dirs['abs_browser_dir'])

    def install_app(self):
        c = self.config
        serial = self.query_device_serial()
        file_name = self.query_download_file_name()
        dirs = self.query_abs_dirs()
        file_path = os.path.join(dirs['abs_work_dir'], file_name)
        if c['enable_automation']:
            self.set_device_time()
            self.set_device_proxy_flag("installing %s" % file_path)
        if self._log_level_at_least(DEBUG):
            self.run_command(["adb", "-s", serial, "shell", "ps"],
                             error_list=ADBErrorList)
        # TODO dm.getInfo('memory')
        if self._log_level_at_least(DEBUG):
            self.run_command(["adb", "-s", "shell", "uptime"],
                             error_list=ADBErrorList)
        # TODO getResolution ?
        # for tegra250:
        # adb shell getprop persist.tegra.dpy3.mode.width
        # adb shell getprop persist.tegra.dpy3.mode.height
        #
        # for non-tegra250, this ugliness:
        # adb -s serial shell screencap /mnt/sdcard/tests/foo.png
        # adb -s serial shell ls -l /mnt/sdcard/tests/foo.png
        # -rw-rw-r-- root     sdcard_rw   207187 2011-10-04 18:12 foo.png
        # adb pull /mnt/sdcard/tests/foo.png
        # Can do via PIL:
        # import Image
        # Image.open("foo.png").size
        # (1280, 800)
        # I hate requiring another module just for this, if we can help it.
        #
        # adb -s serial shell am display-size 1024x768
        # reboot; adb wait-for-device; sleep
        # (later) adb -s serial shell am display-size 1680:1050
        cmd = None
        # TODO error checking
        if not c['enable_automation']:
            # -s to install on sdcard? Needs to be config driven
            self.run_command(["adb", "-s", serial, "install", '-r',
                              os.path.join(dirs['abs_work_dir'], file_name)],
                             error_list=ADBErrorList)
        else:
            output = self.get_output_from_command(["adb", "-s", serial,
                                                   "shell",
                                                   "ls -d /data/data/%s" % \
                                                   c['device_package_name']])
            if "No such file" not in output:
                self.run_command(["adb", "-s", serial, "uninstall",
                                  c['device_package_name']],
                                 error_list=ADBErrorList)
            self.run_command(["adb", "-s", serial, "install", '-r',
                              file_path],
                             error_list=ADBErrorList)
            file_name = os.path.join(dirs['abs_browser_dir'], 'application.ini')
            self.run_command(["adb", "-s", serial, "push", file_name,
                              '/data/data/%s/application.ini' % c['device_package_name']])
            self.clear_device_proxy_flag()

    def preflight_configure(self):
        if 'install-app' in self.actions:
            c = self.config
            time_to_sleep = c.get("post_install_sleep", 60)
            self.info("Sleeping %d to avoid post-install errors" %
                      time_to_sleep)
            time.sleep(time_to_sleep)

    def configure(self):
        c = self.config
        dirs = self.query_abs_dirs()
        python = self.query_python_path()
        additional_options = []
        if c.get('disable_chrome'):
            additional_options.append("--noChrome")
        # TODO set no_chrome based on active tests
        command = [python, 'remotePerfConfigurator.py',
                   '-v',
                   '-e', c['device_package_name'],
                   '-t', c['device_name'],
                   '-b', c['talos_branch'],
                   '--branchName', c['talos_branch'],
                   '--resultsServer', c['graph_server'],
                   '--resultsLink', c['results_link'],
                   '--activeTests', ','.join(c['talos_suites']),
#                   '--remoteDevice', "%s:%s" % (c['device_ip'], str(c.get('device_port', 5555))),
#                   '--remoteDevice', c['device_ip'],
                   '--remoteDevice', '',
# remotePort of -1 for ADB
                   '--remotePort', '-1',
                   '--sampleConfig', c['talos_config_file'],
                   '--output', 'local.yml',
                   '--browserWait', '60',
# TODO Only run this if we want a webserver
                   '--develop',
                   '--webServer', c['talos_web_server'],
                  ] + additional_options
        self.run_command(command, cwd=dirs['abs_talos_dir'],
                         error_list=PythonErrorList,
                         halt_on_failure=True)

    def preflight_run_talos(self):
        if 'install-app' not in self.actions:
            c = self.config
            serial = self.query_device_serial()
            procs = self.get_output_from_command(['adb', "-s", serial,
                                                  'shell', 'ps'],
                                                 log_level=DEBUG)
            if c['device_package_name'] in procs:
                self.info("Found %s running... attempting to kill." %
                          c['device_package_name'])
                # TODO this needs to kill the pid
                # TODO verify it's gone
                for line in procs.splitlines():
                    line_contents = re.split('\s+', line)
                    if line_contents[-1].startswith(c['device_package_name']):
                        self.run_command(['adb', "-s", serial, 'shell',
                                          'kill', line_contents[1]],
                                         error_list=ADBErrorList)

    def run_talos(self):
        dirs = self.query_abs_dirs()
        python = self.query_python_path()
        TalosErrorList = PythonErrorList[:]
        TalosErrorList += [
         {'regex': r'''run-as: Package '.*' is unknown''', 'level': DEBUG},
         {'substr': r'''FAIL: Graph server unreachable''', 'level': CRITICAL},
         {'substr': r'''erfConfigurator.py: Unknown error''', 'level': CRITICAL},
         {'regex': r'''No machine_name called '.*' can be found''', 'level': CRITICAL},
        ]
        self.run_command([python, 'run_tests.py', '--noisy', '--debug',
                          'local.yml'],
                          error_list=TalosErrorList,
                          cwd=dirs['abs_talos_dir'])

# __main__ {{{1
if __name__ == '__main__':
    device_talos_runner = DeviceTalosRunner()
    device_talos_runner.run()
