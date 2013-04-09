#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****
"""poc_beagle.py

Proof of concept for multi-repo m-c hg<->gitmo conversions with cvs prepending.
"""

import os
import sys

sys.path.insert(1, os.path.dirname(sys.path[0]))

from mozharness.base.log import FATAL
from mozharness.base.python import VirtualenvMixin, virtualenv_config_options
from mozharness.base.script import BaseScript
from mozharness.base.vcs.vcsbase import VCSMixin, VCSConversionMixin


# HgGitScript {{{1
class HgGitScript(VCSMixin, VCSConversionMixin, VirtualenvMixin, BaseScript):

    def __init__(self, require_config_file=True):
        super(HgGitScript, self).__init__(
            config_options=virtualenv_config_options,
            all_actions=[
                'clobber',
                'create-virtualenv',
                'create-stage-mirror',
                'create-work-mirror',
                'create-test-target',
                'update-stage-mirror',
                'update-work-mirror',
                'convert-work-mirror',
                'prepend-cvs',
                'create-map-file',
                'verify',
                'push',
                'notify',
            ],
            default_actions=[
                'clobber',
                'create-virtualenv',
                'create-stage-mirror',
                'create-work-mirror',
                'create-test-target',
                #'update-stage-mirror',
                #'update-work-mirror',
                #'push',
            ],
            require_config_file=require_config_file
        )

    def _init_hg_repo(self, path, additional_args=None):
        hg = self.query_exe("hg", return_type="list")
        cmd = hg + ['init']
        if additional_args:
            cmd.extend(additional_args)
        cmd.append(path)
        return self.retry(self.run_command, args=(cmd, ), error_level=FATAL, error_message="Can't set up %s!" % path)

    def create_stage_mirror(self):
        hg = self.query_exe('hg', return_type='list')
        dirs = self.query_abs_dirs()
        for repo_config in self.config['repos']:
            source_dest = self.query_repo_dest(repo_config, 'source_dest')
            if not os.path.exists(source_dest):
                if repo_config.get('vcs', 'hg') == 'hg':
                    self.retry(
                        self.run_command,
                        args=(hg + ['clone', '--noupdate', repo_config['repo'], source_dest], ),
                        kwargs={
#                            'idle_timeout': 15 * 60,
                            'cwd': dirs['abs_work_dir'],
                        }
                    )
                else:
                    # TODO git
                    self.fatal("Don't know how to deal with vcs %s!" % repo_config['vcs'])
            else:
                self.info("%s already exists; skipping." % source_dest)

    def create_work_mirror(self):
        hg = self.query_exe("hg", return_type="list")
        git = self.query_exe("git", return_type="list")
        for repo_config in self.config['repos']:
            work_dest = self.query_repo_dest(repo_config, 'work_dest')
            source_dest = self.query_repo_dest(repo_config, 'source_dest')
            if repo_config.get('vcs', 'hg') == 'hg':
                if not os.path.exists(work_dest):
                    self.run_command(hg + ["init", work_dest])
                self.run_command(hg + ["pull", source_dest],
                                 cwd=work_dest)
                # Create .git for conversion, if it doesn't exist
                git_dir = os.path.join(work_dest, '.git')
                if not os.path.exists(git_dir):
                    self.run_command(git + ['init'], cwd=work_dest)
                    self.run_command(git + ['--git-dir', git_dir, 'config', 'gc.auto', '0'], cwd=work_dest)
                # Update .hg/hgrc, if not already updated
                hgrc = os.path.join(work_dest, '.hg', 'hgrc')
                contents = ''
                if os.path.exists(hgrc):
                    contents = self.read_from_file(hgrc)
                if 'hggit=' not in contents:
                    hgrc_update = """[extensions]
hggit=
[git]
intree=1
"""
                    self.write_to_file(hgrc, hgrc_update, open_mode='a')
            else:
                self.fatal("Don't know how to deal with vcs %s!" % repo_config['vcs'])
                # TODO git

    def create_test_target(self):
        dirs = self.query_abs_dirs()
        for repo_config in self.config['repos']:
            for target_config in repo_config['targets']:
                target_dest = os.path.join(dirs['abs_work_dir'], target_config['target_dest'])
                if not os.path.exists(target_dest):
                    self.info("Creating local target repo %s." % target_dest)
                    if target_config.get("vcs", "git") == "git":
                        self.init_git_repo(target_dest, additional_args=['--bare'])
                    else:
                        self.fatal("Don't know how to deal with vcs %s!" % target_config['vcs'])
                        # TODO hg
                else:
                    self.debug("%s exists; skipping." % target_dest)

    def update_stage_mirror(self):
        hg = self.query_exe("hg", return_type="list")
        dirs = self.query_abs_dirs()
        for repo_config in self.config['repos']:
            dest = os.path.join(dirs['abs_work_dir'], repo_config['source_dest'])
            cmd = hg + ['pull']
            self.retry(
                self.run_command,
                args=(cmd, ),
                kwargs={
                    #'idle_timeout': 15 * 60,
                    'cwd': dest,
                },
            )
            # TODO on failure, nuke and re-create stage mirror, not work mirror
            # TODO I'm pulling tags as well as branches; limit?

    def update_work_mirror(self):
        hg = self.query_exe("hg", return_type="list")
        dirs = self.query_abs_dirs()
        for repo_config in self.config['repos']:
            source = os.path.join(dirs['abs_work_dir'], repo_config['source_dest'])
            dest = os.path.join(dirs['abs_work_dir'], repo_config['work_dest'])
            for (branch, target_branch) in repo_config['branches'].items():
                output = self.get_output_from_command(hg + ['id', '-r', branch], cwd=source)
                if output:
                    rev = output.split(' ')[0]
                self.run_command(hg + ['pull', '-r', rev, source], cwd=dest)
                self.run_command(hg + ['bookmark', '-f', '-r', rev, target_branch], cwd=dest)
                self.run_command(hg + ['-v', 'gexport'], cwd=dest)
        # TODO error checking, idle timeouts

    def push(self):
        git = self.query_exe('git', return_type='list')
        for repo_config in self.config['repos']:
            work_dest = self.query_repo_dest(repo_config, 'work_dest')
            target_dest = self.query_repo_dest(repo_config, 'target_dest')
            self.run_command(git + ['push', '--force', '--mirror', target_dest],
                             cwd=work_dest)

# __main__ {{{1
if __name__ == '__main__':
    conversion = HgGitScript()
    conversion.run()
