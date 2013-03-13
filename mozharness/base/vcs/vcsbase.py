#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****
"""Generic VCS support.
"""

from copy import deepcopy
import os
import sys

sys.path.insert(1, os.path.dirname(os.path.dirname(os.path.dirname(sys.path[0]))))

from mozharness.base.errors import VCSException
from mozharness.base.log import FATAL
from mozharness.base.script import BaseScript
from mozharness.base.vcs.mercurial import MercurialVCS
from mozharness.base.vcs.hgtool import HgtoolVCS
from mozharness.base.vcs.gittool import GittoolVCS

# Update this with supported VCS name : VCS object
VCS_DICT = {
    'hg': MercurialVCS,
    'hgtool': HgtoolVCS,
    'gittool': GittoolVCS,
}


# VCSMixin {{{1
class VCSMixin(object):
    """Basic VCS methods that are vcs-agnostic.
    The vcs_class handles all the vcs-specific tasks.
    """
    def query_dest(self, kwargs):
        if 'dest' in kwargs:
            return kwargs['dest']
        dest = os.path.basename(kwargs['repo'])
        # Git fun
        if dest.endswith('.git'):
            dest = dest.replace('.git', '')
        return dest

    def _vcs_checkout_with_update(self, vcs_obj, error_level, **kwargs):
        return self.retry(
            self._get_revision,
            error_level=error_level,
            error_message="Can't checkout %s!" % kwargs['repo'],
            args=(vcs_obj, kwargs['dest']),
        )

    def _vcs_checkout_bare(self, vcs_obj, error_level, **kwargs):
        if os.path.exists(kwargs['dest']):
            command = vcs_obj.pull
            error_message = "Can't pull %s in %s!" % (kwargs['repo'], kwargs['dest'])
        else:
            command = vcs_obj.clone
            error_message = "Can't clone %s to %s!" % (kwargs['repo'], kwargs['dest'])
        return self.retry(
            command,
            args=(kwargs['repo'], kwargs['dest']),
            kwargs={'update_dest': False},
            error_level=error_level,
            error_message=error_message,
            retry_exceptions=(VCSException, ),
        )

    def _get_revision(self, vcs_obj, dest):
        try:
            got_revision = vcs_obj.ensure_repo_and_revision()
            if got_revision:
                return got_revision
        except VCSException:
            self.rmtree(dest)
            raise

    def vcs_checkout(self, vcs=None, error_level=FATAL,
                     bare_checkout=False, **kwargs):
        """ Check out a single repo.
        """
        c = self.config
        if not vcs:
            if c.get('default_vcs'):
                vcs = c['default_vcs']
            else:
                try:
                    vcs = self.default_vcs
                except AttributeError:
                    pass
        vcs_class = VCS_DICT.get(vcs)
        if not vcs_class:
            self.error("Running vcs_checkout with kwargs %s" % str(kwargs))
            raise VCSException("No VCS set!")
        # need a better way to do this.
        if 'dest' not in kwargs:
            kwargs['dest'] = self.query_dest(kwargs)
        if 'vcs_share_base' not in kwargs:
            kwargs['vcs_share_base'] = c.get('%s_share_base' % vcs, c.get('vcs_share_base'))
        vcs_obj = vcs_class(
            log_obj=self.log_obj,
            config=self.config,
            vcs_config=kwargs,
        )
        if bare_checkout:
            return self._vcs_checkout_bare(vcs_obj, error_level, **kwargs)
        else:
            return self._vcs_checkout_with_update(vcs_obj, error_level, **kwargs)

    def vcs_checkout_repos(self, repo_list, parent_dir=None,
                           tag_override=None, **kwargs):
        """Check out a list of repos.
        """
        orig_dir = os.getcwd()
        c = self.config
        if not parent_dir:
            parent_dir = os.path.join(c['base_work_dir'], c['work_dir'])
        self.mkdir_p(parent_dir)
        self.chdir(parent_dir)
        revision_dict = {}
        kwargs_orig = deepcopy(kwargs)
        for repo_dict in repo_list:
            kwargs = deepcopy(kwargs_orig)
            kwargs.update(repo_dict)
            if tag_override:
                kwargs['revision'] = tag_override
            dest = self.query_dest(kwargs)
            revision_dict[dest] = {'repo': kwargs['repo']}
            revision_dict[dest]['revision'] = self.vcs_checkout(**kwargs)
        self.chdir(orig_dir)
        return revision_dict


class VCSScript(VCSMixin, BaseScript):
    def __init__(self, **kwargs):
        super(VCSScript, self).__init__(**kwargs)

    def pull(self, repos=None):
        repos = repos or self.config.get('repos')
        if not repos:
            self.info("Pull has nothing to do!")
            return
        dirs = self.query_abs_dirs()
        return self.vcs_checkout_repos(self.config['repos'],
                                       parent_dir=dirs['abs_work_dir'])


# Specific VCS stubs {{{1
# For ease of use.
# This is here instead of mercurial.py because importing MercurialVCS into
# vcsbase from mercurial, and importing VCSScript into mercurial from
# vcsbase, was giving me issues.
class MercurialScript(VCSScript):
    default_vcs = 'hg'


# VCSConversionMixin {{{1
class VCSConversionMixin(object):
    """ Shared methods for VCS conversions.
        """

    def init_git_repo(self, path, additional_args=None):
        git = self.query_exe("git", return_type="list")
        cmd = git + ['init']
        # generally for --bare
        if additional_args:
            cmd.extend(additional_args)
        cmd.append(path)
        return self.retry(self.run_command, args=(cmd, ), error_level=FATAL, error_message="Can't set up %s!" % path)

    def query_repo_dest(self, repo_config, dest_type):
        dirs = self.query_abs_dirs()
        short_dest_type = dest_type.replace('_dest', '')
        return os.path.join(dirs['abs_work_dir'], repo_config.get(dest_type, short_dest_type))

# __main__ {{{1
if __name__ == '__main__':
    pass
