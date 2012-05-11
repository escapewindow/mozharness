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

from mozharness.base.log import FATAL
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
     ['--source-type',],
     {"action": "store",
      "dest": "source_type",
      "type": "choice",
      "choices": VALID_SOURCE_TYPES,
      "default": "bundle",
      "help": "Specify what kind of source release (bundle or text file)"
     }
    ],[
     ['--revision-source',],
     {"action": "store",
      "dest": "revision_source",
      "type": "choice",
      "choices": VALID_REVISION_SOURCES,
      "default": "hgweb",
      "help": "Specify where we get the revision from (for --source-type text)"
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
        if c['source_type'] == "text":
            if os.path.isabs(c['template']):
                self.template = c['template']
            else:
                self.template = os.path.join(dirs['abs_work_dir'], c['template'])
        else:
            # TODO write bundle
            pass

# helper methods {{{1

    def parse_hgweb(self, url):
        dirs = self.query_abs_dirs()
        tmp_path = os.path.join(dirs['abs_work_dir'], 'hgweb.html')
        self.mkdir_p(dirs['abs_work_dir'])
        wget = self.query_exe('wget')
        if self.run_command([wget, url, '-O', tmp_path]):
            self.fatal("Can't wget %s!" % url)
        contents = self.read_from_file(tmp_path)
        m = re.compile(' \d+:([0-9a-f]{12})')
        for line in contents.splitlines():
            r = m.search(contents)
            if r:
                revision = r.groups()[0]
                self.info("Found revision %s" % revision)
                return revision
        self.fatal("Can't find revision in %s!" % url)

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

    def create_source_bundle(self):
        pass

    def create_source_text(self):
        c = self.config
        rc = self.query_release_config()
        dirs = self.query_abs_dirs()
        template = self.read_from_file(self.template)
        self.info(template)
        for repo_nick in c['source_repo_nicks']:
            repo_dict = rc['release_dict']['sourceRepositories'][repo_nick]
            replace_dict = {'BRANCH': repo_dict['path']}
            if c['revision_source'] == "hgweb":
                tag = '%s_RELEASE' % rc['release_dict']['baseTag']
                url = '%s/%s/rev/%s_RELEASE' % (c['hgweb_server'], repo_dict['path'], rc['release_dict']['baseTag'])
                replace_dict['REVISION'] = self.parse_hgweb(url)
            else:
                replace_dict['REVISION'] = repo_dict['revision']
            file_path = os.path.join(dirs['abs_upload_dir'], 'source', '%s-%s.txt' % (rc['release_dict']['productName'], rc['version']))
            self.info(str(replace_dict))
            contents = template % replace_dict
            self.write_to_file(file_path, contents, create_parent_dir=True,
                               error_level=FATAL)

    def create_source(self):
        c = self.config
        if c['source_type'] == "bundle":
            return self.create_source_bundle()
        else:
            return self.create_source_text()

    def upload(self):
        pass

# main {{{1
if __name__ == '__main__':
    source_text = SourceRelease()
    source_text.run()
