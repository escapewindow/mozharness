#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****
"""Generic signing methods.
"""

import hashlib
import os

from mozharness.base.errors import ZipErrorList
from mozharness.base.log import IGNORE

UnsignApkErrorList = [{
    'substr': r'''zip warning: name not matched: 'META-INF/*''',
    'level': IGNORE,
    'explanation': 'apk is already unsigned.'
},{
    'substr': r'''zip error: Nothing to do!''',
    'level': IGNORE,
}] + ZipErrorList



# BaseSigningMixin {{{1
class BaseSigningMixin(object):
    """Generic signing helper methods.
    """
    def query_filesize(self, file_path):
        self.info("Determining filesize for %s" % file_path)
        length = os.path.getsize(file_path)
        self.info(" %s" % str(length))
        return length

    # TODO this should be parallelized with the to-be-written BaseHelper!
    def query_sha512sum(self, file_path):
        self.info("Determining sha512sum for %s" % file_path)
        m = hashlib.sha512()
        fh = open(file_path, 'rb')
        contents = fh.read()
        fh.close()
        m.update(contents)
        sha512 = m.hexdigest()
        self.info(" %s" % sha512)
        return sha512



# AndroidSigningMixin {{{1
class AndroidSigningMixin(object):
    def sign_apk(self, apk):
        pass

    def unsign_apk(self, apk):
        zip_bin = self.query_exe("zip")
        return self.run_command([zip_bin, apk, '-d', 'META-INF/*'],
                                error_list=UnsignApkErrorList,
                                success_codes=[0, 12])
