#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****
'''Interact with mozpool/lifeguard/bmm.
'''

import urllib2

try:
    import simplejson as json
except ImportError:
    import json

from mozharness.base.log import FATAL



class MozpoolMixin(object):
    """ Depends on OSMixin.
    """
    mozpool_api_url = None
    mozpool_timeout = 60

    def get_text_from_url(self, url=None, partial_url=None, **kwargs):
        """Generic get output from a url method; this can probably be
        moved into mozharness.base.script
        """
        if url is None:
            if partial_url is None:
                self.fatal("get_text_from_url() requires either url or partial_url to be specified!")
            url = self.mozpool_api_url + partial_url
        if kwargs.get("timeout") is None:
            kwargs["timeout"] = self.mozpool_timeout
        if kwargs.get("num_retries") is None:
            kwargs["num_retries"] = self.config.get("global_retries", 10)
        return super(MozpoolMixin, self).get_text_from_url(url, **kwargs)

    def query_full_device_list(self):
        return json.loads(self.get_text_from_url(partial_url="/api/device/list/")).get("devices")
