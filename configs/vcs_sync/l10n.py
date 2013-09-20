import os
import socket
hostname = socket.gethostname()

config = {
    "log_name": "l10n",
    "log_max_rotate": 99,
    "job_name": "l10n",
    "env": {
        "PATH": "%(PATH)s:/usr/libexec/git-core",
    },
    "exes": {
        # bug 828140 - shut https warnings up.
        # http://kiln.stackexchange.com/questions/2816/mercurial-certificate-warning-certificate-not-verified-web-cacerts
        "hg": [os.path.join(os.getcwd(), "build", "venv", "bin", "hg"), "--config", "web.cacerts=/etc/pki/tls/certs/ca-bundle.crt"],
    },
    "conversion_type": "b2g-l10n",
    "l10n_config": {
        "gecko_config": {
            'mozilla-release': {
                'locales_file_url': 'http://hg.mozilla.org/releases/mozilla-release/raw-file/default/b2g/locales/all-locales',
                'hg_url': 'http://hg.mozilla.org/releases/l10n/mozilla-release/%(locale)s',
                'git_branch_name': 'mozilla-release',
                'targets': [{
                    "target_dest": "gitmo-gecko-l10n",
                }],
                'tag_config': {
                    'tag_regexes': [
                        '^B2G_',
                    ],
                },
            },
            'mozilla-beta': {
                'locales_file_url': 'http://hg.mozilla.org/releases/mozilla-beta/raw-file/default/b2g/locales/all-locales',
                'hg_url': 'http://hg.mozilla.org/releases/l10n/mozilla-beta/%(locale)s',
                'git_branch_name': 'mozilla-beta',
                'targets': [{
                    "target_dest": "gitmo-gecko-l10n",
                }],
                'tag_config': {
                    'tag_regexes': [
                        '^B2G_',
                    ],
                },
            },
            'mozilla-aurora': {
                'locales_file_url': 'http://hg.mozilla.org/releases/mozilla-aurora/raw-file/default/b2g/locales/all-locales',
                'hg_url': 'http://hg.mozilla.org/releases/l10n/mozilla-aurora/%(locale)s',
                'git_branch_name': 'mozilla-aurora',
                'targets': [{
                    "target_dest": "gitmo-gecko-l10n",
                }],
                'tag_config': {
                    'tag_regexes': [
                        '^B2G_',
                    ],
                },
            },
            'mozilla-central': {
                'locales_file_url': 'http://hg.mozilla.org/mozilla-central/raw-file/default/b2g/locales/all-locales',
                'hg_url': 'http://hg.mozilla.org/l10n-central/%(locale)s',
                'git_branch_name': 'master',
                'targets': [{
                    "target_dest": "gitmo-gecko-l10n",
                }],
                'tag_config': {
                    'tag_regexes': [
                        '^B2G_',
                    ],
                },
            },
        },
        "gaia_config": {
            'v1_2': {
                'locales_file_url': 'https://raw.github.com/mozilla-b2g/gaia/v1.2/locales/languages_dev.json',
                'hg_url': 'https://hg.mozilla.org/releases/gaia-l10n/v1_2/%(locale)s',
                'git_branch_name': 'v1.2',
                'targets': [{
                    "target_dest": "gitmo-gaia-l10n",
                }],
                'tag_config': {
                    'tag_regexes': [
                        '^B2G_',
                    ],
                },
            },
            'v1-train': {
                'locales_file_url': 'https://raw.github.com/mozilla-b2g/gaia/v1-train/locales/languages_dev.json',
                'hg_url': 'https://hg.mozilla.org/releases/gaia-l10n/v1_1/%(locale)s',
                'git_branch_name': 'v1.1',
                'targets': [{
                    "target_dest": "gitmo-gaia-l10n",
                }],
                'tag_config': {
                    'tag_regexes': [
                        '^B2G_',
                    ],
                },
            },
            'v1_0_1': {
                'locales_file_url': 'https://raw.github.com/mozilla-b2g/gaia/v1.0.1/locales/languages_dev.json',
                'hg_url': 'https://hg.mozilla.org/releases/gaia-l10n/v1_0_1/%(locale)s',
                'git_branch_name': 'v1.0.1',
                'targets': [{
                    "target_dest": "gitmo-gaia-l10n",
                }],
                'tag_config': {
                    'tag_regexes': [
                        '^B2G_',
                    ],
                },
            },
            'master': {
                'locales_file_url': 'https://raw.github.com/mozilla-b2g/gaia/master/locales/languages_dev.json',
                'hg_url': 'https://hg.mozilla.org/gaia-l10n/%(locale)s',
                'git_branch_name': 'master',
                'targets': [{
                    "target_dest": "gitmo-gaia-l10n",
                }],
                'tag_config': {
                    'tag_regexes': [
                        '^B2G_',
                    ],
                },
            },
        },
    },

    "remote_targets": {
        "gitmo-gecko-l10n": {
            "repo": 'git+ssh://git.mozilla.org/releases/l10n/%(locale)s/gecko.git',
            "ssh_key": "~/.ssh/blah",
            "vcs": "git",
        },
        "gitmo-gaia-l10n": {
            "repo": 'git+ssh://git.mozilla.org/releases/l10n/%(locale)s/gaia.git',
            "ssh_key": "~/.ssh/blah",
            "vcs": "git",
        },
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
        "remote_host": "github-sync2",
        "remote_path": "/home/asasaki/upload/l10n",
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
