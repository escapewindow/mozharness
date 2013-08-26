import os
import socket
hostname = socket.gethostname()

CVS_MANIFEST = """[{
"size": 1301484692,
"digest": "89df462d8d20f54402caaaa4e3c10aa54902a1d7196cdf86b7790b76e62d302ade3102dc3f7da4145dd832e6938b0472370ce6a321e0b3bcf0ad050937bd0e9a",
"algorithm": "sha512",
"filename": "mozilla-cvs-history.tar.bz2"
}]
"""

config = {
    "log_name": "beagle",
    "log_max_rotate": 99,
    "repos": [{
        "repo": "https://hg.mozilla.org/users/hwine_mozilla.com/repo-sync-tools",
        "vcs": "hg",
    }],
    "job_name": "beagle",
    "conversion_dir": "beagle",
    "initial_repo": {
        "repo": "https://hg.mozilla.org/mozilla-central",
        "revision": "default",
        "repo_name": "mozilla-central",
        "targets": [{
            "target_dest": "beagle/.git",
            "vcs": "git",
            "test_push": True,
        }, {
            "target_dest": "github-beagle",
            "vcs": "git",
        }, {
            "target_dest": "m-c1/.git",
            "vcs": "git",
            "test_push": True,
            "force_push": True,
        }],
        "bare_checkout": True,
        "vcs": "hg",
        "branch_config": {
            "branches": {
                "default": "master",
            },
        },
    },
    "backup_dir": "/mnt/netapp/github_sync/aki/%s" % hostname,
    "cvs_manifest": CVS_MANIFEST,
    "tooltool_servers": ["http://runtime-binaries.pvt.build.mozilla.org/tooltool/"],
    "cvs_history_tarball": "/home/asasaki/mozilla-cvs-history.tar.bz2",
    "env": {
        "PATH": "%(PATH)s:/usr/libexec/git-core",
    },
    "conversion_repos": [{
        "repo": "https://hg.mozilla.org/releases/mozilla-b2g18",
        "revision": "default",
        "repo_name": "mozilla-b2g18",
        "targets": [{
            "target_dest": "beagle/.git",
            "vcs": "git",
            "test_push": True,
            "tag_config": {
                "tags": {'*': '*'},
            },
        }, {
            "target_dest": "github-beagle",
            "vcs": "git",
            "tag_config": {
                "tag_regexes": [
                    "^B2G_",
                ],
            },
        }, {
            "target_dest": "m-b2g18/.git",
            "vcs": "git",
            "test_push": True,
            "branch_config": {
                "branches": {
                    "b2g18": "master",
                },
            },
        }],
        "bare_checkout": True,
        "vcs": "hg",
        "branch_config": {
            "branches": {
                "default": "b2g18",
            },
        },
        "tag_config": {
            "tag_regexes": [
                "^B2G_",
            ],
        },
    }, {
        "repo": "https://hg.mozilla.org/releases/mozilla-b2g18_v1_1_0_hd",
        "revision": "default",
        "repo_name": "mozilla-b2g18_v1_1_0_hd",
        "targets": [{
            "target_dest": "beagle/.git",
            "vcs": "git",
            "test_push": True,
        }, {
            "target_dest": "github-beagle",
            "vcs": "git",
        }],
        "bare_checkout": True,
        "vcs": "hg",
        "branch_config": {
            "branches": {
                "default": "b2g18_v1_1_0_hd",
            },
        },
        "tag_config": {
            "tag_regexes": [
                "^B2G_",
            ],
        },
    }, {
        "repo": "https://hg.mozilla.org/releases/mozilla-b2g18_v1_0_1",
        "revision": "default",
        "repo_name": "mozilla-b2g18_v1_0_1",
        "targets": [{
            "target_dest": "beagle/.git",
            "vcs": "git",
            "test_push": True,
        }, {
            "target_dest": "github-beagle",
            "vcs": "git",
        }],
        "bare_checkout": True,
        "vcs": "hg",
        "branch_config": {
            "branches": {
                "default": "b2g18_v1_0_1",
            },
        },
        "tag_config": {
            "tag_regexes": [
                "^B2G_",
            ],
        },
    }, {
        "repo": "https://hg.mozilla.org/releases/mozilla-b2g18_v1_0_0",
        "revision": "default",
        "repo_name": "mozilla-b2g18_v1_0_0",
        "targets": [{
            "target_dest": "beagle/.git",
            "vcs": "git",
            "test_push": True,
        }, {
            "target_dest": "github-beagle",
            "vcs": "git",
        }],
        "bare_checkout": True,
        "vcs": "hg",
        "branch_config": {
            "branches": {
                "default": "b2g18_v1_0_0",
            },
        },
        "tag_config": {
            "tag_regexes": [
                "^B2G_",
            ],
        },
    }, {
        "repo": "https://hg.mozilla.org/releases/mozilla-aurora",
        "revision": "default",
        "repo_name": "mozilla-aurora",
        "targets": [{
            "target_dest": "beagle/.git",
            "vcs": "git",
            "test_push": True,
        }, {
            "target_dest": "github-beagle",
            "vcs": "git",
        }],
        "bare_checkout": True,
        "vcs": "hg",
        "branch_config": {
            "branches": {
                "default": "aurora",
            },
        },
        "tag_config": {
            "tag_regexes": [
                "^B2G_",
            ],
        },
    }, {
        "repo": "https://hg.mozilla.org/releases/mozilla-beta",
        "revision": "default",
        "repo_name": "mozilla-beta",
        "targets": [{
            "target_dest": "beagle/.git",
            "vcs": "git",
            "test_push": True,
        }, {
            "target_dest": "github-beagle",
            "vcs": "git",
        }],
        "bare_checkout": True,
        "vcs": "hg",
        "branch_config": {
            "branches": {
                "default": "beta",
            },
            "branch_regexes": [
                "^GECKO[0-9_]*RELBRANCH$",
                "^MOBILE[0-9_]*RELBRANCH$",
            ],
        },
        "tag_config": {
            "tag_regexes": [
                "^(B2G|RELEASE_BASE)_",
                "^(FIREFOX|FENNEC)[0-9_b]*BUILD\d+",
            ],
        },
    }, {
        "repo": "https://hg.mozilla.org/releases/mozilla-release",
        "revision": "default",
        "repo_name": "mozilla-release",
        "targets": [{
            "target_dest": "beagle/.git",
            "vcs": "git",
            "test_push": True,
        }, {
            "target_dest": "github-beagle",
            "vcs": "git",
        }],
        "bare_checkout": True,
        "vcs": "hg",
        "branch_config": {
            "branches": {
                "default": "release",
            },
            "branch_regexes": [
                "^GECKO[0-9_]*RELBRANCH$",
                "^MOBILE[0-9_]*RELBRANCH$",
            ],
        },
        "tag_config": {
            "tag_regexes": [
                "^(B2G|RELEASE_BASE)_",
                "^(FIREFOX|FENNEC)[0-9_b]*BUILD\d+",
            ],
        },
    }, {
        "repo": "https://hg.mozilla.org/releases/mozilla-esr17",
        "revision": "default",
        "repo_name": "mozilla-esr17",
        "targets": [{
            "target_dest": "beagle/.git",
            "vcs": "git",
            "test_push": True,
        }, {
            "target_dest": "github-beagle",
            "vcs": "git",
        }],
        "bare_checkout": True,
        "vcs": "hg",
        "branch_config": {
            "branches": {
                "default": "esr17",
            },
        },
        "tag_config": {
            "tag_regexes": [
#                "^(B2G|FIREFOX|FENNEC|THUNDERBIRD|RELEASE_BASE|CALENDAR|SEAMONKEY)_",
                "^B2G_",
            ],
        },
    }, {
        "repo": "https://hg.mozilla.org/integration/mozilla-inbound",
        "revision": "default",
        "repo_name": "mozilla-inbound",
        "targets": [{
            "target_dest": "beagle/.git",
            "vcs": "git",
            "test_push": True,
        }, {
            "target_dest": "github-beagle",
            "vcs": "git",
        }],
        "bare_checkout": True,
        "vcs": "hg",
        "branch_config": {
            "branches": {
                "default": "inbound",
            },
        },
        "tag_config": {},
    }, {
        "repo": "https://hg.mozilla.org/integration/b2g-inbound",
        "revision": "default",
        "repo_name": "b2g-inbound",
        "targets": [{
            "target_dest": "beagle/.git",
            "vcs": "git",
            "test_push": True,
        }, {
            "target_dest": "github-beagle",
            "vcs": "git",
        }],
        "bare_checkout": True,
        "vcs": "hg",
        "branch_config": {
            "branches": {
                "default": "b2g-inbound",
            },
        },
        "tag_config": {},
    }, {
        "repo": "https://hg.mozilla.org/integration/fx-team",
        "revision": "default",
        "repo_name": "fx-team",
        "targets": [{
            "target_dest": "beagle/.git",
            "vcs": "git",
            "test_push": True,
        }, {
            "target_dest": "github-beagle",
            "vcs": "git",
        }],
        "bare_checkout": True,
        "vcs": "hg",
        "branch_config": {
            "branches": {
                "default": "fx-team",
            },
        },
        "tag_config": {},
    }],
    "remote_targets": {
        "github-beagle": {
            "repo": "git@github.com:escapewindow/test-beagle2.git",
            "ssh_key": "~/.ssh/github1_rsa",
            "vcs": "git",
        },
    },

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
        "http://puppetagain.pub.build.mozilla.org/data/python/packages/",
        "http://releng-puppet2.srv.releng.use1.mozilla.com/python/packages/",
        "http://releng-puppet1.srv.releng.use1.mozilla.com/python/packages/",
        "http://releng-puppet2.build.mtv1.mozilla.com/python/packages/",
        "http://releng-puppet2.srv.releng.usw2.mozilla.com/python/packages/",
        "http://releng-puppet1.srv.releng.usw2.mozilla.com/python/packages/",
        "http://releng-puppet2.srv.releng.scl3.mozilla.com/python/packages/",
        "http://releng-puppet2.build.scl1.mozilla.com/python/packages/",
    ],
    "pip_index": False,

    "upload_config": [{
        "ssh_key": "~/.ssh/id_rsa",
        "ssh_user": "asasaki",
        "remote_host": "github-sync3",
        "remote_path": "/home/asasaki/beagle1/beagle-upload",
    }],

    "default_notify_from": "vcs2vcs@%s" % hostname,
    "notify_config": [{
        "to": "aki@mozilla.com",
        "failure_only": False,
    }],

    # Disallow sharing.  We may need a better way of doing this.
    "vcs_share_base": None,
    "hg_share_base": None,
}
