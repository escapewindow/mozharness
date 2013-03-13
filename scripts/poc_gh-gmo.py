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

from mozharness.base.script import BaseScript
from mozharness.base.vcs.vcsbase import VCSMixin, VCSConversionMixin


# GithubScript {{{1
class GithubScript(VCSMixin, VCSConversionMixin, BaseScript):

    def __init__(self, require_config_file=False):
        super(GithubScript, self).__init__(
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
                'create-work-mirror',
                'create-test-target',
                'update-stage-mirror',
                'update-work-mirror',
                'push',
            ],
            require_config_file=require_config_file
        )

    def create_stage_mirror(self):
        for repo_config in self.config['repos']:
            source_dest = self.query_repo_dest(repo_config, 'source_dest')
            git = self.query_exe('git', return_type='list')
            if not os.path.exists(source_dest):
                if repo_config.get("branches"):
                    self.init_git_repo(source_dest, additional_args=['--bare'])
                    self.run_command(
                        git + ['config', '--add', 'remote.origin.url', repo_config['repo']],
                        cwd=source_dest,
                    )
                    for branch_source in repo_config['branches'].keys():
                        branch_target = repo_config['branches'][branch_source]
                        cmd = git + ['config', '--add', 'remote.origin.fetch',
                                     '+refs/heads/%s:refs/heads/%s' % (branch_source, branch_target)],
                        self.retry(
                            self.run_command,
                            args=(cmd),
                            kwargs={'cwd': source_dest},
                        )
                else:
                    self.fatal("No branches specified for %s; not written yet!" % repo_config['repo'])
            else:
                self.info("%s already exists; skipping." % source_dest)

    def create_work_mirror(self):
        git = self.query_exe("git", return_type="list")
        for repo_config in self.config['repos']:
            work_dest = self.query_repo_dest(repo_config, 'work_dest')
            source_dest = self.query_repo_dest(repo_config, 'source_dest')
            if not os.path.exists(work_dest):
                # clone --mirror for now, which may or may not work.
                self.run_command(git + ["clone", "--mirror", source_dest, work_dest])
            else:
                self.info("%s already exists; skipping." % work_dest)

    def create_test_target(self):
        for repo_config in self.config['repos']:
            # for testing only: create local git repos to push to
            target_dest = self.query_repo_dest(repo_config, 'target_dest')
            if not os.path.exists(target_dest):
                self.info("Creating local target repo %s." % target_dest)
                self.init_git_repo(target_dest, additional_args=['--bare'])

    def _update_mirror(self, dest_type="source_dest"):
        git = self.query_exe("git", return_type="list")
        for repo_config in self.config['repos']:
            dest = self.query_repo_dest(repo_config, dest_type)
            cmd = git + ['fetch', '--force']
            self.retry(
                self.run_command,
                args=(cmd, ),
                kwargs={'cwd': dest},
            )
            # TODO on failure, nuke and re-create stage mirror, not work mirror
            # TODO I'm pulling tags as well as branches; limit?

    def update_stage_mirror(self):
        self._update_mirror()

    def update_work_mirror(self):
        self._update_mirror(dest_type="work_dest")

    def push(self):
        git = self.query_exe('git', return_type='list')
        for repo_config in self.config['repos']:
            work_dest = self.query_repo_dest(repo_config, 'work_dest')
            target_dest = self.query_repo_dest(repo_config, 'target_dest')
            self.run_command(git + ['push', '--force', '--mirror', target_dest],
                             cwd=work_dest)

# __main__ {{{1
if __name__ == '__main__':
    conversion = GithubScript()
    conversion.run()
