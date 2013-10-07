import os
import socket
hostname = socket.gethostname()

# These all need to be under hg.m.o/projects.
# If you need to add a different repo, add it to conversion_repos
# with the same format as beagle or gecko.git conversion_repos.
PROJECT_BRANCHES = [
    # twig projects
    "ash",
    "alder",
    "ash",
    "birch",
    "cedar",
    "cypress",
    "date",
    "elm",
    "fig",
    "gum",
    "holly",
    "jamun",
    "larch",
    "maple",
    "oak",
    "pine",
    # Non-twig projects
    "build-system",
    "graphics",
    "profiling",
    "ux",
]

config = {
    "log_name": "project-branches",
    "log_max_rotate": 99,
    "repos": [{
        "repo": "https://hg.mozilla.org/users/hwine_mozilla.com/repo-sync-tools",
        "vcs": "hg",
    }],
    "job_name": "project-branches",
    "conversion_dir": "project-branches",
    "mapfile_name": "project-branches-mapfile",
    "env": {
        "PATH": "%(PATH)s:/usr/libexec/git-core",
    },
    "conversion_type": "project-branches",
    "project_branches": PROJECT_BRANCHES,
    "project_branch_repo_url": "http://hg.mozilla.org/projects/%(project)s",
    "conversion_repos": [],
    "remote_targets": {
        "github-project-branches": {
            "repo": "git@github.com:escapewindow/test-project-branches.git",
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
        "remote_host": "github-sync4",
        "remote_path": "/home/asasaki/projects/project-branches-upload",
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
