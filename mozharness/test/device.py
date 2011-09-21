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
#   Mike Taylor <bear@mozilla.com>
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
'''Interact with ADB, SUT Agent, and devicemanager.

This code is largely from
http://hg.mozilla.org/build/tools/file/default/sut_tools
'''

import datetime
import os
import re
import sys
import time

from mozharness.base.errors import PythonErrorList, BaseErrorList
from mozharness.base.log import LogMixin
from mozharness.base.script import ShellMixin, OSMixin

class DeviceException(Exception):
    pass

# DeviceMixin {{{1
device_config_options = [[
 ["--device-ip"],
 {"action": "store",
  "dest": "device_ip",
  "help": "Specify the IP address of the device."
 }
],[
 ["--device-port"],
 {"action": "store",
  "dest": "device_port",
  # TODO how do I default this to 20701 if device_protocol == 'sut' ?
  # default to 5555 / 20701 if device_protocol is adb/sut and device_port
  # is None?
  "help": "Specify the IP address of the device."
 }
],[
 ["--devicemanager-path"],
 {"action": "store",
  "dest": "devicemanager_path",
  "help": "Specify the path to devicemanager.py."
 }
],[
 ["--device-type"],
 # A bit useless atm, but we can add new device types as we add support
 # for them.
 {"action": "store",
  "type": "choice",
  "choices": ["non-tegra", "tegra250"],
  "default": "non-tegra",
  "dest": "device_type",
  "help": "Specify the device type."
 }
]]

class DeviceMixin(object):
    '''BaseScript mixin, designed to interface with the device through
    devicemanager.

    Config items:
     * devicemanager_path points to the devicemanager.py location on disk.
     * device_ip holds the IP of the device.
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

    def query_devicemanager(self, level='fatal'):
        if self.devicemanager:
            return self.devicemanager
        c = self.config
        dm_path = self.query_devicemanager_path()
        sys.path.append(dm_path)
        try:
            if c['device_protocol'] == 'adb':
                import devicemanagerADB as devicemanager
            else:
                self.fatal("Don't know how to use device_protocol %s!" %
                           c['device_protocol'])
        except ImportError, e:
            self.log("Can't import devicemanager! %s\nDid you check out talos?" % str(e), level=level)
            raise
        self.devicemanager = devicemanager.DeviceManager(c['device_ip'])
        self.devicemanager.debug = 3
        return self.devicemanager

    # device_flags {{{2
    def _query_device_flag(self, flag_file=None):
        """Return (file_path, contents) if flag_file exists; None otherwise.
        """
        dirs = self.query_abs_dirs()
        return_value = {}
        flag_file_path = os.path.join(dirs['abs_device_flag_dir'], flag_file)
        self.info("Looking for %s ..." % flag_file_path)
        if flag_file not in ('error.flg', 'proxy.flg'):
            raise ValueError, "Unknown flag_file type %s!" % flag_file
        if os.path.exists(flag_file_path):
            fh = open(flag_file_path, 'r')
            contents = fh.read()
            fh.close()
            return (flag_file_path, contents)

    def query_device_error_flag(self):
        flag = self._query_device_flag('error.flg')
        if flag:
            self.error("Found error flag at %s: %s!" % (flag[0], flag[1]))
            return flag

    def query_device_proxy_flag(self):
        flag = self._query_device_flag('proxy.flg')
        if flag:
            self.info("Found proxy flag at %s: %s." % (flag[0], flag[1]))
            return flag

    def query_device_flags(self):
        """Return "error" or "proxy" if those flags exists; None otherwise.
        """
        self.info("Checking device flags...")
        flags = []
        if self.query_device_error_flag():
            flags.append('error')
        if self.query_device_proxy_flag():
            flags.append('proxy')
        if flags:
            return flags

    def _set_device_flag(self, message, flag_file=None, level="info"):
        dirs = self.query_abs_dirs()
        flag_file_path = os.path.join(dirs['abs_device_flag_dir'], flag_file)
        self.log("Setting %s ..." % flag_file_path, level=level)
        if flag_file not in ('error.flg', 'proxy.flg'):
            raise ValueError, "Unknown flag_file type %s!" % flag_file
        # TODO do we need a generic way to write to a local file?
        self.mkdir_p(dirs['abs_device_flag_dir'])
        # TODO try/except?
        fh = open(flag_file_path, "a")
        fh.write("%s: %s" % (time.strftime("%Y/%m/%d %H:%M:%S", time.localtime()), message))
        fh.close()
        return flag_file_path

    def set_device_error_flag(self, message):
        self._set_device_flag(message, flag_file="error.flg", level="error")

    def set_device_proxy_flag(self, message):
        self._set_device_flag(message, flag_file="proxy.flg")

    def _clear_device_flag(self, flag_file=None):
        dirs = self.query_abs_dirs()
        return_value = {}
        (flag_file_path, contents) = self._query_device_flag(flag_file)
        if os.path.exists(flag_file_path):
            self.info("Clearing %s..." % flag_file)
            self.rmtree(flag_file_path)

    def clear_device_error_flag(self):
        self._clear_device_flag("error.flg")

    def clear_device_proxy_flag(self):
        self._clear_device_flag("proxy.flg")

    # devicemanager calls {{{2
    def query_device_root(self, silent=False):
        dm = self.query_devicemanager()
        device_root = dm.getDeviceRoot()
        if not silent:
            self.info("Device root is %s" % device_root)
        if not device_root or device_root == '/tests':
            self.error("Bad device root; most likely the device isn't up.")
            return None
        return device_root

    def wait_for_device(self, interval=60, max_attempts=20):
        self.info("Waiting for device to come back...")
        time.sleep(interval)
        tries = 0
        while tries <= max_attempts:
            tries += 1
            self.info("Try %d" % tries)
            if self.query_device_root(silent=True) is not None:
                return 0
            time.sleep(interval)
        raise DeviceException, "Remote Device Error: waiting for device timed out."

    def set_device_time(self, device_time=None, error_level='error'):
        dm = self.query_devicemanager()
        if device_time is None:
            device_time = datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S')
        try:
            dm.verifySendCMD(['settime %s' % device_time])
        except devicemanager.DMError, e:
            self.log("Can't set device time: %s" % e, level=error_level)
            return False
        return True

    def remove_device_dir(self, error_level='error'):
        dm = self.query_devicemanager()
        dev_root = dm.query_device_root()
        if dm.dirExists(dev_root):
            self.info("Removing device root %s." % dev_root)
            if dm.removeDir(dev_root) is None:
                self.log("Unable to remove device root!", level=error_level)
                return False
        return True

    def uninstall_app(self, package_name, package_root="/data/data",
                      error_level="error"):
        dm = self.query_devicemanager()
        if dm.dirExists('%s/%s' % (package_root, package_name)):
            status = dm.uninstallAppAndReboot(package_name)
            if status is None:
                self.log("Failed to uninstall %s!" % package_name,
                         level=error_level)

    # Maintenance {{{2

    def _ping_device(self):
        c = self.config
        if not c['device_ip']:
            self.info("device_ip not set; not attempting to ping.")
        else:
            self.info("Attempting to ping device %s." % c['device_ip'])
        # TODO cross-platform
        return self.run_command("ping -c 5 -o %s" % c['device_ip'])

    def check_for_device(self):
        self.info("Looking for device...")
        # TODO support non-adb
        output = self.get_output_from_command("adb devices",
                                              error_list=BaseErrorList)
        if basestring in output.__bases__:
            # TODO make this multi-device friendly?
            m = re.search("\n(\S+)\s+(\S+)\n\n", output)
            if m and len(m.groups()) == 2:
                self.info("Found %s %s." % (m.group(2), m.group(1)))
                return True
        self.error("Can't find a device.")
        return False



    # Device-type-specific. {{{2

    def remove_etc_hosts(self, hosts_file="/system/etc/hosts",
                         error_level='error'):
        c = self.config
        if c['device_type'] != 'tegra250':
            self.debug("No need to remove /etc/hosts on a non-Tegra250.")
            return
        dm = self.query_devicemanager()
        if dm.fileExists(hosts_file):
            self.info("Removing %s file." % hosts_file)
            try:
                dm.sendCMD(['exec mount -o remount,rw -t yaffs2 /dev/block/mtdblock3 /system'])
                dm.sendCMD(['exec rm %s' % hosts_file])
            except devicemanager.DMError, e:
                self.log("Unable to remove %s: %s!" % (hosts_file, str(e)),
                         level=error_level)
                raise
        else:
            self.debug("%s file doesn't exist; skipping." % hosts_file)



# ADBDevice {{{1
class ADBDevice(ShellMixin, OSMixin, LogMixin, DeviceMixin, object):
    def __init__(self, log_obj=None, config=None, devicemanager=None):
        super(ADBDevice, self).__init__()
        self.log_obj = log_obj
        self.config = config
        self.devicemanager = devicemanager



# __main__ {{{1

if __name__ == '__main__':
    '''TODO: unit tests.
    '''
    pass
