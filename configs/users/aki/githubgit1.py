config = {
    "log_name": "ghmh",
    "repos": [{
        "repo": "https://github.com/escapewindow/mozharness.git",
        "source_dest": "gh-mh-src/.git",
        "work_dest": "gh-mh-wrk/.git",
        "target_dest": "gh-mh-target",
        "bare_checkout": True,
        "branches": {
            # TODO be able to pull branch origin/X and push to branch remote/Y
            "master": "master",
            "vcs_checkout": "vcs_mirror",
        },
        "vcs": "git",
        "workflow_type": "github",
    }],

#    "exes": {
#    },
#
#    # Disallow sharing.  We may need a better way of doing this.
#    "vcs_share_base": None,
#    "hg_share_base": None,
}
