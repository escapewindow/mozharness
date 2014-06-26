#!/usr/bin/env python
# lint_ignore=E501
# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****
""" gecko_migration.py

Merge day script for gecko (mozilla-central -> mozilla-aurora,
mozilla-aurora -> mozilla-beta, mozilla-beta -> mozilla-release).

Ported largely from
http://hg.mozilla.org/build/tools/file/084bc4e2fc76/release/beta2release.py
and
http://hg.mozilla.org/build/tools/file/084bc4e2fc76/release/merge_helper.py
"""

import os
import pprint
import sys

sys.path.insert(1, os.path.dirname(os.path.dirname(sys.path[0])))

from mozharness.base.errors import HgErrorList
from mozharness.base.log import INFO, FATAL
from mozharness.base.vcs.vcsbase import MercurialScript
from mozharness.base.vcs.mercurial import MercurialVCS

VALID_MIGRATION_BEHAVIORS = (
    "beta_to_release", "aurora_to_beta", "central_to_aurora"
)


# GeckoMigration {{{1
class GeckoMigration(MercurialScript):
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
        super(GeckoMigration, self).__init__(
            config_options=self.config_options,
            all_actions=[
                'clobber',
                'clean-repos',
                'pull',
                'migrate',
                'commit-changes',
                'push',
            ],
            default_actions=[
                'clean-repos',
                'pull',
                'migrate',
            ],
            require_config_file=require_config_file
        )
        self.run_sanity_check()

# Helper methods {{{1
    def run_sanity_check(self):
        """ Verify the configs look sane before proceeding.
            """
        message = ""
        if self.config['migration_behavior'] not in VALID_MIGRATION_BEHAVIORS:
            message += "%s must be one of %s!\n" % (self.config['migration_behavior'], VALID_MIGRATION_BEHAVIORS)
        if self.config['migration_behavior'] == 'beta_to_release':
            if self.config.get("require_remove_locales") and not self.config.get("remove_locales"):
                message += "You must specify --remove-locales!\n"
        else:
            if self.config.get("require_remove_locales"):
                message += "--remove-locales isn't valid unless you're using beta_to_release migration_behavior!\n"
        if message:
            self.fatal(message)

    def query_abs_dirs(self):
        """ Allow for abs_from_dir and abs_to_dir
            """
        if self.abs_dirs:
            return self.abs_dirs
        dirs = super(GeckoMigration, self).query_abs_dirs()
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

    def query_hg_revision(self, path):
        """ Avoid making 'pull' a required action every run, by being able
            to fall back to figuring out the revision from the cloned repo
            """
        m = MercurialVCS(log_obj=self.log_obj, config=self.config)
        revision = m.get_revision_from_path(path)
        return revision

    def query_from_revision(self):
        """ Shortcut to get the revision for the from repo
            """
        dirs = self.query_abs_dirs()
        return self.query_hg_revision(dirs['abs_from_dir'])

    def query_to_revision(self):
        """ Shortcut to get the revision for the to repo
            """
        dirs = self.query_abs_dirs()
        return self.query_hg_revision(dirs['abs_to_dir'])

    def get_fx_major_version(self, path):
        version_path = os.path.join(path, "browser", "config", "version.txt")
        contents = self.read_from_file(version_path, error_level=FATAL)
        return contents.split(".")[0]

    def hg_tag(self, cwd, tags, user=None, message=None, revision=None,
               force=None, halt_on_failure=True):
        if isinstance(tags, basestring):
            tags = [tags]
        message = "Tagging %s" % cwd
        if revision:
            message = "%s %s" % (message, revision)
        message = "%s with %s" % (message, ', '.join(tags))
        self.info(message)
        cmd = self.query_exe('hg', return_type='list') + ['tag']
        if user:
            cmd.extend(['-u', user])
        if message:
            cmd.extend(['-m', message])
        if revision:
            cmd.extend(['-r', revision])
        if force:
            cmd.append('-f')
        cmd.extend(tags)
        return self.run_command(
            cmd, cwd=cwd, halt_on_failure=halt_on_failure,
            error_list=HgErrorList
        )

    def hg_commit(self, cwd, message, user=None):
        """ Commit changes to hg.
            """
        cmd = self.query_exe('hg', return_type='list') + [
            'commit', '-m', message]
        if user:
            cmd.extend(['-u', user])
        self.run_command(cmd, cwd=cwd, error_list=HgErrorList,
                         halt_on_failure=True)
        return self.query_hg_revision(cwd)

    def hg_merge_via_debugsetparents(self, cwd, old_head, new_head, message,
                                     user=None):
        """ Merge 2 heads avoiding non-fastforward commits
            """
        cmd = self.query_exe('hg', return_type='list') + [
            'debugsetparents', new_head, old_head
        ]
        self.run_command(cmd, cwd=cwd, error_list=HgErrorList,
                         halt_on_failure=True)
        self.hg_commit(cwd, message=message, user=user)

    def replace(self, file_name, from_, to_):
        """ Replace text in a file.
            """
        text = self.read_from_file(file_name, error_level=FATAL)
        new_text = text.replace(from_, to_)
        if text == new_text:
            self.fatal("Cannot replace '%s' to '%s' in '%s'" %
                       (from_, to_, file_name))
        self.write_to_file(file_name, new_text, error_level=FATAL)

    def remove_locales(self, file_name, locales):
        """ Remove locales from shipped-locales (m-r only)
            """
        contents = self.read_from_file(file_name)
        new_contents = ""
        for line in contents.splitlines():
            locale = line.split()[0]
            if locale not in locales:
                new_contents += line
            else:
                self.info("Removed locale: %s", locale)
        self.write_to_file(file_name, new_contents)

    def bump_version(self, cwd, curr_version, next_version, curr_suffix,
                     next_suffix, bump_major=False):
        """ Bump versions (m-c, m-a, m-b).

            At some point we may want to unhardcode these filenames into config
            """
        curr_weave_version = str(int(curr_version) + 2)
        next_weave_version = str(int(curr_weave_version) + 1)
        version_files = ["browser/config/version.txt", "config/milestone.txt",
                         "mobile/android/confvars.sh", "b2g/confvars.sh"]
        for f in version_files:
            self.replace(os.path.join(cwd, f), "%s.0%s" % (curr_version, curr_suffix),
                         "%s.0%s" % (next_version, next_suffix))
        # only applicable for m-c
        if bump_major:
            self.replace(
                os.path.join(cwd, "xpcom/components/Module.h"),
                "static const unsigned int kVersion = %s;" % curr_version,
                "static const unsigned int kVersion = %s;" % next_version
            )
            self.replace(
                os.path.join(cwd, "services/sync/Makefile.in"),
                "weave_version := 1.%s.0" % curr_weave_version,
                "weave_version := 1.%s.0" % next_weave_version
            )

    # Branch-specific workflow helper methods {{{1
    def central_to_aurora(self):
        """ mozilla-central -> mozilla-aurora behavior.

            We could have all of these individually toggled by flags, but
            by separating into workflow methods we can be more precise about
            what happens in each workflow, while allowing for things like
            staging beta user repo migrations.
            """
        # TODO
        pass
        # TODO CLOBBER file

    def aurora_to_beta(self):
        """ mozilla-aurora -> mozilla-beta behavior.

            We could have all of these individually toggled by flags, but
            by separating into workflow methods we can be more precise about
            what happens in each workflow, while allowing for things like
            staging beta user repo migrations.
            """
        dirs = self.query_abs_dirs()
        mb_version = self.get_fx_major_version(dirs['abs_to_dir'])
        self.bump_version(dirs['abs_to_dir'], mb_version, mb_version, "a2", "")
        self.replace(
            os.path.join(dirs['abs_to_dir'], "browser/confvars.sh"),
            "MOZ_BRANDING_DIRECTORY=browser/branding/aurora",
            "MOZ_BRANDING_DIRECTORY=browser/branding/nightly")
        self.replace(
            os.path.join(dirs['abs_to_dir'], "browser/confvars.sh"),
            "ACCEPTED_MAR_CHANNEL_IDS=firefox-mozilla-aurora",
            "ACCEPTED_MAR_CHANNEL_IDS=firefox-mozilla-beta,firefox-mozilla-release")
        self.replace(
            os.path.join(dirs['abs_to_dir'], "browser/confvars.sh"),
            "MAR_CHANNEL_ID=firefox-mozilla-aurora",
            "MAR_CHANNEL_ID=firefox-mozilla-beta")
        for d in self.config['branding_dirs']:
            for f in self.config['branding_files']:
                self.replace(
                    os.path.join(dirs['abs_to_dir'], d, f),
                    "ac_add_options --with-branding=mobile/android/branding/aurora",
                    "ac_add_options --with-branding=mobile/android/branding/beta")
        # TODO mozconfig diffing
        # TODO CLOBBER file

    def beta_to_release(self):
        """ mozilla-beta -> mozilla-release behavior.

            We could have all of these individually toggled by flags, but
            by separating into workflow methods we can be more precise about
            what happens in each workflow, while allowing for things like
            staging beta user repo migrations.
            """
        dirs = self.query_abs_dirs()
        self.replace(
            os.path.join(dirs['abs_to_dir'], "browser/confvars.sh"),
            "ACCEPTED_MAR_CHANNEL_IDS=firefox-mozilla-beta,firefox-mozilla-release",
            "ACCEPTED_MAR_CHANNEL_IDS=firefox-mozilla-release"
        )
        self.replace(
            os.path.join(
                dirs['abs_to_dir'], "browser/confvars.sh"),
            "MAR_CHANNEL_ID=firefox-mozilla-beta",
            "MAR_CHANNEL_ID=firefox-mozilla-release"
        )
        for d in self.config['branding_dirs']:
            for f in self.config['branding_files']:
                self.replace(
                    os.path.join(dirs['abs_to_dir'], d, f),
                    "ac_add_options --with-branding=mobile/android/branding/beta",
                    "ac_add_options --with-branding=mobile/android/branding/official")
        if self.config.get("remove_locales"):
            self.remove_locales(
                os.path.join(dirs['abs_to_dir'], "browser/locales/shipped-locales"),
                self.config['remove_locales']
            )
        # TODO CLOBBER file

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
                self.run_command(
                    hg + ["up", "-C", "-r", repo_config['revision']],
                    cwd=repo_path,
                    error_list=HgErrorList,
                    halt_on_failure=True,
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
        super(GeckoMigration, self).pull(repos=repos)

    def migrate(self):
        """ Perform the migration.
            """
        dirs = self.query_abs_dirs()
        from_fx_major_version = self.get_fx_major_version(dirs['abs_from_dir'])
        to_fx_major_version = self.get_fx_major_version(dirs['abs_to_dir'])
        base_from_rev = self.query_from_revision()
        base_to_rev = self.query_to_revision()
        base_tag = self.config['base_tag'] % {'major_version': from_fx_major_version}
        end_tag = self.config['end_tag'] % {'major_version': to_fx_major_version}
        self.hg_tag(
            dirs['abs_from_dir'], base_tag, user=self.config['hg_user'],
            message="Added %s tag for changeset %s. IGNORE BROKEN CHANGESETS DONTBUILD CLOSED TREE NO BUG a=release" %
                    (base_tag, base_from_rev),
            revision=base_from_rev,
        )
        new_from_rev = self.query_from_revision()
        self.info("New revision %s" % new_from_rev)
        m = MercurialVCS(log_obj=self.log_obj, config=self.config)
        m.pull(dirs['abs_from_dir'], dirs['abs_to_dir'])
        self.hg_merge_via_debugsetparents(
            dirs['abs_to_dir'], old_head=base_to_rev, new_head=new_from_rev,
            user=self.config['hg_user'],
            message="Merge old head via |hg debugsetparents %s %s|. "
            "CLOSED TREE DONTBUILD a=release" % (new_from_rev, base_to_rev)
        )
        self.hg_tag(
            dirs['abs_to_dir'], end_tag, user=self.config['hg_user'],
            message="Added %s tag for changeset %s. IGNORE BROKEN CHANGESETS DONTBUILD CLOSED TREE NO BUG a=release" %
                    (end_tag, base_to_rev),
            revision=base_to_rev,
        )

        # Call beta_to_release etc.
        if not hasattr(self, self.config['migration_behavior']):
            self.fatal("Don't know how to proceed with migration_behavior %s !" % self.config['migration_behavior'])
        getattr(self, self.config['migration_behavior'])()
        self.info("Verify the diff, and apply any manual changes, such as disabling features.")

    def commit_changes(self):
        """ Do the commit.
            """
        hg = self.query_exe("hg", return_type="list")
        dirs = self.query_abs_dirs()
        self.run_command(hg + ["diff"], cwd=dirs['abs_to_dir'])
        self.hg_commit(
            dirs['abs_to_dir'], user=self.config['hg_user'],
            message="Update configs. IGNORE BROKEN CHANGESETS CLOSED TREE NO BUG a=release ba=release"
        )

    def push(self):
        """
            """
        pass


# __main__ {{{1
if __name__ == '__main__':
    gecko_migration = GeckoMigration()
    gecko_migration.run_and_exit()
