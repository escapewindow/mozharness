#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****
'''Interact with mozpool/lifeguard/bmm.
'''

import sys

try:
    import simplejson as json
except ImportError:
    import json

from mozharness.base.log import LogMixin, DEBUG, WARNING, FATAL
from mozharness.base.script import ShellMixin, OSMixin



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

    def url_get(self, url, auth=None, params=None, num_retries=None,
                decode_json=False, verbose_level=DEBUG, **kwargs):
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
            error_level = WARNING
            if try_num == num_retries:
                error_level = FATAL
            try:
                r = requests.get(url, **kwargs)
                if verbose_level:
                    self.log(r.text, level=verbose_level)
                if decode_json:
                    j = self.decode_json(r.text)
                    if j is not None:
                        return j
                    else:
                        self.log("Try %d: Can't decode json from %s!" % (try_num, url), level=error_level)
                else:
                    return r.text
            except requests.exceptions.RequestException, e:
                self.log("Try %d: Can't get %s: %s!" % (try_num, url, str(e)),
                         level=error_level)

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
    def query_full_device_list(self):
        return self.partial_url_get("/api/device/list/", decode_json=True).get("devices")

    def query_full_device_details(self):
        return self.partial_url_get("/api/device/list?details=1", decode_json=True).get("devices")



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
