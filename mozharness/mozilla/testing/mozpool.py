#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****
'''Interact with mozpool/lifeguard/bmm.
'''

import sys
import time

try:
    import simplejson as json
except ImportError:
    import json

from mozharness.base.log import LogMixin, DEBUG, WARNING, FATAL
from mozharness.base.script import ShellMixin, OSMixin

# TODO do something with r.status_code?
# 200 OK
# 201 Created
# 202 Accepted
# 300 Multiple Choices
# 301 Moved Permanently
# 302 Found
# 304 Not Modified
# 400 Bad Request
# 401 Unauthorized
# 403 Forbidden
# 404 Not Found
# 500 Server Error
# 501 Not Implemented
# 503 Service Unavailable



# MozpoolHandler {{{1
class MozpoolHandler(ShellMixin, OSMixin, LogMixin):
    """ Depends on /requests/; if you don't have this installed you need to
    instantiate this after installing /requests/ via VirtualenvMixin.
    """
    def __init__(self, mozpool_api_url, mozpool_config=None, config=None,
                 log_obj=None, script_obj=None):
        self.config = config
        self.log_obj = log_obj
        super(MozpoolHandler, self).__init__()
        self.mozpool_api_url = mozpool_api_url
        self.mozpool_config = mozpool_config or {}
        self.script_obj = script_obj
        self.mozpool_auth = self.mozpool_config.get("mozpool_auth")
        self.mozpool_timeout = self.mozpool_config.get("mozpool_timeout", 60)
        try:
            site_packages_path = self.script_obj.query_python_site_packages_path()
            sys.path.append(site_packages_path)
            global requests
            requests = __import__('requests', globals(), locals(), [], -1)
        except ImportError:
            self.fatal("Can't instantiate MozpoolHandler until requests python package is installed! (VirtualenvMixin?)")

    # Helper methods {{{2
    def url_get(self, url, auth=None, params=None, num_retries=None,
                decode_json=True, error_level=FATAL, verbose_level=DEBUG,
                **kwargs):
        """Generic get output from a url method; this can probably be
        moved into mozharness.base.script
        """
        self.info("Request GET %s..." % url)
        if kwargs.get("timeout") is None:
            kwargs["timeout"] = self.mozpool_timeout
        if kwargs.get("auth") is None and self.mozpool_auth:
            kwargs["auth"] = self.mozpool_auth
        if num_retries is None:
            num_retries = self.config.get("global_retries", 10)
        try_num = 0
        while try_num <= num_retries:
            try_num += 1
            log_level = WARNING
            if try_num == num_retries:
                log_level = error_level
            try:
                r = requests.get(url, **kwargs)
                self.info("Status code: %s" % str(r.status_code))
                if verbose_level:
                    self.log(r.text, level=verbose_level)
                if decode_json:
                    j = self.decode_json(r.text)
                    if j is not None:
                        return j
                    else:
                        self.log("Try %d: Can't decode json from %s!" % (try_num, url), level=log_level)
                else:
                    return r.text
            except requests.exceptions.RequestException, e:
                self.log("Try %d: Can't get %s: %s!" % (try_num, url, str(e)),
                         level=log_level)
            if try_num <= num_retries:
                sleep_time = 2 * try_num
                self.info("Sleeping %d..." % sleep_time)
                time.sleep(sleep_time)

    def partial_url_get(self, partial_url, **kwargs):
        return self.url_get(self.mozpool_api_url + partial_url, **kwargs)

    def decode_json(self, contents, error_level=WARNING):
        try:
            return json.loads(contents, encoding="ascii")
        except ValueError, e:
            self.log("Can't decode json: %s!" % str(e), level=error_level)
        except TypeError, e:
            self.log("Can't decode json: %s!" % str(e), level=error_level)
        else:
            self.log("Can't decode json: Unknown error!" % str(e), level=error_level)

    # TODO we could do some caching and more error checking
    # Device queries {{{2
    def query_all_device_list(self, **kwargs):
        return self.partial_url_get("/api/device/list/", **kwargs).get("devices")

    def query_all_device_details(self, **kwargs):
        return self.partial_url_get("/api/device/list?details=1", **kwargs).get("devices")

    def query_device_status(self, device, error_level=WARNING, **kwargs):
        """ Defaults to WARNING because we may be asking about a device
        that doesn't exist and don't necessarily want to FATAL when we keep
        getting 500s.

        I imagine we may want to tweak these error levels later.
        """
        return self.partial_url_get("/api/device/%s/status/" % device,
                                    error_level=error_level, **kwargs)

    def query_device_details(self, device, error_level=WARNING, **kwargs):
        devices = self.query_all_device_details(**kwargs)
        if isinstance(devices, dict):
            if device not in devices:
                self.log("Couldn't find %s in device list!" % device,
                         level=error_level)
                return
            else:
                return devices[device]
        else:
            # We shouldn't get here if query_all_device_details() FATALs...
            self.log("Invalid response from query_all_device_details()!",
                     level=error_level)



# MozpoolMixin {{{1
class MozpoolMixin(object):
    mozpool_handler = None

    def query_mozpool_handler(self):
        if not self.mozpool_handler:
            if 'mozpool_api_url' not in self.config:
                self.fatal("Can't create mozpool handler without mozpool_api_url set!")
            mozpool_config = {}
            for var in ("mozpool_auth", "mozpool_timeout"):
                if self.config.get(var):
                    mozpool_config[var] = self.config[var]
            self.mozpool_handler = MozpoolHandler(
                self.config["mozpool_api_url"],
                config=self.config,
                log_obj=self.log_obj,
                script_obj=self,
            )
        return self.mozpool_handler
