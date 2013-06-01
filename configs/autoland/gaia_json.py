#!/usr/bin/env python

import os

config = {
    "ssh_key": os.path.expanduser("~/.ssh/id_rsa"),
    "ssh_user": "asasaki@mozilla.com",
    "revision_file": "b2g/config/gaia.json",
# Let's not use share base while committing/pushing might cause issues in the
# share dir
#    "vcs_share_base": "/builds/hg-shared",
#    "hgtool_base_mirror_urls": ["http://hg-internal.dmz.scl3.mozilla.com"],
#    "hgtool_base_bundle_urls": ["http://ftp.mozilla.org/pub/mozilla.org/firefox/bundles"],
    "repo_list": [{
        "repo": "http://hg.mozilla.org/integration/gaia-central",
        "tag": "default",
        "parent_dir": "gaia-central",
        "target_repos": [{
            "push_repo_url": "ssh://hg.mozilla.org/users/asasaki_mozilla.com/birch",
            "pull_repo_url": "http://hg.mozilla.org/users/asasaki_mozilla.com/birch",
            "tag": "default",
        }],
    }],
}
