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

    def query_all_repos(self):
        """ Very simple method, but we need this concatenated list many times
            throughout the script.
            """
        if self.config.get('initial_repo'):
            all_repos = [self.config['initial_repo']] + list(self.config['conversion_repos'])
        else:
            all_repos = list(self.config['conversion_repos'])
        return all_repos

    # Git specific {{{1
    def init_git_repo(self, path, additional_args=None):
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
            error_level=FATAL,
            error_message="Can't set up %s!" % path
        )

    def make_git_repo_bare(self, path, tmpdir=None):
        """ Since we do a |git checkout| in prepend_cvs(), and later want
            a bare repo.
            """
        self.info("Making %s/.git a bare repo..." % path)
        for p in (path, os.path.join(path, ".git")):
            if not os.path.exists(p):
                self.error("%s doesn't exist! Skipping..." % p)
        if tmpdir is None:
            tmpdir = os.path.dirname(os.path.abspath(path))
        git = self.query_exe("git", return_type="list")
        # Hardcode: assumes only git + hg
        for dirname in (".git", ".hg"):
            if os.path.exists(os.path.join(path, dirname)):
                self.move(
                    os.path.join(path, dirname),
                    os.path.join(tmpdir, dirname),
                    error_level=FATAL,
                )
        self.rmtree(path, error_level=FATAL)
        self.mkdir_p(path)
        # Hardcode: assumes only git + hg
        for dirname in (".git", ".hg"):
            if os.path.exists(os.path.join(tmpdir, dirname)):
                self.move(
                    os.path.join(tmpdir, dirname),
                    os.path.join(path, dirname),
                    error_level=FATAL,
                )
        self.run_command(
            git + ['--git-dir', os.path.join(path, ".git"),
                   'config', '--bool', 'core.bare', 'true'],
            halt_on_failure=True,
        )

    # HG specific {{{1
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
