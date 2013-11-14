# This is for standalone github mirrors of hg.m.o/build repos.

import os
import socket
hostname = socket.gethostname()

# These all need to be under hg.m.o/build.
# If you need to add a different repo, add it to CONVERSION_REPOS.
BUILD_REPOS = [
    "autoland",
    "buildapi",
    "buildbot-configs",
    "buildbotcustom",
    "cloud-tools",
    "mozharness",
    "opsi-package-sources",
    "partner-repacks",
    "preproduction",
    "puppet-manifests",
    "puppet",
    "rpm-sources",
    "talos",
    "tools",
]

CONVERSION_REPOS = []
for repo in BUILD_REPOS:
    CONVERSION_REPOS.append({
        "repo": "https://hg.mozilla.org/build/%s" % repo,
        "revision": "default",
        "repo_name": repo,
        "conversion_dir": repo,
        "mapfile_name": "%s-mapfile" % repo,
        "targets": [{
            "target_dest": "%(branch)s/.git",
            "vcs": "git",
            "test_push": True,
            "force_push": True,
        }],
        "vcs": "hg",
        "branch_config": {
            "branches": {'*': '*'},
        },
        "tag_config": {
            "tags": {'*': '*'},
        },
    })

config = {
    "log_name": "build-repos",
    "log_max_rotate": 99,
    "job_name": "build-repos",
    "conversion_dir": "build-repos",
    "combined_mapfile": "combined-build-mapfile",
    "env": {
        "PATH": "%(PATH)s:/usr/libexec/git-core",
    },
    "conversion_repos": CONVERSION_REPOS,
    "remote_targets": {},
    "exes": {
        # bug 828140 - shut https warnings up.
        # http://kiln.stackexchange.com/questions/2816/mercurial-certificate-warning-certificate-not-verified-web-cacerts
        "hg": [os.path.join(os.getcwd(), "build", "venv", "bin", "hg"), "--config", "web.cacerts=/etc/pki/tls/certs/ca-bundle.crt"],
        "tooltool.py": [
            os.path.join(os.getcwd(), "build", "venv", "bin", "python"),
            os.path.join(os.getcwd(), "mozharness", "external_tools", "tooltool.py"),
        ],
    },

    "virtualenv_modules": [
        "bottle==0.11.6",
        "dulwich==0.9.0",
        "ordereddict==1.1",
        "hg-git==0.4.0-moz2",
        "mapper==0.1",
        "mercurial==2.6.3",
        "mozfile==0.9",
        "mozinfo==0.5",
        "mozprocess==0.11",
    ],
    "find_links": [
        "http://pypi.pvt.build.mozilla.org/pub",
        "http://pypi.pub.build.mozilla.org/pub",
    ],
    "pip_index": False,

    "rsync_upload_config": [{
        "ssh_key": "~/.ssh/vcs-sync_rsa",
        "ssh_user": "asasaki",
        "remote_host": "people.mozilla.org",
        "remote_path": "/home/asasaki/public_html/vcs2vcs/gecko-projects",
    }],

    "default_notify_from": "vcs2vcs@%s" % hostname,
    "notify_config": [{
        "to": "aki@mozilla.com",
        "failure_only": False,
        "skip_empty_messages": False,
    }, {
        "to": "release+vcs2vcs@mozilla.com",
        "failure_only": True,
        "skip_empty_messages": True,
    }],

    # Disallow sharing.  We may need a better way of doing this.
    "vcs_share_base": None,
    "hg_share_base": None,
}
