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
from mozharness.base.log import LogMixin, DEBUG, INFO, WARNING, ERROR, CRITICAL, FATAL, IGNORE
from mozharness.base.script import ShellMixin, OSMixin

class DeviceException(Exception):
    pass

PROXY_FLAG = 'proxy.flg'
ERROR_FLAG = 'error.flg'

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
    devicemanager = None

    def query_devicemanager(self, level='fatal'):
        if self.devicemanager:
            return self.devicemanager
        c = self.config
        dirs = self.query_abs_dirs()
        dm_path = c.get("devicemanager_path", dirs['abs_talos_dir'])
        sys.path.append(dm_path)
        try:
            if c['device_protocol'] == 'adb':
                import devicemanagerADB as devicemanager
                self.devicemanager = devicemanager.DeviceManagerADB()
            else:
                self.fatal("Don't know how to use device_protocol %s!" %
                           c['device_protocol'])
        except ImportError, e:
            self.log("Can't import devicemanager! %s\nDid you check out talos?" % str(e), level=level)
            raise
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
        if flag_file not in (ERROR_FLAG, PROXY_FLAG):
            raise ValueError, "Unknown flag_file type %s!" % flag_file
        if os.path.exists(flag_file_path):
            fh = open(flag_file_path, 'r')
            contents = fh.read()
            fh.close()
            return (flag_file_path, contents)

    def query_device_error_flag(self, log_level=ERROR):
        flag = self._query_device_flag(ERROR_FLAG)
        if flag:
            self.log("Found error flag at %s: %s!" % (flag[0], flag[1]),
                     level=log_level)
            return flag

    def query_device_proxy_flag(self, log_level=INFO):
        flag = self._query_device_flag(PROXY_FLAG)
        if flag:
            self.log("Found proxy flag at %s: %s." % (flag[0], flag[1]),
                     level=log_level)
            return flag

    def query_device_flags(self, clear_proxy_flag=True,
                           halt_on_error_flag=True):
        """Return a dict with 'error' or 'proxy' keys if those flags exist;
        None otherwise.
        """
        self.info("Checking device flags...")
        flags = {}
        flag = self.query_device_proxy_flag(log_level=WARNING)
        if flag:
            if clear_proxy_flag:
                self.clear_device_proxy_flag()
            else:
                flags['proxy'] = flag
        level = ERROR
        if halt_on_error_flag:
            level = FATAL
        flag = self.query_device_error_flag(log_level=level)
        if flag:
            flags['error'] = flag
        if flags:
            return flags

    def _set_device_flag(self, message, flag_file=None, level="info"):
        dirs = self.query_abs_dirs()
        flag_file_path = os.path.join(dirs['abs_device_flag_dir'], flag_file)
        self.log("Setting %s ..." % flag_file_path, level=level)
        if flag_file not in (ERROR_FLAG, PROXY_FLAG):
            raise ValueError, "Unknown flag_file type %s!" % flag_file
        # TODO do we need a generic way to write to a local file?
        self.mkdir_p(dirs['abs_device_flag_dir'])
        # TODO try/except?
        fh = open(flag_file_path, "a")
        fh.write("%s: %s" % (time.strftime("%Y/%m/%d %H:%M:%S", time.localtime()), message))
        fh.close()
        return flag_file_path

    def set_device_error_flag(self, message):
        self.critical("Setting error flag: %s" % ERROR_FLAG)
        self._set_device_flag(message, flag_file=ERROR_FLAG, level="error")

    def set_device_proxy_flag(self, message):
        self.info("Setting proxy flag: %s" % PROXY_FLAG)
        self._set_device_flag(message, flag_file=PROXY_FLAG)

    def _clear_device_flag(self, flag_file=None):
        dirs = self.query_abs_dirs()
        return_value = {}
        (flag_file_path, contents) = self._query_device_flag(flag_file)
        if os.path.exists(flag_file_path):
            self.info("Clearing %s..." % flag_file_path)
            self.rmtree(flag_file_path, error_level=FATAL)

    def clear_device_error_flag(self):
        self._clear_device_flag(ERROR_FLAG)

    def clear_device_proxy_flag(self):
        self._clear_device_flag(PROXY_FLAG)

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

    def remove_device_root(self, error_level='error'):
        dm = self.query_devicemanager()
        dev_root = self.query_device_root()
        if dev_root is None:
            self.exit_on_error("Can't connect to device!")
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

    def exit_on_error(self, message, **kwargs):
        if self.config['enable_automation']:
            self.set_device_error_flag(message)
            self.fatal("Remote Device Error: %s" % message, **kwargs)
        else:
            self.fatal(message, **kwargs)

    def ping_device(self):
        c = self.config
        # TODO support non-adb
        if c['device_protocol'] == 'adb':
            self.info("Looking for device...")
            output = self.get_output_from_command("adb devices")
            if output.__class__ == str:
                # TODO make this multi-device friendly?
                m = re.search(r'''\n(\S+)\s+(\S+)\n*$''', output)
                if m and len(m.groups()) >= 2:
                    self.info("Found %s %s." % (m.group(2), m.group(1)))
                    return True
            self.error("Can't find a device.")
            return False
        else:
            self.fatal("Device protocol %s is unsupported!" %
                       c['device_protocol'])

    def check_device(self):
        if not self.ping_device():
            self.exit_on_error("Can't find device!")
        if self.query_device_root() is None:
            self.exit_on_error("Can't connect to device!")
        if self.config.get('enable_automation'):
            self.query_device_flags()

    def cleanup_device(self):
        status = self.remove_device_root()
        if not status:
            self.exit_on_error("Can't remove device root!")
        self.remove_etc_hosts()
        # TODO pid kill
        # TODO uninstall apps



    # Device-type-specific. {{{2

    def remove_etc_hosts(self, hosts_file="/system/etc/hosts"):
        c = self.config
        if c['device_type'] not in ("tegra",):
            self.debug("No need to remove /etc/hosts on a non-Tegra250.")
            return
        dm = self.query_devicemanager()
        if dm.fileExists(hosts_file):
            self.info("Removing %s file." % hosts_file)
            try:
                dm.sendCMD(['exec mount -o remount,rw -t yaffs2 /dev/block/mtdblock3 /system'])
                dm.sendCMD(['exec rm %s' % hosts_file])
            except devicemanager.DMError, e:
                self.exit_on_error("Unable to remove %s: %s!" % (hosts_file,
                                   str(e)))
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
