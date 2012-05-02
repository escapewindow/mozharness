#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****
"""source_text.py

SingleSourceFactory, or a text file.
"""

from copy import deepcopy
import os
import re
import sys

# load modules from parent dir
sys.path.insert(1, os.path.dirname(sys.path[0]))

from mozharness.base.transfer import TransferMixin
from mozharness.base.vcs.vcsbase import MercurialScript
from mozharness.mozilla.buildbot import BuildbotMixin
from mozharness.mozilla.release import ReleaseMixin


VALID_REVISION_SOURCES = ["hgweb", "revision"]
VALID_SOURCE_TYPES = ["bundle", "text"]


# SourceRelease {{{1
class SourceRelease(ReleaseMixin, TransferMixin, BuildbotMixin, MercurialScript):
    config_options = [[
     ['--tag-override',],
     {"action": "store",
      "dest": "tag_override",
      "type": "string",
      "help": "Override the tags set for all repos"
     }
    ],[
     ['--user-repo-override',],
     {"action": "store",
      "dest": "user_repo_override",
      "type": "string",
      "help": "Override the user repo path for all repos"
     }
    ],[
     ['--release-config-file',],
     {"action": "store",
      "dest": "release_config_file",
      "type": "string",
      "help": "Specify the release config file to use"
     }
    ],[
     ['--revision-source',],
     {"action": "store",
      "dest": "revision_source",
      "type": "choice",
      "choices": VALID_REVISION_SOURCES,
      "default": "hgweb",
      "help": "Specify where we get the revision from"
     }
    ],[
     ['--template',],
     {"action": "store",
      "dest": "template",
      "default": "buildbot-configs/mozilla/release_templates/source_text",
      "help": "Specify the release source template"
     }
    ],[
     ['--source-repo-nick',],
     {"action": "extend",
      "dest": "source_repo_nicks",
      "help": "Specify the release source nick"
     }
    ]]

    def __init__(self, require_config_file=True):
        super(SourceRelease, self).__init__(
            config_options=self.config_options,
            all_actions=[
                "clobber",
                "pull",
                "create-source",
                "upload",
            ],
            require_config_file=require_config_file,
            config={
                "repos": [{
                    "repo": "http://hg.mozilla.org/%(user_repo_override)s/buildbot-configs",
                    "dest": "buildbot-configs",
                    "revision": "production",
                }],
                "user_repo_override": "build",
            },
        )
        c = self.config
        dirs = self.query_abs_dirs()
        if os.path.isabs(c['template']):
            self.template = c['template']
        else:
            self.template = os.path.join(dirs['abs_work_dir'], c['template'])

# helper methods {{{1

    def parse_hgweb(self):
        pass

# actions {{{1
    # clobber is defined in BaseScript

    def pull(self):
        c = self.config
        dirs = self.query_abs_dirs()
        repos = []
        replace_dict = {}
        if c.get("user_repo_override"):
            replace_dict['user_repo_override'] = c['user_repo_override']
            # deepcopy() needed because of self.config lock bug :(
            for repo_dict in deepcopy(c['repos']):
                repo_dict['repo'] = repo_dict['repo'] % replace_dict
                repos.append(repo_dict)
        else:
            repos = c['repos']
        self.vcs_checkout_repos(repos, parent_dir=dirs['abs_work_dir'],
                                tag_override=c.get('tag_override'))

    def create_source(self):
        c = self.config
        rc = self.query_release_config()
        if c['source_type'] == "bundle":
            pass
        else:
            pass
        if c['revision_source'] == "hgweb":
            source_info = self.parse_hgweb()
        else:
            pass

    def upload(self):
        pass

# main {{{1
if __name__ == '__main__':
    source_text = SourceRelease()
    source_text.run()
