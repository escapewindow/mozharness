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
'''Interact with SUT Agent and devicemanager.
'''

import os
import sys
import time

from mozharness.base.errors import PythonErrorList

# SUT {{{1
sut_config_options = [[
 ["--sut-ip"],
 {"action": "store",
  "dest": "sut_ip",
  # TODO remove the default
  # TODO adb non-ip support?
  "default": "10.0.1.4",
  "help": "Specify the IP address of the device running SUT."
 }
],[
 ["--devicemanager-path"],
 {"action": "store",
  "dest": "devicemanager_path",
  "help": "Specify the path to devicemanager.py."
 }
]]

class SUTMixin(object):
    '''BaseScript mixin, designed to interface with SUT Agent through
    devicemanager.

    Config items:
     * devicemanager_path points to the devicemanager.py location on disk.
     * sut_ip holds the IP of the device.
    '''
    devicemanager_path = None
    devicemanager = None

    def query_devicemanager_path(self):
        """Return the path to devicemanager.py.
        """
        if self.devicemanager_path:
            return self.devicemanager_path
        if self.config.get('devicemanager_path'):
            self.devicemanager_path = self.config['devicemanager_path']
        else:
            dirs = self.query_abs_dirs()
            self.devicemanager_path = dirs['abs_talos_dir']
        return self.devicemanager_path

    def query_devicemanager(self, error_level='fatal'):
        if self.devicemanager:
            return self.devicemanager
        c = self.config
        dm_path = self.query_devicemanager_path()
        sys.path.append(dm_path)
        try:
            import devicemanager
        except ImportError, e:
            self.log("Can't import devicemanager! %s" % e, level=error_level)
            return None
        self.devicemanager = devicemanager.DeviceManager(c['sut_ip'])

    # sut_flags {{{2
    def _query_sut_flag(self, flag_file=None):
        """Return (file_path, contents) if flag_file exists; None otherwise.
        """
        dirs = self.query_abs_dirs()
        return_value = {}
        flag_file_path = os.path.join(dirs['abs_sut_flag_dir'], flag_file)
        self.info("Looking for %s ..." % flag_file_path)
        if flag_file not in ('error.flg', 'proxy.flg'):
            raise ValueError, "Unknown flag_file type %s!" % flag_file
        if os.path.exists(flag_file_path):
            fh = open(flag_file_path, 'r')
            contents = fh.read()
            fh.close()
            return (flag_file_path, contents)

    def query_sut_error_flag(self):
        flag = self._query_sut_flag('error.flg')
        if flag:
            self.error("Found error flag at %s: %s!" % (flag[0], flag[1]))
            return flag

    def query_sut_proxy_flag(self):
        flag = self._query_sut_flag('proxy.flg')
        if flag:
            self.info("Found proxy flag at %s: %s." % (flag[0], flag[1]))
            return flag

    def query_sut_flags(self):
        """Return "error" or "proxy" if those flags exists; None otherwise.
        """
        self.info("Checking sut flags...")
        flags = []
        if self.query_sut_error_flag():
            flags.append('error')
        if self.query_sut_proxy_flag():
            flags.append('proxy')
        if flags:
            return flags

    def _set_sut_flag(self, message, flag_file=None, level="info"):
        dirs = self.query_abs_dirs()
        flag_file_path = os.path.join(dirs['abs_sut_flag_dir'], flag_file)
        self.log("Setting %s ..." % flag_file_path, level=level)
        if flag_file not in ('error.flg', 'proxy.flg'):
            raise ValueError, "Unknown flag_file type %s!" % flag_file
        # TODO do we need a generic way to write to a local file?
        self.mkdir_p(dirs['abs_sut_flag_dir'])
        # TODO try/except?
        fh = open(flag_file_path, "a")
        fh.write("%s: %s" % (time.strftime("%Y/%m/%d %H:%M:%S", time.localtime()), message))
        fh.close()
        return flag_file_path

    def set_sut_error_flag(self, message):
        self._set_sut_flag(message, flag_file="error.flg", level="error")

    def set_sut_proxy_flag(self, message):
        self._set_sut_flag(message, flag_file="proxy.flg")

    def _clear_sut_flag(self, flag_file=None):
        dirs = self.query_abs_dirs()
        return_value = {}
        (flag_file_path, contents) = self._query_sut_flag(flag_file)
        if os.path.exists(flag_file_path):
            self.info("Clearing %s..." % flag_file)
            self.rmtree(flag_file_path)

    def clear_sut_error_flag(self):
        self._clear_sut_flag("error.flg")

    def clear_sut_proxy_flag(self):
        self._clear_sut_flag("proxy.flg")

    # devicemanager calls {{{2
    def check_device_root(self):
        pass

    def wait_for_device(self, interval=60, max_attempts=20):
        pass



# __main__ {{{1

if __name__ == '__main__':
    '''TODO: unit tests.
    '''
    pass
