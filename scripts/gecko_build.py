#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****
"""gecko_build.py

Build Gecko.  Oriented towards Firefox currently.
"""

import os
import sys

sys.path.insert(1, os.path.dirname(sys.path[0]))

from mozharness.base.vcs.vcsbase import MercurialScript


# GeckoBuild {{{1
class GeckoBuild(MercurialScript):
    config_options = []

    def __init__(self, require_config_file=False):
        self.config_files = []
        MercurialScript.__init__(
            self, config_options=self.config_options,
            all_actions=[
                'clobber',
            ],
            default_actions=[
                'clobber',
            ],
            require_config_file=require_config_file)


# __main__ {{{1
if __name__ == '__main__':
    gecko_build = GeckoBuild()
    gecko_build.run()
