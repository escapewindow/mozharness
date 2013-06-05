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
from mozharness.base.log import ERROR, FATAL
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
        [['--prev-revision', ], {
            "action": "store",
            "dest": "prev_revision",
            "type": "string",
            "help": "Specify which revision to poll from.",
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
    def get_revision_info(self, path, revision):
        """ Get the author + commit message from the revision
            """
        hg = self.query_exe("hg", return_type="list")
        revision_info = {}
        revision_info['author'] = self.retry(
            self.get_output_from_command,
            args=(hg + ["log", "-r", revision, "--template", "{author}"],),
            kwargs={"cwd": path},
            error_level=FATAL,
        )
        revision_info['desc'] = self.retry(
            self.get_output_from_command,
            args=(hg + ["log", "-r", revision, "--template", "{desc}"],),
            kwargs={"cwd": path},
            error_level=FATAL,
        )
        return revision_info

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
        try:
            # Hm, should we use self.read_from_file() then json.loads() here?
            fh = open(path, 'r')
            contents = json.load(fh)
            fh.close()
        except ValueError:
            self.error("%s is invalid json!" % (url, revision))
            contents = {}
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
        dirs = self.query_abs_dirs()
        repo_config = {}
        repo_config["repo"] = orig_repo_config["target_pull_url"]
        repo_config["tag"] = orig_repo_config.get("target_tag", "default")
        repo_config["dest"] = os.path.join(
            dirs['abs_work_dir'], orig_repo_config['repo_name'],
            orig_repo_config['target_repo_name']
        )
        repos = [repo_config]
        super(BumpGaiaJson, self).pull(repos=repos)

    def _do_looped_push(self, repo_config, revision_config):
        dirs = self.query_abs_dirs()
        hg = self.query_exe("hg", return_type="list")
        self._pull_target_repo(repo_config)
        repo_path = os.path.join(
            dirs['abs_work_dir'],
            repo_config['repo_name'],
            repo_config['target_repo_name'],
        )
        # TODO
        revision = 'TODO'
        revision_info = {}
        path = os.path.join(repo_path, self.config['revision_file'])
        status = self._update_json(path, revision, repo_config["repo"])
        if status is not None:
            return status
        command = hg + ["commit", "-u", revision_info['author'],
                        "-m", revision_info['desc']]
        self.run_command(command, cwd=repo_path)
        # TODO need to specify user / ssh key
        command = hg + ["push", "-e",
                        "ssh -oIdentityFile=%s -i %s" % (
                            self.config["ssh_key"], self.config["ssh_user"],
                        ),
                        repo_config["push_repo_url"]]
        status = self.run_command(command, cwd=repo_path,
                                  error_list=HgErrorList)
        if status:
            self.run_command(hg + ["rollback"],
                             cwd=repo_path)
            self.run_command(hg + ["revert", "-a"],
                             cwd=repo_path)
            return -1

    # Actions {{{1
    def push_loop(self):
        """ A bit of a misnomer since we pull and update and commit as well?
            """
        for repo_config in self.config['repo_list']:
            self._pull_target_repo(repo_config)
            # TODO get revision list from json
            revision_list = {}
            for revision_config in revision_list:
#                self.info("%s is revision %s" % (repo_config["repo"], revisionlist))
                if self.retry(
                    self._do_looped_push,
                    args=(repo_config, revision_config),
                ):
                    self.add_summary(
                        "Unable to push to %s" % repo_config['push_repo_url'],
                        level=ERROR,
                    )


# __main__ {{{1
if __name__ == '__main__':
    bump_gaia_json = BumpGaiaJson()
    bump_gaia_json.run()
