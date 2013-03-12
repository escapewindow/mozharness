#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****
"""poc_gh-gmo.py

Proof of concept for github<->gitmo conversions.
"""

import os
import sys

sys.path.insert(1, os.path.dirname(sys.path[0]))

from mozharness.base.log import FATAL
from mozharness.base.script import BaseScript
from mozharness.base.vcs.vcsbase import VCSMixin


# GithubScript {{{1
class GithubScript(VCSMixin, BaseScript):
#    config_options = [[
#        ["--test-file", ],
#        {"action": "extend",
#         "dest": "test_files",
#         "help": "Specify which config files to test"
#         }
#    ]]

    def __init__(self, require_config_file=False):
        super(GithubScript, self).__init__(
            #config_options=self.config_options,
            all_actions=[
                'clobber',
                'create-stage-mirror',
                'create-work-mirror',
                'create-test-target',
                'update-stage-mirror',
                'update-work-mirror',
                'push',
            ],
            default_actions=[
                'clobber',
                'create-stage-mirror',
                'create-test-target',
            ],
            require_config_file=require_config_file
        )

    def _init_git_repo(self, path, bare=False):
        git = self.query_exe("git", return_type="list")
        cmd = git + ["init"]
        if bare:
            cmd.append("--bare")
        cmd.append(path)
        return self.retry(self.run_command, args=(cmd, ), error_level=FATAL, error_message="Can't set up %s!" % path)

    def query_repo_dest(self, repo_config, dest_type):
        dirs = self.query_abs_dirs()
        return os.path.join(dirs['abs_work_dir'], repo_config[dest_type])

    def create_stage_mirror(self):
        for repo_config in self.config['repos']:
            source_dest = self.query_repo_dest(repo_config, 'source_dest')
            target_dest = self.query_repo_dest(repo_config, 'target_dest')
            git = self.query_exe('git', return_type='list')
            if not os.path.exists(source_dest):
                self._init_git_repo(source_dest, bare=True)
                if repo_config["workflow_type"] == "github":
                    self.run_command(
                        git + ['config', '--add', 'remote.origin.url', target_dest],
                        cwd=source_dest,
                    )
                    for branch in repo_config['branches'].keys():
                        self.run_command(
                            git + ['config', '--add', 'remote.origin.fetch',
                                   '+refs/heads/nightly:refs/heads/%s' % branch],
                            cwd=source_dest,
                        )
            else:
                self.info("%s already exists; skipping." % source_dest)

    def create_test_target(self):
        for repo_config in self.config['repos']:
            # for testing only: create local git repos to push to
            target_dest = self.query_repo_dest(repo_config, 'target_dest')
            if not os.path.exists(target_dest):
                self.info("Creating local target repo %s." % target_dest)
                self._init_git_repo(target_dest)

    def update_stage_mirror(self):
        pass
#            cmd = git + ['fetch']
#            self.retry(
#                self.run_command,
#                args=(cmd, ),
#                kwargs={'cwd': source_dest},
#            )

# __main__ {{{1
if __name__ == '__main__':
    conversion = GithubScript()
    conversion.run()
