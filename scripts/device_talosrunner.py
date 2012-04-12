#!/usr/bin/env python -u
# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
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

from mozharness.base.errors import PythonErrorList
from mozharness.base.log import DEBUG, ERROR, CRITICAL
from mozharness.base.vcs.vcsbase import VCSMixin
from mozharness.mozilla.talos import Talos
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
class DeviceTalosRunner(VCSMixin, DeviceMixin, Talos):
    config_options = Talos.config_options + device_config_options

    def __init__(self, require_config_file=False):
        super(DeviceTalosRunner, self).__init__(
         config_options=self.config_options,
         all_actions=['preclean',
                      'pull',
                      'check-device',
                      'create-virtualenv',
                      'pre-cleanup-device',
                      'download',
                      'unpack',
                      'install-app',
                      'configure',
                      'run-tests',
                      'post-cleanup-device',
#                      'upload',
#                      'notify',
#                      'postclean',
#                      'reboot-host',
                      ],
         default_actions=['preclean',
#                          'pull',
#                          'check-device',
#                          'pre-cleanup-device',
#                          'download',
#                          'unpack',
#                          'install-app',
#                          'configure',
#                          'run-tests',
#                          'post-cleanup-device',
                         ],
         require_config_file=require_config_file,
         config={"virtualenv_modules": ["talos"],
                 "browser_dir": "fennec",
                },
        )

    # Helper methods {{{2

    def _pre_config_lock(self, rw_config):
        c = self.config
        if 'device_protocol' not in c:
            self.fatal("Must specify --device-protocol!")
        if 'tests' not in c:
            self.fatal("Must specify --talos-suites!")
        for suite in c['tests']:
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
        for key in dirs.keys():
            if key not in abs_dirs:
                abs_dirs[key] = dirs[key]
        self.abs_dirs = abs_dirs
        return self.abs_dirs

    # Actions {{{2

    def preclean(self):
        self.clobber()

    def pull(self):
        c = self.config
        dirs = self.query_abs_dirs()
        if c.get('talos_zip'):
            self.mkdir_p(dirs['abs_work_dir'])
            self.download_file(
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

    def pre_cleanup_device(self):
        self.cleanup_device()

    # TODO install_app defined in DeviceMixin

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
        if c['device_protocol'] == 'sut':
            additional_options.extend(['--remoteDevice', c['device_ip']])
            additional_options.extend(['--remotePort', c.get('device_port', '20701')])
        elif c['device_protocol'] == 'adb':
            additional_options.extend(['--remoteDevice', ''])
            additional_options.extend(['--remotePort', '-1'])
        if c.get('start_python_webserver'):
            additional_options.append('--develop')
        # TODO set no_chrome based on active tests
        command = [python, 'remotePerfConfigurator.py',
                   '-v',
                   '-e', c['device_package_name'],
                   '-t', c.get('talos_device_name', c['device_name']),
                   '-b', c['talos_branch'],
                   '--branchName', c['talos_branch'],
                   '--resultsServer', c['graph_server'],
                   '--resultsLink', c['results_link'],
                   '--activeTests', ':'.join(c['tests']),
                   '--sampleConfig', c['talos_config_file'],
                   '--output', 'local.yml',
                   '--browserWait', '60',
                   '--webServer', c['talos_webserver'],
                  ] + additional_options
        self.run_command(command, cwd=dirs['abs_talos_dir'],
                         error_list=PythonErrorList,
                         halt_on_failure=True)

#    def preflight_run_talos(self):
#        #TODO get this un-adb-hardcoded
#        if 'install-app' not in self.actions:
#            c = self.config
#            device_id = self.query_device_id()
#            adb = self.query_exe('adb')
#            kill = self.query_device_exe('kill')
#            procs = self.get_output_from_command([adb, "-s", device_id,
#                                                  'shell', 'ps'],
#                                                 log_level=DEBUG)
#            if c['device_package_name'] in procs:
#                self.info("Found %s running... attempting to kill." %
#                          c['device_package_name'])
#                # TODO this needs to kill the pid
#                # TODO verify it's gone
#                for line in procs.splitlines():
#                    line_contents = re.split('\s+', line)
#                    if line_contents[-1].startswith(c['device_package_name']):
#                        self.run_command([adb, "-s", device_id, 'shell',
#                                          kill, line_contents[1]],
#                                         error_list=ADBErrorList)

    def post_cleanup_device(self):
        c = self.config
        if c.get('enable_automation'):
            self.cleanup_device(reboot=True)
        else:
            self.info("Nothing to do without enable_automation set.")

    # run_tests() is in Talos

# __main__ {{{1
if __name__ == '__main__':
    device_talos_runner = DeviceTalosRunner()
    device_talos_runner.run()
