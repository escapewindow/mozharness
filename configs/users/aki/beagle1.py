import os

CVS_MANIFEST = """[{
"size": 1301484692,
"digest": "89df462d8d20f54402caaaa4e3c10aa54902a1d7196cdf86b7790b76e62d302ade3102dc3f7da4145dd832e6938b0472370ce6a321e0b3bcf0ad050937bd0e9a",
"algorithm": "sha512",
"filename": "mozilla-cvs-history.tar.bz2"
}]
"""

config = {
    "log_name": "beagle",
    "log_max_rotate": 10,
    "repos": [{
        "repo": "https://hg.mozilla.org/users/hwine_mozilla.com/repo-sync-tools",
        "vcs": "hg",
    }],
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
            "target_dest": "m-c1/.git",
            "vcs": "git",
            "test_push": True,
        }],
        "bare_checkout": True,
        "vcs": "hg",
        "branches": {
            "default": "master",
        },
    },
    "cvs_manifest": CVS_MANIFEST,
    "tooltool_servers": ["http://runtime-binaries.pvt.build.mozilla.org/tooltool/"],
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
            "branches": {
                "b2g18": "master",
            },
        }, {
            "target_dest": "m-b2g18/.git",
            "vcs": "git",
            "test_push": True,
        }],
        "bare_checkout": True,
        "vcs": "hg",
        "branches": {
            "default": "b2g18",
        },
    }],

    "exes": {
        # bug 828140 - shut https warnings up.
        # http://kiln.stackexchange.com/questions/2816/mercurial-certificate-warning-certificate-not-verified-web-cacerts
        "hg": [os.path.join(os.getcwd(), 'build', 'venv', 'bin', 'hg'), '--config', 'web.cacerts=/etc/pki/tls/certs/ca-bundle.crt'],
        "tooltool.py": [
            os.path.join(os.getcwd(), 'build', 'venv', 'bin', 'python'),
            os.path.join(os.getcwd(), 'mozharness', 'external_tools', 'tooltool.py'),
        ],
    },

    "virtualenv_modules": [
        "http://puppetagain.pub.build.mozilla.org/data/python/packages/hg-git-0.4.0-moz2.tar.gz",
        "mercurial==2.2.1",
    ],
#    "find_links": ["http://puppetagain.pub.build.mozilla.org/data/python/packages/", ],

    ## .ssh/config
    #Host git.m.o
    #    HostName git.mozilla.org
    #    IdentityFile $HOME/.ssh/vcs-sync_rsa
    #    User vcs-sync@mozilla.com
    #Host hg.m.o
    #    HostName hg.mozilla.org
    #    IdentityFile $HOME/.ssh/vcs-sync_rsa
    #    User vcs-sync@mozilla.com
    #Host mirror_writer
    #    # staging server
    #    HostName git1.stage.dmz.scl3.mozilla.com
    #    User gitolite
    #Host *
    #    # avoid disconnects on large pushes
    #    ServerAliveInterval 300
    #
    # _ known_hosts will have to be prepopulated.

    # Disallow sharing.  We may need a better way of doing this.
    "vcs_share_base": None,
    "hg_share_base": None,
}
