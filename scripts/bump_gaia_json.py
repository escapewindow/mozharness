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

from mozharness.base.vcs.vcsbase import MercurialScript


# BumpGaiaJson {{{1
class BumpGaiaJson(MercurialScript):
    config_options = []
    revision_dict = {}

    def __init__(self, require_config_file=False):
        super(BumpGaiaJson, self).__init__(
            config_options=self.config_options,
            all_actions=[
                'clobber',
                'pull',
                'push-loop',
            ],
            default_actions=[
                'pull',
                'push-loop',
            ],
            require_config_file=require_config_file,
        )

    # Helper methods {{{1
    def get_repo_paths(self, repo_config):
        """ I found myself re-generating these file paths multiple times,
            so I put the logic in its own method.
            """
        dirs = self.query_abs_dirs()
        repo_name = self.get_filename_from_url(repo_config["repo"])
        parent_dir = repo_config.get("parent_dir", repo_name)
        source_path = os.path.join(dirs['abs_work_dir'], parent_dir, repo_name)
        target_paths = {}
        for target_config in repo_config['target_repos']:
            repo_name = self.get_filename_from_url(target_config['pull_repo_url'])
            dest = os.path.join(dirs['abs_work_dir'], parent_dir, repo_name)
            target_paths[target_config['pull_repo_url']] = dest
        return (source_path, target_paths)

    def _update_json(self, path, revision, url):
        """ Update path with url/revision.

            If the revision hasn't changed, don't do anything.
            If the url changes or the current json is invalid, error but don't fail.
            """
        if not os.path.exists(path):
            self.add_failure("%s doesn't exist; can't update with repo %s revision %s!" % url, revision)
            return -1
        try:
            # Hm, should we use self.read_from_file() then json.loads() here?
            fh = open(path, 'r')
            contents = json.load(fh)
            fh.close()
        except ValueError:
            self.error("%s is invalid json!" % url, revision)
            contents = {}
        if contents.get("repo") != url:
            self.error("Current repo %s differs from %s!" % (str(contents.get("repo")), url))
        if contents.get("revision") == revision:
            self.info("Revision %s is the same.  No action needed.")
            return 1
        contents = {
            "repo": url,
            "revision": revision
        }
        if self.write_to_file(path, json.dumps(contents, indent=4) + "\n") != path:
            self.add_failure("Unable to update %s with new revision %s!" % (path, revision))
            return -2

    def _pull_repos(self, orig_repo_config, targets_only=False):
        repos = []
        repo_config = {}
        repo_paths = self.get_repo_paths(orig_repo_config)
        if not targets_only:
            repo_config["repo"] = orig_repo_config["repo"]
            if "tag" in orig_repo_config:
                repo_config["tag"] = orig_repo_config["tag"]
            repo_config["dest"] = repo_paths[0]
            repos.append(repo_config)
        for target_config in orig_repo_config['target_repos']:
            repo_config = {}
            repo_config["repo"] = target_config["pull_repo_url"]
            repo_config["tag"] = target_config.get("tag", "default")
            repo_config["dest"] = repo_paths[1][repo_config["repo"]]
            repos.append(repo_config)
        status = super(BumpGaiaJson, self).pull(repos=repos)
        if isinstance(status, dict):
            self.revision_dict.update(status)

    # Actions {{{1
    def pull(self):
        """ Prepopulate all the repos before going into the push-loop.
            """
        for repo_config in self.config['repo_list']:
            self._pull_repos(repo_config)

    def push_loop(self):
        """ A bit of a misnomer since we pull and update and commit as well?
            """
        for repo_config in self.config['repo_list']:
            repo_paths = self.get_repo_paths(repo_config)
            self._pull_repos(repo_config)
            rev = self.revision_dict[repo_paths[0]]['revision']
            self.info("%s is revision %s" % (repo_config["repo"], rev))
            for target_config in repo_config['target_repos']:
                path = os.path.join(
                    repo_paths[1][target_config['pull_repo_url']],
                    self.config['revision_file'],
                )
                self._update_json(path, rev, repo_config["repo"])


# __main__ {{{1
if __name__ == '__main__':
    bump_gaia_json = BumpGaiaJson()
    bump_gaia_json.run()
