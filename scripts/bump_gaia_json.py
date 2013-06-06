#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****
""" bump_gaia_json.py

    Polls [a] gaia hg repo(s), and updates a [set of] gecko repo(s) with the
    revision information and pushes.

    This is to tie the gaia revision to a visible TBPL gecko revision,
    so sheriffs can blame the appropriate changes.
"""

import os
import sys
try:
    import simplejson as json
    assert json
except ImportError:
    import json

sys.path.insert(1, os.path.dirname(sys.path[0]))

from mozharness.base.errors import HgErrorList
from mozharness.base.log import ERROR
from mozharness.base.vcs.vcsbase import MercurialScript


# BumpGaiaJson {{{1
class BumpGaiaJson(MercurialScript):
    config_options = [
        [['--max-revisions', ], {
            "action": "store",
            "dest": "max_revisions",
            "type": "int",
            "default": 5,
            "help": "Limit the number of revisions to populate to this number.",
        }],
    ]

    def __init__(self, require_config_file=False):
        super(BumpGaiaJson, self).__init__(
            config_options=self.config_options,
            all_actions=[
                'clobber',
                'push-loop',
                'summary',
            ],
            default_actions=[
                'push-loop',
                'summary',
            ],
            require_config_file=require_config_file,
        )

    # Helper methods {{{1
    def get_revision_list(self, repo_config, prev_revision=None):
        revision_list = []
        url = repo_config['polling_url']
        branch = repo_config.get('branch', 'default')
        max_revisions = self.config['max_revisions']
        dirs = self.query_abs_dirs()
        if prev_revision:
            # hgweb json-pushes hardcode
            url += '&fromchange=%s' % prev_revision
        file_name = os.path.join(dirs['abs_work_dir'],
                                 '%s.json' % repo_config['repo_name'])
        # might be nice to have a load-from-url option; til then,
        # download then read
        if self.retry(
            self.download_file,
            args=(url, ),
            kwargs={'file_name': file_name},
            error_level=ERROR,
        ) != file_name:
            return None
        contents = self.read_from_file(file_name)
        revision_dict = json.loads(contents)
        if not revision_dict:
            return []
        # Discard any revisions not on the branch we care about.
        for k, v in sorted(revision_dict.items()):
            if v['changesets'][-1]['branch'] == branch:
                revision_list.append(v)
        # limit the list to max_revisions
        return revision_list[-max_revisions:]

    def build_commit_message(self, revision_config, repo_name):
        revision_list = []
        comments = ''
        for changeset_config in revision_config['changesets']:
            revision_list.append(changeset_config['node'])
            comments += "\n========\n"
            comments += '\nMercurial revision: %s\nAuthor: %s\nDesc: %s\n' % (
                changeset_config['node'],
                changeset_config['author'],
                changeset_config['desc'],
            )
        message = 'Bumping gaia.json for %d %s revision(s)\n' % (
            len(revision_list),
            repo_name
        )
        return message + comments

    def query_repo_path(self, repo_config):
        dirs = self.query_abs_dirs()
        return os.path.join(
            dirs['abs_work_dir'],
            repo_config['repo_name'],
            repo_config['target_repo_name'],
        )

    def _read_json(self, path):
        if not os.path.exists(path):
            self.error("%s doesn't exist!" % path)
            return
        contents = self.read_from_file(path)
        try:
            json_contents = json.loads(contents)
            return json_contents
        except ValueError:
            self.error("%s is invalid json!" % path)

    def _update_json(self, path, revision, url):
        """ Update path with url/revision.

            If the revision hasn't changed, don't do anything.
            If the url changes or the current json is invalid, error but don't fail.
            """
        if not os.path.exists(path):
            self.add_summary(
                "%s doesn't exist; can't update with repo %s revision %s!" % (path, url, revision),
                level=ERROR,
            )
            return -1
        contents = self._read_json(path)
        if contents:
            if contents.get("repo") != url:
                self.error("Current repo %s differs from %s!" % (str(contents.get("repo")), url))
            if contents.get("revision") == revision:
                self.info("Revision %s is the same.  No action needed." % revision)
                self.add_summary("%s is unchanged." % url)
                return 0
        contents = {
            "repo": url,
            "revision": revision
        }
        if self.write_to_file(path, json.dumps(contents, indent=4) + "\n") != path:
            self.add_summary(
                "Unable to update %s with new revision %s!" % (path, revision),
                level=ERROR,
            )
            return -2

    def _pull_target_repo(self, orig_repo_config):
        repo_config = {}
        repo_config["repo"] = orig_repo_config["target_pull_url"]
        repo_config["tag"] = orig_repo_config.get("target_tag", "default")
        repo_path = self.query_repo_path(orig_repo_config)
        repo_config["dest"] = repo_path
        repos = [repo_config]
        super(BumpGaiaJson, self).pull(repos=repos)

    def _do_looped_push(self, repo_config, revision_config):
        hg = self.query_exe("hg", return_type="list")
        self._pull_target_repo(repo_config)
        repo_path = self.query_repo_path(repo_config)
        path = os.path.join(repo_path, self.config['revision_file'])
        revision = revision_config['changesets'][-1]['node']
        status = self._update_json(path, revision, repo_config["repo_url"])
        if status is not None:
            return status
        message = self.build_commit_message(revision_config, repo_config["repo_name"])
        command = hg + ["commit", "-u", self.config['hg_user'],
                        "-m", message]
        self.run_command(command, cwd=repo_path)
        command = hg + ["push", "-e",
                        "ssh -oIdentityFile=%s -l %s" % (
                            self.config["ssh_key"], self.config["ssh_user"],
                        ),
                        repo_config["target_push_url"]]
        status = self.run_command(command, cwd=repo_path,
                                  error_list=HgErrorList)
        if status:
            self.run_command(hg + ["rollback"],
                             cwd=repo_path)
            self.run_command(hg + ["revert", "-a"],
                             cwd=repo_path)
            return -1
        return 0

    # Actions {{{1
    def push_loop(self):
        """ A bit of a misnomer since we pull and update and commit as well?
            """
        for repo_config in self.config['repo_list']:
            self._pull_target_repo(repo_config)
            repo_path = self.query_repo_path(repo_config)
            contents = self._read_json(os.path.join(repo_path, self.config['revision_file']))
            prev_revision = None
            if contents:
                prev_revision = contents.get('revision')
            revision_list = self.get_revision_list(repo_config, prev_revision=prev_revision)
            if not revision_list:
                self.add_summary(
                    "Unable to get revision_list for %s" % repo_config['repo_url'],
                    level=ERROR,
                )
                continue
            for revision_config in revision_list:
                if self.retry(
                    self._do_looped_push,
                    args=(repo_config, revision_config),
                ):
                    # Don't FATAL; we may have another repo to update
                    self.add_summary(
                        "Unable to push to %s; breaking out of revision loop" % repo_config['target_push_url'],
                        level=ERROR,
                    )
                    break


# __main__ {{{1
if __name__ == '__main__':
    bump_gaia_json = BumpGaiaJson()
    bump_gaia_json.run()
