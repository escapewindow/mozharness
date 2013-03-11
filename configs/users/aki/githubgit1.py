config = {
    "log_name": "ghmh",
    "repos": [{
        "repo": "https://github.com/escapewindow/mozharness.git",
        "source_dest": "gh-mh-src/.git",
        "work_dest": "gh-mh-wrk/.git",
        "target_dest": "gh-mh-target/.git",
        "bare_checkout": True,
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
