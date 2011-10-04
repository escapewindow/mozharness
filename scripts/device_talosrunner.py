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

sys.path.insert(1, os.path.dirname(sys.path[0]))

from mozharness.base.errors import PythonErrorList, ADBErrorList
from mozharness.base.python import virtualenv_config_options, VirtualenvMixin
from mozharness.base.vcs.vcsbase import MercurialScript
from mozharness.test.device import device_config_options, DeviceMixin

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
        self.browser_revision = None
        super(DeviceTalosRunner, self).__init__(
         config_options=self.config_options,
         all_actions=['preclean',
                      'pull',
                      'check-device',
                      'create-virtualenv',
                      'cleanup-device',
                      'download',
                      'unpack',
                      'print-browser-revision',
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
                          'print-browser-revision',
                          'install-app',
                          'configure',
                         ],
         require_config_file=require_config_file,
         config={"virtualenv_modules": ["PyYAML"],
                 "device_protocol": "adb",
                 "browser_dir": "fennec",
                },
        )

    # Helper methods {{{2

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

    def query_browser_revision(self):
        if self.browser_revision:
            return self.browser_revision
        dirs = self.query_abs_dirs()
        file_name = os.path.join(dirs['abs_browser_dir'], 'application.ini')
        if os.path.exists(file_name):
            browser_revision = {}
            # TODO generic way to read a file?
            # TODO this probably needs to be more robust.
            fh = open(file_name, 'r')
            contents = fh.read()
            fh.close()
            m = re.search(r"""BuildID=(?P<buildid>\d+)""", contents)
            browser_revision['buildid'] = m.group("buildid")
            m = re.search(r"""SourceStamp=(?P<revision>\S+)""", contents)
            browser_revision['revision'] = m.group("revision")
            m = re.search(r"""SourceRepository=(?P<repo_path>\S+)""", contents)
            browser_revision['repo_path'] = m.group("repo_path")
            self.browser_revision = browser_revision
            return self.browser_revision
        self.warning("Can't find browser revision: %s doesn't exist!" % \
                     file_name)

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

    def print_browser_revision(self):
        browser_revision = self.query_browser_revision()
        if not browser_revision:
            self.warning("Can't print browser revision!")
            return -1
        if self.config.get("enable_automation"):
            self.info("""TinderboxPrint: <a href="%(repo_path)s/rev/%(revision)s" title="Built from Mozilla revision %(revision)s">moz:%(revision)s</a> <br />""" % browser_revision)
        else:
            self.info("Built from %(repo_path)s/rev/%(revision)s." % browser_revision)

    def install_app(self):
        dm = self.query_devicemanager()
        file_name = self.query_download_file_name()
        dirs = self.query_abs_dirs()
        file_path = os.path.join(dirs['abs_work_dir'], file_name)
        c = self.config
        if c['enable_automation']:
            self.set_device_time()
            self.set_device_proxy_flag("installing %s" % file_path)
        self.run_command('adb shell ps', error_list=ADBErrorList)
        # TODO dm.getInfo('memory')
        self.run_command('adb shell uptime', error_list=ADBErrorList)
        # TODO getResolution
        # dm.adjustResolution(1024, 768, 'crt')
        # reboot; waitfordevice
        cmd = None
        # TODO error checking
        if not c['enable_automation']:
            # -s to install on sdcard? Needs to be config driven
            self.run_command(["adb", "install", '-r', os.path.join(dirs['abs_work_dir'], file_name)], error_list=ADBErrorList)
        else:
            output = self.get_output_from_command("adb shell ls -d /data/data/%s" % c['device_package_name'])
            if "No such file" not in output:
                self.run_command(["adb", "uninstall", c['device_package_name']],
                                 error_list=ADBErrorList)
            self.run_command(["adb", "install", '-r', file_path],
                             error_list=ADBErrorList)
            file_name = os.path.join(dirs['abs_browser_dir'], 'application.ini')
            self.run_command(["adb", "push", file_name,
                              '/data/data/%s/application.ini' % c['device_package_name']])

    def configure(self):
        c = self.config
        dirs = self.query_abs_dirs()
        python = self.query_python_path()
        no_chrome = "--noChrome"
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
                   no_chrome,
# TODO how do i just use the adb device?
#                   '--remoteDevice', "%s:%s" % (c['device_ip'], str(c.get('device_port', 5555))),
#                   '--remoteDevice', c['device_ip'],
                   '--remoteDevice', '',
# remotePort of -1 for ADB
                   '--remotePort', '-1',
                   '--sampleConfig', c['talos_config_file'],
                   '--output', 'local.yml',
                   '--webServer', c['talos_web_server'],
                   '--browserWait', '60',
                  ]
        self.run_command(command, cwd=dirs['abs_talos_dir'],
                         error_list=PythonErrorList,
                         halt_on_failure=True)

    def run_talos(self):
        dirs = self.query_abs_dirs()
        python = self.query_python_path()
        TalosList = PythonErrorList[:]

# __main__ {{{1
if __name__ == '__main__':
    device_talos_runner = DeviceTalosRunner()
    device_talos_runner.run()
