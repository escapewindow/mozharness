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
'''Interact with ADB.

This code is largely from
http://hg.mozilla.org/build/tools/file/default/sut_tools

Currently angling for ADB support only.
'''

import os
import re
import signal
import subprocess
import sys
import time

from mozharness.base.errors import PythonErrorList, BaseErrorList, ADBErrorList
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
  "help": "Specify the IP address of the device."
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
    '''BaseScript mixin, designed to interface with the device.

    '''
    device_root = None
    device_serial = None

    def _query_config_device_serial(self):
        c = self.config
        if c.get('device_serial'):
            return c['device_serial']
        if c.get('device_ip'):
            return "%s:%s" % (c['device_ip'], c.get('device_port', 5555))

    def _query_attached_devices(self):
        devices = []
        output = self.get_output_from_command("adb devices")
        starting_list = False
        for line in output:
            if 'adb: command not found' in line:
                self.fatal("Can't find adb; install the Android SDK!")
            if line.startswith("* daemon"):
                continue
            if line.startswith("List of devices"):
                starting_list = True
                continue
            # TODO somehow otherwise determine whether this is an actual
            # device?
            if starting_list:
                devices.append(re.split('\s+', line)[0])
        return devices

    def query_device_serial(self, auto_connect=False):
        if self.device_serial:
            return self.device_serial
        c = self.config
        device_serial = self._query_config_device_serial()
        if device_serial:
            if auto_connect:
                self.ping_device(auto_connect=True)
        else:
            self.info("Trying to find device...")
            devices = self._query_attached_devices()
            if not devices:
                self.fatal("No device attached via adb!\nUse 'adb connect' or specify a device_serial or device_ip in config!")
            elif len(devices) > 1:
                self.warning("""More than one device detected; specify 'device_serial' or\n'device_ip' to target a specific device!""")
            device_serial = devices[0]
            self.info("Found %s." % device_serial)
        self.device_serial = device_serial
        return self.device_serial

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

    # device calls {{{2
    def query_device_root(self, silent=False):
        if self.device_root:
            return self.device_root
        device_root = None
        device_serial = self.query_device_serial()
        output = self.get_output_from_command("adb -s %s shell df" % device_serial,
                                              silent=silent)
        # TODO this assumes we're connected; error checking?
        if "/mnt/sdcard" in output:
            device_root = "/mnt/sdcard/tests"
        elif ' not found' in output:
            self.error("Can't get output from 'adb shell df'!\n%s" % output)
            return None
        else:
            device_root = "/data/local/tmp/tests"
        if not silent:
            self.info("Device root is %s" % device_root)
        self.device_root = device_root
        return self.device_root

    def wait_for_device(self, interval=60, max_attempts=20):
        self.info("Waiting for device to come back...")
        time.sleep(interval)
        tries = 0
        while tries <= max_attempts:
            tries += 1
            self.info("Try %d" % tries)
            if self.ping_device(auto_connect=True, silent=True):
                return self.ping_device()
            time.sleep(interval)
        raise DeviceException, "Remote Device Error: waiting for device timed out."

    def query_device_time(self):
        c = self.config
        serial = self.query_device_serial()
        # adb shell 'date' will give a date string
        date_string = self.get_output_from_command(["adb", "-s", serial,
                                                    "shell", "date"])
        # TODO what to do when we error?
        return date_string

    def set_device_time(self, device_time=None, error_level='error'):
        # adb shell date UNIXTIMESTAMP will set date
        c = self.config
        serial = self.query_device_serial()
        if device_time is None:
            device_time = time.time()
        self.info(self.query_device_time())
        status = self.run_command(["adb", "-s", serial,  "shell", "date",
                                   str(device_time)],
                                  error_list=ADBErrorList)
        self.info(self.query_device_time())
        return status

    def query_device_file_exists(self, file_name):
        device_serial = self.query_device_serial()
        output = self.get_output_from_command(["adb", "-s", device_serial,
                                               "shell", "ls", "-d", file_name])
        if output.rstrip() == file_name:
            return True
        return False

    def remove_device_root(self, error_level='error'):
        device_root = self.query_device_root()
        device_serial = self.query_device_serial()
        if device_root is None:
            self.fatal("Can't connect to device!")
        if self.query_device_file_exists(device_root):
            self.info("Removing device root %s." % device_root)
            self.run_command(["adb", "-s", device_serial, "shell", "rm",
                              "-r", device_root], error_list=ADBErrorList)
            if self.query_device_file_exists(device_root):
                self.log("Unable to remove device root!", level=error_level)
                return False
        return True

    def uninstall_app(self, package_name, package_root="/data/data",
                      error_level="error"):
        c = self.config
        device_serial = self.query_device_serial()
        self.info("Uninstalling %s..." % package_name)
        if self.query_device_file_exists('%s/%s' % (package_root, package_name)):
            cmd = ["adb", "-s", device_serial, "uninstall"]
            if not c.get('enable_automation'):
                cmd.append("-k")
            cmd.append(package_name)
            status = self.run_command(cmd, error_list=ADBErrorList)
            # TODO is this the right error check?
            if status:
                self.log("Failed to uninstall %s!" % package_name,
                         level=error_level)

    # Maintenance {{{2
    def exit_on_error(self, message, **kwargs):
        '''When exit_on_error is defined, a FATAL log call will call it
        and use the message and other args from it.
        '''
        if self.config['enable_automation']:
            self.set_device_error_flag(message)
            message = "Remote Device Error: %s" % message
        return (message, kwargs)

    def connect_device(self):
        self.info("Connecting device...")
        cmd = ["adb", "connect"]
        device_serial = self._query_config_device_serial()
        if device_serial:
            devices = self._query_attached_devices()
            if device_serial in devices:
                # TODO is this the right behavior?
                self.disconnect_device()
            cmd.append(device_serial)
        status = self.run_command(cmd, error_list=ADBErrorList)

    def disconnect_device(self):
        self.info("Disconnecting device...")
        device_serial = self.query_device_serial()
        if device_serial:
            status = self.run_command(["adb", "-s", device_serial,
                                       "disconnect"],
                                      error_list=ADBErrorList)
#            self.device_serial = None
        else:
            self.info("No device found.")

    def reboot_device(self):
        if not self.ping_device(auto_connect=True):
            self.error("Can't reboot disconnected device!")
            return False
        device_serial = self.query_device_serial()
        self.info("Rebooting device...")
        cmd = ["adb", "-s", device_serial, "reboot"]
        self.info("Running command (in the background): %s" % cmd)
        # This won't exit until much later, but we don't need to wait.
        # However, some error checking would be good.
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT)
        time.sleep(10)
        self.disconnect_device()
        status = False
        try:
            self.wait_for_device()
            status = True
        except DeviceException:
            self.error("Can't reconnect to device!")
        return status

    def ping_device(self, auto_connect=False, silent=False):
        c = self.config
        if auto_connect and not self._query_attached_devices():
            self.connect_device()
        if not silent:
            self.info("Determining device connectivity over adb...")
        serial = self.query_device_serial()
        output = self.get_output_from_command(["adb", "-s", serial,
                                               "shell", "uptime"],
                                              silent=silent)
        if str(output).startswith("up time:"):
            if not silent:
                self.info("Found %s." % serial)
            return True
        elif auto_connect:
            # TODO retry?
            self.connect_device()
            return self.ping_device()
        else:
            if not silent:
                self.error("Can't find a device.")
            return False

    def check_device(self):
        if not self.ping_device(auto_connect=True):
            self.fatal("Can't find device!")
        if self.query_device_root() is None:
            self.fatal("Can't connect to device!")
        if self.config.get('enable_automation'):
            self.query_device_flags()

    def cleanup_device(self):
        self.info("Cleaning up device.")
        c = self.config
        device_serial = self.query_device_serial()
        status = self.remove_device_root()
        if not status:
            self.fatal("Can't remove device root!")
        if c.get("enable_automation"):
            self.remove_etc_hosts()
        if c.get("device_package_name"):
            self.run_command(["adb", "-s", device_serial, "shell",
                              "killall", c["device_package_name"]],
                              error_list=ADBErrorList)
            self.uninstall_app(c['device_package_name'])

    # Device-type-specific. {{{2

    def remove_etc_hosts(self, hosts_file="/system/etc/hosts"):
        c = self.config
        if c['device_type'] not in ("tegra250",):
            self.debug("No need to remove /etc/hosts on a non-Tegra250.")
            return
        device_serial = self.query_device_serial()
        if self.query_device_file_exists(hosts_file):
            self.info("Removing %s file." % hosts_file)
            self.run_command(["adb", "-s", device_serial, "shell",
                              "mount", "-o", "remount,rw", "-t", "yaffs2",
                              "/dev/block/mtdblock3", "/system"],
                             error_list=ADBErrorList)
            self.run_command(["adb", "-s", device_serial, "shell", "rm",
                              hosts_file])
            if self.query_device_file_exists(hosts_file):
                self.fatal("Unable to remove %s!" % hosts_file)
        else:
            self.debug("%s file doesn't exist; skipping." % hosts_file)



# ADBDevice {{{1
class ADBDevice(ShellMixin, OSMixin, LogMixin, DeviceMixin, object):
    def __init__(self, log_obj=None, config=None):
        super(ADBDevice, self).__init__()
        self.log_obj = log_obj
        self.config = config



# __main__ {{{1

if __name__ == '__main__':
    '''TODO: unit tests.
    '''
    pass
