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

import os
import pprint
import sys

sys.path.insert(1, os.path.dirname(os.path.dirname(sys.path[0])))

from mozharness.base.errors import HgErrorList, VCSException
from mozharness.base.log import INFO
from mozharness.base.transfer import TransferMixin
from mozharness.base.vcs.vcsbase import MercurialScript


# Beta2Release {{{1
class Beta2Release(TransferMixin, MercurialScript):
    config_options = [
#        [['--gecko-repo', ], {
#            "action": "extend",
#            "dest": "gecko_repos",
#            "type": "string",
#            "help": "Specify which gecko repo(s) to tag, along with gaia."
#        }],
#        [['--date-string', ], {
#            "action": "store",
#            "dest": "date_string",
#            "type": "string",
#            "default": time.strftime('%Y%m%d'),
#            "help": "Specify the date string to use in the tag name."
#        }],
    ]
    gecko_repos = None

    def __init__(self, require_config_file=True):
        super(Beta2Release, self).__init__(
            config_options=self.config_options,
            all_actions=[
                'clobber',
                'clean-repos',
                'pull',
                'push-loop',
                'summary',
            ],
            default_actions=[
                'clean-repos',
                'pull',
                'push-loop',
                'summary',
            ],
            require_config_file=require_config_file
        )

# Helper methods {{{1
    def query_gecko_repos(self):
        """ Build a list of repos to clone.
            """
        if self.gecko_repos:
            return self.gecko_repos
        self.info("Building gecko_repos list...")
        self.gecko_repos = [{
            "repo": self.config["tools_repo_url"],
            "revision": self.config["tools_repo_revision"],
            "dest": "tools",
            "vcs": "hg",
        }]
        for k in ('from_repo', 'to_repo'):
            url = self.config["%s_url" % k]
            self.gecko_repos.append({
                "repo": url,
                "revision": self.config.get("%s_revision", "default"),
                "dest": self.config.get("%s_dir", self.get_filename_from_url(url)),
                "vcs": "hgtool",
            })
        self.info(pprint.pformat(self.gecko_repos))
        return self.gecko_repos

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

    def hg_tag(self, repo_name, b2g_branch_config):
        """ Attempt to tag and push gecko.  This assumes the trees are open.

            On failure, throw a VCSException.
            """
        hg = self.query_exe("hg", return_type="list")
        dirs = self.query_abs_dirs()
        hg_dir = os.path.join(dirs["abs_work_dir"], repo_name)
        tag_name = self.query_tag_name(b2g_branch_config)
        short_tag_name = self.query_short_tag_name(b2g_branch_config)
        push_url = self.query_repo_push_url(repo_name)
        cmd = hg + ["tag", tag_name, "-m",
                    "tagging %s for mergeday. r=a=mergeday DONTBUILD" % short_tag_name,
                    ]
        if self.run_command(cmd, cwd=hg_dir, error_list=HgErrorList):
            raise VCSException("Can't tag %s with %s" % (repo_name, tag_name))
        # Debugging! Echo only for now.
        # cmd = hg + ["push", push_url]
        cmd = ["echo"] + hg + ["push", push_url]
        if self.run_command(cmd, cwd=hg_dir, error_list=HgErrorList):
            self.run_command(hg + ["--config", "extensions.mq=",
                                   "strip", "--no-backup", "outgoing()"],
                             cwd=hg_dir)
            self.run_command(hg + ["up", "-C"],
                             cwd=hg_dir)
            self.run_command(hg + ["--config", "extensions.purge=",
                                   "purge", "--all"],
                             cwd=hg_dir)
            raise VCSException("Can't push to %s!" % push_url)

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
        """ Pull action.

            Builds an hg repo list-of-dicts and sends them to
            MercurialScript.pull().  Also pulls the gaia_url.

            We'll potentially run another pull in the push-loop action, but
            this action makes sure we have an up-to-date clone on disk to
            operate on.
            """
        repos = self.query_gecko_repos()
#            b2g_branch_config = self.config['b2g_branches'][repo_name]
#            hg_repos.append(self.query_repo_pull_config(repo_name, b2g_branch_config))
#        self.debug("HG repos: %s" % pprint.pformat(hg_repos))
        super(Beta2Release, self).pull(repos=repos)

    def push_loop(self):
        """ Create the tag and push for each gecko+gaia pair.
            This sometimes requires a pull+rebase, hence the loop.
            """
        for repo_name in self.query_gecko_repos():
            b2g_branch_config = self.config['b2g_branches'][repo_name]
            repo_config = self.query_repo_pull_config(repo_name, b2g_branch_config)
            super(Beta2Release, self).pull(repos=[repo_config])

#aki
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
#    logging.basicConfig(format="%(asctime)s - %(message)s", level=logging.INFO)
#    parser = argparse.ArgumentParser()
#    parser.add_argument("--from-dir", default="mozilla-beta",
#                        help="Working directory of repo to be merged from")
#    parser.add_argument("--from-repo",
#                        default="ssh://hg.mozilla.org/releases/mozilla-beta",
#                        help="Repo to be merged from")
#    parser.add_argument("--to-dir", default="mozilla-release",
#                        help="Working directory of repo to be merged to")
#    parser.add_argument(
#        "--to-repo", default="ssh://hg.mozilla.org/releases/mozilla-release",
#        help="Repo to be merged to")
#    parser.add_argument("--hg-user", default="ffxbld <release@mozilla.com>",
#                        help="Mercurial username to be passed to hg -u")
#    parser.add_argument("--remove-locale", dest="remove_locales", action="append",
#                        required=True,
#                        help="Locales to be removed from release shipped-locales")
#
#    args = parser.parse_args()
#    from_dir = args.from_dir
#    to_dir = args.to_dir
#    from_repo = args.from_repo
#    to_repo = args.to_repo
#    hg_user = args.hg_user
#
#    with retrying(mercurial) as clone:
#        for (d, repo) in ((from_dir, from_repo), (to_dir, to_repo)):
#            clone(repo, d)
#            log.info("Cleaning up %s...", d)
#            strip_outgoing(d)
#            update(d, branch="default")
#    beta_rev = get_revision(from_dir)
#    release_rev = get_revision(to_dir)
#
#    now = datetime.datetime.now()
#    date = now.strftime("%Y%m%d")
#    # TODO: make this tag consistent with other branches
#    release_base_tag = "RELEASE_BASE_" + date
#
#    log.info("Tagging %s beta with %s", beta_rev, release_base_tag)
#    tag(from_dir, tags=[release_base_tag], rev=beta_rev, user=hg_user,
#        msg="Added %s tag for changeset %s. DONTBUILD CLOSED TREE a=release" %
#        (release_base_tag, beta_rev))
#    new_beta_rev = get_revision(from_dir)
#    raw_input("Push mozilla-beta and hit Return")
#
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
