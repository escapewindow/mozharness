config = {
    "log_name": "de",
    "repos": [{
        "repo": "https://hg.mozilla.org/l10n-central/de",
        "revision": "default",
        "dest": "de",
        "bare_checkout": True,
        "vcs": "hg"
    }],

    "exes": {
        # bug 828140 - shut https warnings up.
        # http://kiln.stackexchange.com/questions/2816/mercurial-certificate-warning-certificate-not-verified-web-cacerts
        "hg": ['hg', '--config', 'web.cacerts=/src/vcs_conversion/dummycert.pem']
    },

    # Disallow sharing.  We may need a better way of doing this.
    "vcs_share_base": None,
    "hg_share_base": None,
}
