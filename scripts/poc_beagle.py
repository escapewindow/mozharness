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

from mozharness.base.errors import HgErrorList, GitErrorList, TarErrorList
from mozharness.base.log import INFO, FATAL
from mozharness.base.python import VirtualenvMixin, virtualenv_config_options
from mozharness.base.vcs.vcsbase import VCSScript
from mozharness.mozilla.tooltool import TooltoolMixin


# HgGitScript {{{1
class HgGitScript(VirtualenvMixin, TooltoolMixin, VCSScript):

    def __init__(self, require_config_file=True):
        super(HgGitScript, self).__init__(
            config_options=virtualenv_config_options,
            all_actions=[
                'clobber',
                'create-virtualenv',
                'pull',
                'create-stage-mirror',
                'create-work-mirror',
                'initial-conversion',
                'prepend-cvs',
                'update-stage-mirror',
                'update-work-mirror',
                'push',
                'upload',
                'notify',
            ],
            default_actions=[
                'clobber',
                'pull',
                'create-virtualenv',
                'create-stage-mirror',
                'create-work-mirror',
                'initial-conversion',
                'prepend-cvs',
                'update-stage-mirror',
                'update-work-mirror',
                'push',
            ],
            require_config_file=require_config_file
        )

    # Helper methods {{{1
    def _init_hg_repo(self, path, additional_args=None):
        hg = self.query_exe("hg", return_type="list")
        cmd = hg + ['init']
        if additional_args:
            cmd.extend(additional_args)
        cmd.append(path)
        return self.retry(self.run_command, args=(cmd, ), error_level=FATAL, error_message="Can't set up %s!" % path)

    def query_abs_dirs(self):
        if self.abs_dirs:
            return self.abs_dirs
        abs_dirs = super(HgGitScript, self).query_abs_dirs()
        abs_dirs['abs_cvs_history_dir'] = os.path.join(abs_dirs['abs_work_dir'], 'mozilla-cvs-history')
        abs_dirs['abs_conversion_dir'] = os.path.join(abs_dirs['abs_work_dir'], 'conversion', self.config['conversion_dir'])
        abs_dirs['abs_source_dir'] = os.path.join(abs_dirs['abs_work_dir'], 'stage_source')
        abs_dirs['abs_repo_sync_tools_dir'] = os.path.join(abs_dirs['abs_work_dir'], 'repo-sync-tools')
        abs_dirs['abs_git_rewrite_dir'] = os.path.join(abs_dirs['abs_work_dir'], 'mc-git-rewrite')
        abs_dirs['abs_target_dir'] = os.path.join(abs_dirs['abs_work_dir'], 'target')
        self.abs_dirs = abs_dirs
        return self.abs_dirs

    def init_git_repo(self, path, additional_args=None):
        git = self.query_exe("git", return_type="list")
        cmd = git + ['init']
        # generally for --bare
        if additional_args:
            cmd.extend(additional_args)
        cmd.append(path)
        return self.retry(self.run_command, args=(cmd, ), error_level=FATAL, error_message="Can't set up %s!" % path)

    def query_all_repos(self):
        return [self.config['initial_repo']] + self.config['conversion_repos']

    def _update_stage_repo(self, repo_config, retry=True, clobber=False):
        hg = self.query_exe('hg', return_type='list')
        dirs = self.query_abs_dirs()
        source_dest = os.path.join(dirs['abs_source_dir'], repo_config['repo_name'])
        if clobber:
            self.rmtree(source_dest)
        if not os.path.exists(source_dest):
            if self.retry(
                self.run_command,
                args=(hg + ['clone', '--noupdate', repo_config['repo'], source_dest], ),
                kwargs={
#                   'idle_timeout': 15 * 60,
                    'cwd': dirs['abs_work_dir'],
                    'error_list': HgErrorList,
                },
            ):
                if retry:
                    return self._update_stage_repo(repo_config, retry=False, clobber=True)
                else:
                    self.fatal("Can't clone %s!" % repo_config['repo'])
        cmd = hg + ['pull']
        if self.retry(
            self.run_command,
            args=(cmd, ),
            kwargs={
                #'idle_timeout': 15 * 60,
                'cwd': source_dest,
            },
        ):
            if retry:
                return self._update_stage_repo(repo_config, retry=False, clobber=True)
            else:
                self.fatal("Can't pull %s!" % repo_config['repo'])
        if self.run_command(hg + ["verify"], cwd=source_dest):
            if retry:
                return self._update_stage_repo(repo_config, retry=False, clobber=True)
            else:
                self.fatal("Can't verify %s!" % source_dest)

    def _check_initial_git_revisions(self, repo_path, expected_sha1, expected_sha2):
        git = self.query_exe('git', return_type='list')
        output = self.get_output_from_command(git + ['log', '--oneline', '--grep', '374866'],
                                              cwd=repo_path)
        # hardcode test
        if not output:
            self.fatal("No output from git log!")
        rev = output.split(' ')[0]
        if not rev.startswith(expected_sha1):
            self.fatal("Output doesn't match expected sha %s for initial hg commit: %s" % (expected_sha1, str(output)))
        output = self.get_output_from_command(git + ['log', '-n', '1', '%s^' % rev],
                                              cwd=repo_path)
        if not output:
            self.fatal("No output from git log!")
        rev = output.splitlines()[0].split(' ')[1]
        if rev != expected_sha2:
            self.fatal("Output rev %s doesn't show expected rev %s:\n\n%s" % (rev, expected_sha2, output))

    def munge_mapfile(self):
        """ From https://github.com/ehsan/mozilla-history-tools/blob/master/initial_conversion/translate_git-mapfile.py
            """
        self.info("Updating pre-cvs mapfile...")
        dirs = self.query_abs_dirs()
        orig_mapfile = os.path.join(dirs['abs_upload_dir'], 'pre-cvs-mapfile')
        conversion_dir = dirs['abs_conversion_dir']
        mapfile = os.path.join(dirs['abs_work_dir'], 'post-cvs-mapfile')
        mapdir = os.path.join(dirs['abs_git_rewrite_dir'], 'map')
        orig_mapfile_fh = open(orig_mapfile, "r")
        mapfile_fh = open(mapfile, "w")
        for line in orig_mapfile_fh:
            tokens = line.split(" ")
            if len(tokens) == 2:
                git_sha = tokens[0].strip()
                hg_sha = tokens[1].strip()
                new_path = os.path.join(mapdir, git_sha)
                if os.path.exists(new_path):
                    translated_git_sha = open(new_path).read().strip()
                    print >>mapfile_fh, "%s %s" % (translated_git_sha, hg_sha)
                else:
                    print >>mapfile_fh, "%s %s" % (git_sha, hg_sha)
        orig_mapfile_fh.close()
        mapfile_fh.close()
        self.copyfile(mapfile, os.path.join(conversion_dir, '.hg', 'git-mapfile'))
        self.copy_to_upload_dir(mapfile, dest="post-cvs-mapfile", log_level=INFO)

    def make_repo_bare(self, path, tmpdir=None):
        self.info("Making %s/.git a bare repo..." % path)
        for p in (path, os.path.join(path, ".git")):
            if not os.path.exists(p):
                self.error("%s doesn't exist! Skipping..." % p)
        if tmpdir is None:
            tmpdir = os.path.dirname(os.path.abspath(path))
        git = self.query_exe("git", return_type="list")
        for dirname in (".git", ".hg"):
            if os.path.exists(os.path.join(path, dirname)):
                self.move(os.path.join(path, dirname), os.path.join(tmpdir, dirname))
        self.rmtree(path)
        self.mkdir_p(path)
        for dirname in (".git", ".hg"):
            if os.path.exists(os.path.join(tmpdir, dirname)):
                self.move(os.path.join(tmpdir, dirname), os.path.join(path, dirname))
        self.run_command(git + ['--git-dir', os.path.join(path, ".git"), 'config', '--bool', 'core.bare', 'true'])

    # Actions {{{1
    def create_stage_mirror(self):
        self.update_stage_mirror()

    def create_work_mirror(self):
        hg = self.query_exe("hg", return_type="list")
        git = self.query_exe("git", return_type="list")
        dirs = self.query_abs_dirs()
        repo_config = self.config['initial_repo']
        work_dest = dirs['abs_conversion_dir']
        source_dest = os.path.join(dirs['abs_source_dir'], repo_config['repo_name'])
        if not os.path.exists(work_dest):
            self.run_command(hg + ["init", work_dest])
        self.run_command(hg + ["pull", source_dest],
                         cwd=work_dest,
                         error_list=HgErrorList)
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

    def initial_conversion(self):
        hg = self.query_exe("hg", return_type="list")
        dirs = self.query_abs_dirs()
        # TODO more error checking
        repo_config = self.config['initial_repo']
        source = os.path.join(dirs['abs_source_dir'], repo_config['repo_name'])
        dest = dirs['abs_conversion_dir']
        for (branch, target_branch) in repo_config['branches'].items():
            output = self.get_output_from_command(hg + ['id', '-r', branch], cwd=source)
            if output:
                rev = output.split(' ')[0]
            self.run_command(hg + ['pull', '-r', rev, source], cwd=dest,
                             error_list=HgErrorList)
            self.run_command(hg + ['bookmark', '-f', '-r', rev, target_branch], cwd=dest,
                             error_list=HgErrorList)
            self.retry(
                self.run_command,
                args=(hg + ['-v', 'gexport'], ),
                kwargs={
#                    'idle_timeout': 15 * 60,
                    'cwd': dest,
                    'error_list': HgErrorList,
                },
                error_level=FATAL,
            )
            self.copy_to_upload_dir(os.path.join(dest, '.hg', 'git-mapfile'),
                                    dest="pre-cvs-mapfile", log_level=INFO)

    def prepend_cvs(self):
        dirs = self.query_abs_dirs()
        git = self.query_exe('git', return_type='list')
        conversion_dir = dirs['abs_conversion_dir']
        grafts_file = os.path.join(conversion_dir, '.git', 'info', 'grafts')
        if not os.path.exists(dirs["abs_cvs_history_dir"]):
            # gd2 doesn't have access to tooltool :(
            #manifest_path = self.create_tooltool_manifest(self.config['cvs_manifest'])
            #if self.tooltool_fetch(manifest_path, output_dir=dirs['abs_work_dir']):
            #    self.fatal("Unable to download cvs history via tooltool!")
            # Temporary workaround
            self.copyfile("/home/asasaki/mozilla-cvs-history.tar.bz2",
                          os.path.join(dirs['abs_work_dir'], "mozilla-cvs-history.tar.bz2"))
            self.run_command(["tar", "xjvf", "mozilla-cvs-history.tar.bz2"], cwd=dirs["abs_work_dir"],
                             error_list=TarErrorList, halt_on_failure=True)
        # We need to git checkout, or git thinks we've removed all the files
        # without committing
        self.run_command(git + ["checkout"], cwd=conversion_dir)
        self.run_command('ln -s ' + os.path.join(dirs['abs_cvs_history_dir'], 'objects', 'pack', '*') +
                         ' .', cwd=os.path.join(conversion_dir, '.git', 'objects', 'pack'))
        self._check_initial_git_revisions(dirs['abs_cvs_history_dir'], 'e230b03',
                                          '3ec464b55782fb94dbbb9b5784aac141f3e3ac01')
        self._check_initial_git_revisions(conversion_dir, '4b3fd9',
                                          '2514a423aca5d1273a842918589e44038d046a51')
        self.write_to_file(grafts_file,
                           '2514a423aca5d1273a842918589e44038d046a51 3ec464b55782fb94dbbb9b5784aac141f3e3ac01')
        # This script is modified from git-filter-branch from git.
        # https://people.mozilla.com/~hwine/tmp/vcs2vcs/notes.html#initial-conversion
        # We may need to update this script if we update git.
        env = self.query_env()
        git_filter_branch = os.path.join(dirs['abs_repo_sync_tools_dir'], 'git-filter-branch-keep-rewrites')
        self.run_command([git_filter_branch, '--', '3ec464b55782fb94dbbb9b5784aac141f3e3ac01..HEAD'],
                         env=env, cwd=conversion_dir, halt_on_failure=True)
        self.move(os.path.join(conversion_dir, '.git-rewrite'),
                  dirs['abs_git_rewrite_dir'])
        self.rmtree(grafts_file)
        self.munge_mapfile()
        self.make_repo_bare(conversion_dir)

    def create_test_targets(self):
        dirs = self.query_abs_dirs()
        for repo_config in self.query_all_repos():
            for target_config in repo_config['targets']:
                if not target_config.get('test_push'):
                    continue
                target_dest = os.path.join(dirs['abs_target_dir'], target_config['target_dest'])
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
        for repo_config in self.query_all_repos():
            self._update_stage_repo(repo_config)

    def update_work_mirror(self):
        hg = self.query_exe("hg", return_type="list")
        dirs = self.query_abs_dirs()
        dest = dirs['abs_conversion_dir']
        for repo_config in self.query_all_repos():
            source = os.path.join(dirs['abs_source_dir'], repo_config['repo_name'])
            for (branch, target_branch) in repo_config['branches'].items():
                output = self.get_output_from_command(hg + ['id', '-r', branch], cwd=source)
                if output:
                    rev = output.split(' ')[0]
                else:
                    self.fatal("Branch %s doesn't exist in %s!" % (branch, repo_config['repo_name']))
                self.run_command(hg + ['pull', '-r', rev, source], cwd=dest)
                self.run_command(hg + ['bookmark', '-f', '-r', rev, target_branch], cwd=dest)
        self.retry(
            self.run_command,
            args=(hg + ['-v', 'gexport'], ),
            kwargs={
#                'idle_timeout': 15 * 60,
                'cwd': dest,
                'error_list': HgErrorList,
            },
            error_level=FATAL,
        )
        self.copy_to_upload_dir(os.path.join(dest, '.hg', 'git-mapfile'),
                                dest="gecko-mapfile", log_level=INFO)

    def push(self):
        self.create_test_targets()
        dirs = self.query_abs_dirs()
        conversion_dir = dirs['abs_conversion_dir']
        git = self.query_exe('git', return_type='list')
        for repo_config in self.query_all_repos():
            for target_config in repo_config['targets']:
                if target_config.get("vcs", "git") == "git":
                    if target_config.get("test_push"):
                        target_dest = os.path.join(dirs['abs_target_dir'], target_config['target_dest'])
                        if self.retry(
                            self.run_command,
                            args=(git + ['push', target_dest], ),
                            kwargs={
#                                'idle_timeout': 15 * 60,
                                'cwd': os.path.join(conversion_dir, '.git'),
                                'error_list': GitErrorList,
                            },
                        ):
                            self.fatal("Can't push %s to %s!" % conversion_dir, target_dest)
                    else:
                        self.fatal("Don't know how to push live: %s!" % str(target_config))
                else:
                    self.fatal("Don't know how to deal with vcs %s!" % target_config['vcs'])
                    # TODO hg

# __main__ {{{1
if __name__ == '__main__':
    conversion = HgGitScript()
    conversion.run()
