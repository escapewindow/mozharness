#!/usr/bin/env python

config = {
    "ssh_key": "~/.ssh/id_rsa",
    "ssh_user": "asasaki@mozilla.com",
    "hg_user": "Test Pusher <aki@escapewindow.com>",
    "revision_file": "b2g/config/gaia.json",
    "repo_list": [{
        "polling_url": "http://hg.mozilla.org/integration/gaia-central/json-pushes?full=1",
        "branch": "default",
        "repo_url": "http://hg.mozilla.org/integration/gaia-central",
        "repo_name": "gaia-central",
        "target_push_url": "ssh://hg.mozilla.org/users/asasaki_mozilla.com/birch",
        "target_pull_url": "http://hg.mozilla.org/users/asasaki_mozilla.com/birch",
        "target_tag": "default",
        "target_repo_name": "birch",
    }],
}
