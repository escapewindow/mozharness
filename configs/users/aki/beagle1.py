import os
config = {
    "log_name": "beagle",
    "repos": [{
        "repo": "https://hg.mozilla.org/mozilla-central",
        "revision": "default",
        "source_dest": "stage_source/mozilla-central",
        "work_dest": "conversion/mozilla-central",
        "targets": [{
            "target_dest": "target/mozilla-central/.git",
            "vcs": "git",
        }],
        "bare_checkout": True,
        "vcs": "hg",
        "branches": {
            "default": "master",
        },
#    }, {
#        "repo": "https://hg.mozilla.org/releases/mozilla-b2g18",
#        "revision": "default",
#        "source_dest": "stage_source/mozilla-b2g18",
#        "work_dest": "conversion/gecko",
#        "targets": [{
#            "target_dest": "target/mozilla-central/.git",
#            "vcs": "git",
#        }],
#        "bare_checkout": True,
#        "vcs": "hg",
#        "branches": {
#            "default": "b2g18",
#        },
    }],

    "exes": {
        # bug 828140 - shut https warnings up.
        # http://kiln.stackexchange.com/questions/2816/mercurial-certificate-warning-certificate-not-verified-web-cacerts
        "hg": [os.path.join(os.getcwd(), 'build', 'venv', 'bin', 'hg'), '--config', 'web.cacerts=/etc/pki/tls/certs/ca-bundle.crt']
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
