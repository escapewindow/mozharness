#!/usr/bin/env python
# lint_ignore=E501
# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****
""" beta2release.py

Merge mozilla-beta -> mozilla-release.
Hopefully we can refactor this to work with the other gecko merges as well.
"""

import datetime
import os
import pprint
import sys

sys.path.insert(1, os.path.dirname(os.path.dirname(sys.path[0])))

from mozharness.base.errors import HgErrorList
from mozharness.base.log import INFO
from mozharness.base.transfer import TransferMixin
from mozharness.base.vcs.vcsbase import MercurialScript
from mozharness.base.vcs.mercurial import MercurialVCS


# Beta2Release {{{1
class Beta2Release(TransferMixin, MercurialScript):
    config_options = [
        [['--hg-user', ], {
            "action": "store",
            "dest": "hg_user",
            "type": "string",
            "default": "ffxbld <release@mozilla.com>",
            "help": "Specify what user to use to commit to hg.",
        }],
        [['--remove-locale', ], {
            "action": "extend",
            "dest": "remove_locales",
            "type": "string",
            "help": "Comma separated list of locales to remove from the 'to' repo.",
        }],
    ]
    gecko_repos = None

    def __init__(self, require_config_file=True):
        super(Beta2Release, self).__init__(
            config_options=self.config_options,
            all_actions=[
                'clobber',
                'clean-repos',
                'pull',
                'migrate',
                'push',
            ],
            default_actions=[
                'clean-repos',
                'pull',
                'migrate',
                # 'push',
            ],
            require_config_file=require_config_file
        )
        self.run_sanity_check()

# Helper methods {{{1
    def run_sanity_check(self):
        """ Verify the configs look sane before proceeding.
            """
        # TODO flag to require remove_locales
        pass

    def query_abs_dirs(self):
        """ Allow for abs_from_dir and abs_to_dir
            """
        if self.abs_dirs:
            return self.abs_dirs
        dirs = super(Beta2Release, self).query_abs_dirs()
        self.abs_dirs['abs_tools_dir'] = os.path.join(
            dirs['abs_work_dir'], 'tools'
        )
        self.abs_dirs['abs_tools_lib_dir'] = os.path.join(
            dirs['abs_work_dir'], 'tools', 'lib', 'python'
        )
        for k in ('from', 'to'):
            dir_name = self.config.get(
                "%s_repo_dir",
                self.get_filename_from_url(self.config["%s_repo_url" % k])
            )
            self.abs_dirs['abs_%s_dir' % k] = os.path.join(
                dirs['abs_work_dir'], dir_name
            )
        return self.abs_dirs

    def query_gecko_repos(self):
        """ Build a list of repos to clone.
            """
        if self.gecko_repos:
            return self.gecko_repos
        self.info("Building gecko_repos list...")
        dirs = self.query_abs_dirs()
        self.gecko_repos = []
        for k in ('from', 'to'):
            url = self.config["%s_repo_url" % k]
            self.gecko_repos.append({
                "repo": url,
                "revision": self.config.get("%s_repo_revision", "default"),
                "dest": dirs['abs_%s_dir' % k],
                "vcs": "hg",
            })
        self.info(pprint.pformat(self.gecko_repos))
        return self.gecko_repos

    def query_revision(self, path):
        """ Avoid making 'pull' a required action every run, by being able
            to fall back to figuring out the revision from the cloned repo
            """
        m = MercurialVCS(log_obj=self.log_obj)
        revision = m.get_revision_from_path(path)
        return revision

    def query_from_revision(self):
        """ Shortcut to get the revision for the from repo
            """
        dirs = self.query_abs_dirs()
        return self.query_revision(dirs['abs_from_dir'])

    def query_to_revision(self):
        """ Shortcut to get the revision for the to repo
            """
        dirs = self.query_abs_dirs()
        return self.query_revision(dirs['abs_to_dir'])

#def replace(file_name, from_, to_):
#    text = open(file_name).read()
#    new_text = text.replace(from_, to_)
#    if text == new_text:
#        raise RuntimeError(
#            "Cannot replace '%s' to '%s' in '%s'" %
#            (from_, to_, file_name))
#
#    _, tmp_file_path = mkstemp()
#    with open(tmp_file_path, "w") as out:
#        out.write(new_text)
#    shutil.move(tmp_file_path, file_name)

# Actions {{{1
    def clean_repos(self):
        """ We may end up with contaminated local repos at some point, but
            we don't want to have to clobber and reclone from scratch every
            time.

            This is an attempt to clean up the local repos without needing a
            clobber.
            """
        dirs = self.query_abs_dirs()
        hg = self.query_exe("hg", return_type="list")
        hg_repos = self.query_gecko_repos()
        hg_strip_error_list = [{
            'substr': r'''abort: empty revision set''', 'level': INFO,
            'explanation': "Nothing to clean up; we're good!",
        }] + HgErrorList
        for repo_config in hg_repos:
            repo_name = repo_config["dest"]
            repo_path = os.path.join(dirs['abs_work_dir'], repo_name)
            if os.path.exists(repo_path):
                self.retry(
                    self.run_command,
                    args=(hg + ["--config", "extensions.mq=", "strip",
                          "--no-backup", "outgoing()"], ),
                    kwargs={
                        'cwd': repo_path,
                        'error_list': hg_strip_error_list,
                        'return_type': 'num_errors',
                        'success_codes': (0, 255),
                    },
                )

    def pull(self):
        """ Pull tools first, then use hgtool for the gecko repos
            """
        repos = [{
            "repo": self.config["tools_repo_url"],
            "revision": self.config["tools_repo_revision"],
            "dest": "tools",
            "vcs": "hg",
        }] + self.query_gecko_repos()
        super(Beta2Release, self).pull(repos=repos)

    def migrate(self):
        """ Perform the migration.

            I'd like this to be a repo-agnostic method, so we should be able to
            toggle behavior via config flags rather than "is this
            mozilla-aurora" type hardcodes.
            """
        now = datetime.datetime.now()
        date = now.strftime("%Y%m%d")
        dirs = self.query_abs_dirs()
        hg = self.query_exe('hg', return_type='list')
        base_tag = "%sBASE_%s" % (self.config["tag_base_name"], date)
        base_from_rev = self.query_from_revision()
        base_to_rev = self.query_to_revision()
        self.info("Tagging %s beta with %s" % (base_from_rev, base_tag))
        cmd = hg + [
            'tag', '-u', self.config['hg_user'], '-r', base_from_rev, '-m',
            "Added %s tag for changeset %s. DONTBUILD CLOSED TREE a=release" %
            (base_tag, base_from_rev),
            base_tag
        ]
        self.run_command(
            cmd,
            cwd=dirs['abs_from_dir'],
            error_list=HgErrorList,
            halt_on_failure=True,
        )
        new_from_rev = self.query_from_revision()
        self.info("New revision %s" % new_from_rev)
#    pull(from_dir, dest=to_dir)
#    merge_via_debugsetparents(
#        to_dir, old_head=release_rev, new_head=new_beta_rev, user=hg_user,
#        msg="Merge old head via |hg debugsetparents %s %s|. "
#        "CLOSED TREE DONTBUILD a=release" % (new_beta_rev, release_rev))

    def push(self):
        """
            """
        pass

#def remove_locales(file_name, locales):
#    _, tmp_file_path = mkstemp()
#    with open(file_name) as f:
#        lines = f.readlines()
#    with open(tmp_file_path, "w") as out:
#        for line in lines:
#            locale = line.split()[0]
#            if locale not in locales:
#                out.write(line)
#            else:
#                log.warn("Removied locale: %s", locale)
#    shutil.move(tmp_file_path, file_name)
#
#
#def main():
#    parser.add_argument("--hg-user", default="ffxbld <release@mozilla.com>",
#                        help="Mercurial username to be passed to hg -u")
#    parser.add_argument("--remove-locale", dest="remove_locales", action="append",
#                        required=True,
#                        help="Locales to be removed from release shipped-locales")

#    beta_rev = get_revision(from_dir)
#    release_rev = get_revision(to_dir)

#    pull(from_dir, dest=to_dir)
#    merge_via_debugsetparents(
#        to_dir, old_head=release_rev, new_head=new_beta_rev, user=hg_user,
#        msg="Merge old head via |hg debugsetparents %s %s|. "
#        "CLOSED TREE DONTBUILD a=release" % (new_beta_rev, release_rev))
#
#    replace(
#        path.join(to_dir, "browser/confvars.sh"),
#        "ACCEPTED_MAR_CHANNEL_IDS=firefox-mozilla-beta,firefox-mozilla-release",
#        "ACCEPTED_MAR_CHANNEL_IDS=firefox-mozilla-release")
#    replace(path.join(to_dir, "browser/confvars.sh"),
#            "MAR_CHANNEL_ID=firefox-mozilla-beta",
#            "MAR_CHANNEL_ID=firefox-mozilla-release")
#
#    for d in branding_dirs:
#        for f in branding_files:
#            replace(
#                path.join(to_dir, d, f),
#                "ac_add_options --with-branding=mobile/android/branding/beta",
#                "ac_add_options --with-branding=mobile/android/branding/official")
#
#    if args.remove_locales:
#        log.info("Removing locales: %s", args.remove_locales)
#        remove_locales(path.join(to_dir, "browser/locales/shipped-locales"),
#                       args.remove_locales)
#
#    log.warn("Apply any manual changes, such as disabling features.")
#    raw_input("Hit 'return' to display channel, branding, and feature diffs onscreen")
#    run_cmd(["hg", "diff"], cwd=to_dir)
#    raw_input("If the diff looks good hit return to commit those changes")
#    commit(to_dir, user=hg_user,
#           msg="Update configs. CLOSED TREE a=release ba=release")
#    raw_input("Go ahead and push mozilla-release changes.")
#
#if __name__ == "__main__":
#    main()


# __main__ {{{1
if __name__ == '__main__':
    beta2release = Beta2Release()
    beta2release.run_and_exit()
