#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****
"""hg_git.py

hg->git conversions.  Needs to support both the monolithic beagle/gecko.git
type conversions, as well as many-to-many (l10n, build repos, etc.)
"""

from copy import deepcopy
import mmap
import os
import pprint
import re
import smtplib
import sys
import time

try:
    import simplejson as json
    assert json
except ImportError:
    import json

sys.path.insert(1, os.path.dirname(os.path.dirname(sys.path[0])))

import mozharness
external_tools_path = os.path.join(
    os.path.abspath(os.path.dirname(os.path.dirname(mozharness.__file__))),
    'external_tools',
)

from mozharness.base.errors import HgErrorList, GitErrorList
from mozharness.base.log import INFO, ERROR, FATAL
from mozharness.base.python import VirtualenvMixin, virtualenv_config_options
from mozharness.base.transfer import TransferMixin
from mozharness.base.vcs.vcsbase import VCSScript
from mozharness.mozilla.tooltool import TooltoolMixin


# HgGitScript {{{1
class HgGitScript(VirtualenvMixin, TooltoolMixin, TransferMixin, VCSScript):
    """ Beagle-oriented hg->git script (lots of mozilla-central hardcodes;
        assumption that we're going to be importing lots of branches).

        Beagle is a git repo of mozilla-central, with full cvs history,
        and a number of developer-oriented repositories and branches added.

        The partner-oriented gecko.git could also be incorporated into this
        script with some changes.
        """

    mapfile_binary_search = None
    all_repos = None

    def __init__(self, require_config_file=True):
        super(HgGitScript, self).__init__(
            config_options=virtualenv_config_options,
            all_actions=[
                'clobber',
                'create-virtualenv',
                'pull',
                'update-stage-mirror',
                'update-work-mirror',
                'push',
                'upload',
                'notify',
            ],
            # These default actions are the update loop that we run after the
            # initial steps to create the work mirror with all the branches +
            # cvs history have been run.
            default_actions=[
                'create-virtualenv',
                'update-stage-mirror',
                'update-work-mirror',
                'push',
                'upload',
                'notify',
            ],
            require_config_file=require_config_file
        )

    # Helper methods {{{1
    def query_abs_dirs(self):
        """ Define paths.
            """
        if self.abs_dirs:
            return self.abs_dirs
        abs_dirs = super(HgGitScript, self).query_abs_dirs()
        abs_dirs['abs_cvs_history_dir'] = os.path.join(
            abs_dirs['abs_work_dir'], 'mozilla-cvs-history')
        abs_dirs['abs_source_dir'] = os.path.join(
            abs_dirs['abs_work_dir'], 'stage_source')
        abs_dirs['abs_repo_sync_tools_dir'] = os.path.join(
            abs_dirs['abs_work_dir'], 'repo-sync-tools')
        abs_dirs['abs_git_rewrite_dir'] = os.path.join(
            abs_dirs['abs_work_dir'], 'mc-git-rewrite')
        abs_dirs['abs_target_dir'] = os.path.join(abs_dirs['abs_work_dir'],
                                                  'target')
        if 'conversion_dir' in self.config:
            abs_dirs['abs_conversion_dir'] = os.path.join(
                abs_dirs['abs_work_dir'], 'conversion',
                self.config['conversion_dir']
            )
        self.abs_dirs = abs_dirs
        return self.abs_dirs

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

    def write_hggit_hgrc(self, dest):
        # Update .hg/hgrc, if not already updated
        hgrc = os.path.join(dest, '.hg', 'hgrc')
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

    def _query_l10n_repos(self):
        """ Since I didn't want to have to build a huge static list of l10n
            repos, and since it would be nicest to read the list of locales
            from their SSoT files.
            """
        l10n_repos = []
        gecko_dict = deepcopy(self.config['l10n_config'].get('gecko_config', {}))
        for name, gecko_config in gecko_dict.items():
            file_name = self.download_file(gecko_config['locales_file_url'])
            if not os.path.exists(file_name):
                self.error("Can't download locales from %s; skipping!" % gecko_config['locales_file_url'])
                continue
            contents = self.read_from_file(file_name)
            for locale in contents.splitlines():
                replace_dict = {'locale': locale}
                long_name = 'gecko_%s_%s' % (name, locale)
                repo_dict = {
                    'repo': gecko_config['hg_url'] % replace_dict,
                    'revision': 'default',
                    'repo_name': long_name,
                    'conversion_dir': long_name,
                    'targets': [{
                        'target_dest': 'releases-l10n-%s-gecko.git' % (locale),
                        'vcs': 'git',
                        'test_push': True,
                    }],
                    'bare_checkout': True,
                    'vcs': 'hg',
                    'branch_config': {
                        'branches': {
                            'default': gecko_config['git_branch_name'],
                        },
                    },
                    'tag_config': gecko_config.get('tag_config', {}),
                }
                for remote_target in gecko_config.get('targets', []):
                    if not remote_target.get('target_dest') or remote_target['target_dest'] not in self.config['remote_targets']:
                        self.fatal("Can't figure out remote target for %s!" % long_name)
                    target_config = deepcopy(self.config['remote_targets'][remote_target['target_dest']])
                    target_config['repo'] = target_config['repo'] % replace_dict
                    repo_dict['targets'].append(target_config)
                l10n_repos.append(repo_dict)

        gaia_dict = deepcopy(self.config['l10n_config'].get('gaia_config', {}))
        # TODO other than locales and long_name I think these are the same; I
        # need to un-dup code.
        for name, gaia_config in gaia_dict.items():
            contents = self.retry(
                self.load_json_from_url,
                args=(gaia_config['locales_file_url'],)
            )
            if not contents:
                self.error("Can't download locales from %s; skipping!" % gaia_config['locales_file_url'])
                continue
            for locale in dict(contents).keys():
                replace_dict = {'locale': locale}
                long_name = 'gaia_%s_%s' % (name, locale)
                repo_dict = {
                    'repo': gaia_config['hg_url'] % replace_dict,
                    'revision': 'default',
                    'repo_name': long_name,
                    'conversion_dir': long_name,
                    'targets': [{
                        'target_dest': '%s/.git' % long_name,
                        'vcs': 'git',
                        'test_push': True,
                    }],
                    'bare_checkout': True,
                    'vcs': 'hg',
                    'branch_config': {
                        'branches': {
                            'default': gaia_config['git_branch_name'],
                        },
                    },
                    'tag_config': gaia_config.get('tag_config', {}),
                }
                for remote_target in gaia_config.get('targets', []):
                    if not remote_target.get('target_dest') or remote_target['target_dest'] not in self.config['remote_targets']:
                        self.fatal("Can't figure out remote target for %s!" % long_name)
                    target_config = deepcopy(self.config['remote_targets'][remote_target['target_dest']])
                    target_config['repo'] = target_config['repo'] % replace_dict
                    repo_dict['targets'].append(target_config)
                l10n_repos.append(repo_dict)
        self.info("Built l10n_repos...")
        self.info(pprint.pformat(l10n_repos, indent=4))
        return l10n_repos

    def query_all_repos(self):
        """ Very simple method, but we need this concatenated list many times
            throughout the script.
            """
        if self.all_repos:
            return self.all_repos
        if self.config.get('conversion_type') == 'b2g-l10n':
            self.all_repos = self._query_l10n_repos()
        elif self.config.get('initial_repo'):
            self.all_repos = [self.config['initial_repo']] + list(self.config['conversion_repos'])
        else:
            self.all_repos = list(self.config['conversion_repos'])
        return self.all_repos

    def _update_stage_repo(self, repo_config, retry=True, clobber=False):
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
        # commenting out hg verify since it takes ~5min per repo; hopefully
        # exit codes will save us
#        if self.run_command(hg + ["verify"], cwd=source_dest):
#            if retry:
#                return self._update_stage_repo(repo_config, retry=False, clobber=True)
#            else:
#                self.fatal("Can't verify %s!" % source_dest)

    def _do_push_repo(self, base_command, refs_list=None, kwargs=None):
        """ Helper method for _push_repo() since it has to be able to break
            out of the target_repo list loop, and the commands loop borks that.
            """
        commands = []
        if refs_list:
            while len(refs_list) > 10:
                commands.append(base_command + refs_list[0:10])
                refs_list = refs_list[10:]
                commands.append(base_command + refs_list)
        else:
            commands = [base_command]
        if kwargs is None:
            kwargs = {}
        for command in commands:
            # Do the push, with retry!
            if self.retry(
                self.run_command,
                args=(command, ),
                kwargs=kwargs,
            ):
                return -1

    def _push_repo(self, repo_config):
        """ Push a repo to a path ("test_push") or remote server.

            This was meant to be a cross-vcs method, but currently only
            covers git pushes.
            """
        dirs = self.query_abs_dirs()
        conversion_dir = self.query_abs_conversion_dir(repo_config)
        if not conversion_dir:
            self.fatal("No conversion_dir for %s!" % repo_config['repo_name'])
        source_dir = os.path.join(dirs['abs_source_dir'], repo_config['repo_name'])
        git = self.query_exe('git', return_type='list')
        hg = self.query_exe('hg', return_type='list')
        return_status = ''
        for target_config in repo_config['targets']:
            if target_config.get("vcs", "git") == "git":
                base_command = git + ['push']
                env = {}
                if target_config.get("force_push"):
                    base_command.append("-f")
                if target_config.get("test_push"):
                    target_name = os.path.join(
                        dirs['abs_target_dir'], target_config['target_dest'])
                    base_command.append(target_name)
                else:
                    target_name = target_config['target_dest']
                    remote_config = self.config.get('remote_targets', {}).get(target_name)
                    if not remote_config:
                        self.fatal("Can't find %s in remote_targets!" % target_name)
                    base_command.append(remote_config['repo'])
                    # Allow for using a custom git ssh key.
                    env['GIT_SSH_KEY'] = remote_config['ssh_key']
                    env['GIT_SSH'] = os.path.join(external_tools_path, 'git-ssh-wrapper.sh')
                # Allow for pushing a subset of repo branches to the target.
                # If we specify that subset, we can also specify different
                # names for those branches (e.g. b2g18 -> master for a
                # standalone b2g18 repo)
                # We query hg for these because the conversion dir will have
                # branches from multiple hg repos, and the regexes may match
                # too many things.
                refs_list = []
                branch_map = self.query_branches(
                    target_config.get('branch_config', repo_config.get('branch_config', {})),
                    source_dir,
                )
                # If the target_config has a branch_config, the key is the
                # local git branch and the value is the target git branch.
                if target_config.get("branch_config"):
                    for (branch, target_branch) in branch_map.items():
                        refs_list += ['+refs/heads/%s:refs/heads/%s' % (branch, target_branch)]
                # Otherwise the key is the hg branch and the value is the git
                # branch; use the git branch for both local and target git
                # branch names.
                else:
                    for (hg_branch, git_branch) in branch_map.items():
                        refs_list += ['+refs/heads/%s:refs/heads/%s' % (git_branch, git_branch)]
                # Allow for pushing a subset of tags to the target, via name or
                # regex.  Again, query hg for this list because the conversion
                # dir will contain tags from multiple hg repos, and the regexes
                # may match too many things.
                tag_config = target_config.get('tag_config', repo_config.get('tag_config', {}))
                if tag_config.get('tags'):
                    for (tag, target_tag) in tag_config['tags'].items():
                        refs_list += ['+refs/tags/%s:refs/tags/%s' % (tag, target_tag)]
                if tag_config.get('tag_regexes'):
                    regex_list = []
                    for regex in tag_config['tag_regexes']:
                        regex_list.append(re.compile(regex))
                    tag_list = self.get_output_from_command(
                        hg + ['tags'],
                        cwd=source_dir,
                    )
                    for tag_line in tag_list.splitlines():
                        if not tag_line:
                            continue
                        tag_parts = tag_line.split()
                        if not tag_parts:
                            self.warning("Bogus tag_line? %s" % str(tag_line))
                            continue
                        tag_name = tag_parts[0]
                        for regex in regex_list:
                            if regex.search(tag_name) is not None:
                                refs_list += ['+refs/tags/%s:refs/tags/%s' % (tag_name, tag_name)]
                                continue
                error_msg = "%s: Can't push %s to %s!\n" % (repo_config['repo_name'], conversion_dir, target_name)
                if self._do_push_repo(
                    base_command,
                    refs_list=refs_list,
                    kwargs={
                        'output_timeout': target_config.get("output_timeout", 30 * 60),
                        'cwd': os.path.join(conversion_dir, '.git'),
                        'error_list': GitErrorList,
                        'partial_env': env,
                    }
                ):
                    if target_config.get("test_push"):
                        error_msg += "This was a test push that failed; not proceeding any further with %s!\n" % repo_config['repo_name']
                    self.error(error_msg)
                    return_status += error_msg
                    if target_config.get("test_push"):
                        break
            else:
                # TODO write hg
                error_msg = "%s: Don't know how to deal with vcs %s!\n" % (
                    target_config['target_dest'], target_config['vcs'])
                self.error(error_msg)
                return_status += error_msg
        return return_status

    def _query_mapped_revision(self, revision=None, mapfile=None):
        """ Use the virtualenv mapper module to search a mapfile for a
            revision.
            """
        if not callable(self.mapfile_binary_search):
            site_packages_path = self.query_python_site_packages_path()
            sys.path.append(os.path.join(site_packages_path, 'mapper'))
            try:
                from bsearch import mapfile_binary_search
                global log
                log = self.log_obj
                self.mapfile_binary_search = mapfile_binary_search
            except ImportError, e:
                self.fatal("Can't import mapfile_binary_search! %s\nDid you create-virtualenv?" % str(e))
        # I wish mapper did this for me, but ...
        fd = open(mapfile, 'rb')
        m = mmap.mmap(fd.fileno(), 0, mmap.MAP_PRIVATE, mmap.PROT_READ)
        return self.mapfile_binary_search(m, revision)

    def _post_fatal(self, message=None, exit_code=None):
        """ After we call fatal(), run this method before exiting.
            """
        if 'notify' in self.actions:
            self.notify(message=message, fatal=True)
        self.copy_logs_to_upload_dir()

    def _read_repo_update_json(self):
        """ repo_update.json is a file we create with information about each
            repo we're converting: git/hg branch names, git/hg revisions,
            pull datetime/timestamp, and push datetime/timestamp.

            Since we want to be able to incrementally update portions of this
            file as we pull/push each branch, we need to be able to read the
            json into memory, so we can update the dict and re-write the json
            to disk.
            """
        repo_map = {}
        dirs = self.query_abs_dirs()
        path = os.path.join(dirs['abs_upload_dir'], 'repo_update.json')
        if os.path.exists(path):
            fh = open(path, 'r')
            repo_map = json.load(fh)
            fh.close()
        return repo_map

    def query_abs_conversion_dir(self, repo_config):
        dirs = self.query_abs_dirs()
        if repo_config.get('conversion_dir'):
            dest = os.path.join(dirs['abs_work_dir'], 'conversion',
                                repo_config['conversion_dir'])
        else:
            dest = dirs.get('abs_conversion_dir')
        return dest

    def _write_repo_update_json(self, repo_map):
        """ The write portion of _read_repo_update_json().
            """
        dirs = self.query_abs_dirs()
        contents = json.dumps(repo_map, sort_keys=True, indent=4)
        self.write_to_file(
            os.path.join(dirs['abs_upload_dir'], 'repo_update.json'),
            contents,
            create_parent_dir=True
        )

    def query_branches(self, branch_config, repo_path, vcs='hg'):
        """ Given a branch_config of branches and branch_regexes, return
            a dict of existing branch names to target branch names.
            """
        branch_map = {}
        if "branches" in branch_config:
            branch_map = deepcopy(branch_config['branches'])
        if "branch_regexes" in branch_config:
            regex_list = list(branch_config['branch_regexes'])
            full_branch_list = []
            if vcs == 'hg':
                hg = self.query_exe("hg", return_type="list")
                # This assumes we always want closed branches as well.
                # If not we may need more options.
                output = self.get_output_from_command(
                    hg + ['branches', '-a'],
                    cwd=repo_path
                )
                if output:
                    for line in output.splitlines():
                        full_branch_list.append(line.split()[0])
            elif vcs == 'git':
                git = self.query_exe("git", return_type="list")
                output = self.get_output_from_command(
                    git + ['branch', '-l'],
                    cwd=repo_path
                )
                if output:
                    for line in output.splitlines():
                        full_branch_list.append(line.replace('*', '').split()[0])
            for regex in regex_list:
                for branch in full_branch_list:
                    m = re.search(regex, branch)
                    if m:
                        # Don't overwrite branch_map[branch] if it exists
                        branch_map.setdefault(branch, branch)
        return branch_map

    # Actions {{{1
    def create_test_targets(self):
        """ This action creates local directories to do test pushes to.
            """
        dirs = self.query_abs_dirs()
        for repo_config in self.query_all_repos():
            for target_config in repo_config['targets']:
                if not target_config.get('test_push'):
                    continue
                target_dest = os.path.join(dirs['abs_target_dir'], target_config['target_dest'])
                if not os.path.exists(target_dest):
                    self.info("Creating local target repo %s." % target_dest)
                    if target_config.get("vcs", "git") == "git":
                        self.init_git_repo(target_dest, additional_args=['--bare', '--shared=true'])
                    else:
                        self.fatal("Don't know how to deal with vcs %s!" % target_config['vcs'])
                else:
                    self.debug("%s exists; skipping." % target_dest)

    def update_stage_mirror(self):
        """ The stage mirror is a buffer clean clone of repositories.
            The logic behind this is that we get occasional corruption from
            |hg pull|.  It's much less time-consuming to detect this in
            a clean clone, and reclone, than to detect this in a working
            conversion directory, and try to repair or reclone+reconvert.

            We pull the stage mirror into the work mirror, where the conversion
            is done.
            """
        for repo_config in self.query_all_repos():
            self._update_stage_repo(repo_config)

    def update_work_mirror(self):
        """ Pull the latest changes into the work mirror, update the repo_map
            json, and run |hg gexport| to convert those latest changes into
            the git conversion repo.
            """
        hg = self.query_exe("hg", return_type="list")
        dirs = self.query_abs_dirs()
        repo_map = self._read_repo_update_json()
        timestamp = int(time.time())
        datetime = time.strftime('%Y-%m-%d %H:%M %Z')
        repo_map['last_pull_timestamp'] = timestamp
        repo_map['last_pull_datetime'] = datetime
        for repo_config in self.query_all_repos():
            repo_name = repo_config['repo_name']
            source = os.path.join(dirs['abs_source_dir'], repo_name)
            dest = self.query_abs_conversion_dir(repo_config)
            if not dest:
                self.fatal("No conversion_dir for %s!" % repo_name)
            if not os.path.exists(dest):
                self.run_command(hg + ["init", dest], halt_on_failure=True)
                self.write_hggit_hgrc(dest)
            # Build branch map.
            branch_map = self.query_branches(
                repo_config.get('branch_config', {}),
                source,
            )
            for (branch, target_branch) in branch_map.items():
                output = self.get_output_from_command(
                    hg + ['id', '-r', branch],
                    cwd=source
                )
                if output:
                    rev = output.split(' ')[0]
                else:
                    self.fatal("Branch %s doesn't exist in %s!" % (branch, repo_name))
                timestamp = int(time.time())
                datetime = time.strftime('%Y-%m-%d %H:%M %Z')
                self.run_command(hg + ['pull', '-r', rev, source], cwd=dest)
                self.run_command(
                    hg + ['bookmark', '-f', '-r', rev, target_branch],
                    cwd=dest
                )
                # This might get a little large.
                repo_map.setdefault('repos', {}).setdefault(repo_name, {}).setdefault('branches', {})[branch] = {
                    'hg_branch': branch,
                    'hg_revision': rev,
                    'git_branch': target_branch,
                    'pull_timestamp': timestamp,
                    'pull_datetime': datetime,
                }
        self.retry(
            self.run_command,
            args=(hg + ['-v', 'gexport'], ),
            kwargs={
                'output_timeout': 15 * 60,
                'cwd': dest,
                'error_list': HgErrorList,
            },
            error_level=FATAL,
        )
        generated_mapfile = os.path.join(dest, '.hg', 'git-mapfile')
        for repo_config in self.query_all_repos():
            repo_name = repo_config['repo_name']
            source = os.path.join(dirs['abs_source_dir'], repo_name)
            branch_map = self.query_branches(
                repo_config.get('branch_config', {}),
                source,
                vcs='hg',
            )
            for (branch, target_branch) in branch_map.items():
                git_revision = self._query_mapped_revision(
                    revision=rev, mapfile=generated_mapfile)
                repo_map['repos'][repo_name]['branches'][branch]['git_revision'] = git_revision
        self._write_repo_update_json(repo_map)
        self.copy_to_upload_dir(generated_mapfile, dest="gecko-mapfile", log_level=INFO)

    def push(self):
        """ Push to all targets.  test_targets are local directory test repos;
            the rest are remote.  Updates the repo_map json.
            """
        self.create_test_targets()
        repo_map = self._read_repo_update_json()
        failure_msg = ""
        timestamp = int(time.time())
        datetime = time.strftime('%Y-%m-%d %H:%M %Z')
        repo_map['last_push_timestamp'] = timestamp
        repo_map['last_push_datetime'] = datetime
        for repo_config in self.query_all_repos():
            timestamp = int(time.time())
            datetime = time.strftime('%Y-%m-%d %H:%M %Z')
            status = self._push_repo(repo_config)
            if not status:  # good
                repo_name = repo_config['repo_name']
                repo_map.setdefault('repos', {}).setdefault(repo_name, {})['push_timestamp'] = timestamp
                repo_map['repos'][repo_name]['push_datetime'] = datetime
            else:
                failure_msg += status + "\n"
        if not failure_msg:
            repo_map['last_successful_push_timestamp'] = repo_map['last_push_timestamp']
            repo_map['last_successful_push_datetime'] = repo_map['last_push_datetime']
        self._write_repo_update_json(repo_map)
        if failure_msg:
            self.fatal("Unable to push these repos:\n%s" % failure_msg)

    def upload(self):
        """ Upload the upload_dir according to the upload_config.
            """
        failure_msg = ''
        dirs = self.query_abs_dirs()
        for upload_config in self.config.get('upload_config', []):
            if self.retry(
                self.rsync_upload_directory,
                args=(
                    dirs['abs_upload_dir'],
                ),
                kwargs=upload_config,
            ):
                failure_msg += '%s:%s' % (upload_config['remote_host'],
                                          upload_config['remote_path'])
        if failure_msg:
            self.fatal("Unable to upload to this location:\n%s" % failure_msg)

    def notify(self, message=None, fatal=False):
        """ Email people in the notify_config (depending on status and failure_only)
            """
        c = self.config
        dirs = self.query_abs_dirs()
        job_name = c.get('job_name', c.get('conversion_dir', os.getcwd()))
        subject = "[vcs2vcs] Successful conversion for %s <EOM>" % job_name
        text = ''
        error_log = os.path.join(dirs['abs_log_dir'], self.log_obj.log_files[ERROR])
        error_contents = self.read_from_file(error_log)
        if fatal:
            subject = "[vcs2vcs] Failed conversion for %s" % job_name
            text = message + '\n\n'
        elif error_contents:
            text += 'Error log is non-zero!'
        if error_contents:
            text += '\n\n' + error_contents
        for notify_config in c.get('notify_config', []):
            if not fatal and notify_config.get('failure_only'):
                continue
            fromaddr = notify_config.get('from', c['default_notify_from'])
            message = '\r\n'.join((
                "From: %s" % fromaddr,
                "To: %s" % notify_config['to'],
                "CC: %s" % ','.join(notify_config.get('cc', [])),
                "Subject: %s" % subject,
                "",
                text
            ))
            toaddrs = [notify_config['to']] + notify_config.get('cc', [])
            # TODO allow for a different smtp server
            # TODO deal with failures
            server = smtplib.SMTP('localhost')
            self.retry(
                server.sendmail,
                args=(fromaddr, toaddrs, message),
            )
            server.quit()

# __main__ {{{1
if __name__ == '__main__':
    conversion = HgGitScript()
    conversion.run()
