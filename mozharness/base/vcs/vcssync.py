#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****
""" VCS sync methods
"""

import os
import sys

sys.path.insert(1, os.path.dirname(os.path.dirname(os.path.dirname(sys.path[0]))))

from mozharness.base.errors import HgErrorList
from mozharness.base.log import FATAL


class VCSSyncMixin(object):
    def init_git_repo(self, path, additional_args=None, error_level=FATAL):
        """ Create a git repo, with retries.

            We call this with additional_args=['--bare'] to save disk +
            make things cleaner.
            """
        git = self.query_exe("git", return_type="list")
        cmd = git + ['init']
        # generally for --bare
        if additional_args:
            cmd.extend(additional_args)
        cmd.append(path)
        return self.retry(
            self.run_command,
            args=(cmd, ),
            error_level=error_level,
            error_message="Can't set up %s!" % path
        )

    def _update_hg_stage_repo(self, repo_config, retry=True, clobber=False,
                              verify=False):
        """ Update a stage repo.
            See update_stage_mirror() for a description of the stage repos.
            """
        hg = self.query_exe('hg', return_type='list')
        dirs = self.query_abs_dirs()
        source_dest = os.path.join(dirs['abs_source_dir'],
                                   repo_config['repo_name'])
        if clobber:
            self.rmtree(source_dest)
        if not os.path.exists(source_dest):
            if self.retry(
                self.run_command,
                args=(hg + ['clone', '--noupdate', repo_config['repo'],
                      source_dest], ),
                kwargs={
                    'output_timeout': 15 * 60,
                    'cwd': dirs['abs_work_dir'],
                    'error_list': HgErrorList,
                },
            ):
                if retry:
                    return self._update_stage_repo(
                        repo_config, retry=False, clobber=True)
                else:
                    self.fatal("Can't clone %s!" % repo_config['repo'])
        cmd = hg + ['pull']
        if self.retry(
            self.run_command,
            args=(cmd, ),
            kwargs={
                'output_timeout': 15 * 60,
                'cwd': source_dest,
            },
        ):
            if retry:
                return self._update_stage_repo(
                    repo_config, retry=False, clobber=True)
            else:
                self.fatal("Can't pull %s!" % repo_config['repo'])
        # hg verify takes ~5min per repo; hopefully exit codes will save us
        if verify:
            if self.run_command(hg + ["verify"], cwd=source_dest):
                if retry:
                    return self._update_stage_repo(repo_config, retry=False, clobber=True)
                else:
                    self.fatal("Can't verify %s!" % source_dest)
