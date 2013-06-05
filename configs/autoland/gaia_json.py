#!/usr/bin/env python

import os

config = {
    "ssh_key": os.path.expanduser("~/.ssh/id_rsa"),
    "ssh_user": "asasaki@mozilla.com",
    "hg_user": "Test Pusher <test@pusher.org>",
    "revision_file": "b2g/config/gaia.json",
    "push_wait": 3 * 60,
    "repo_list": [{
        "polling_url": "http://hg.mozilla.org/integration/gaia-central/json-pushes?full=1&tipsonly=1",
        "branch": "default",
        "repo_url": "http://hg.mozilla.org/integration/gaia-central",
        "repo_name": "gaia-central",
        "target_push_url": "ssh://hg.mozilla.org/users/asasaki_mozilla.com/birch",
        "target_pull_url": "http://hg.mozilla.org/users/asasaki_mozilla.com/birch",
        "target_tag": "default",
        "target_repo_name": "birch",
    }],
}
