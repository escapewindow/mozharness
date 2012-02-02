MOZILLA_DIR = "mozilla-aurora"
config = {
    "log_name": "single_locale",
    "objdir": "obj-l10n",
    "locales_file": "%s/mobile/android/locales/all-locales" % MOZILLA_DIR,
    "locales_dir": "mobile/android/locales",
    "ignore_locales": ["en-US", "multi"],
    "repos": [{
        "repo": "http://hg.mozilla.org/releases/mozilla-aurora",
        "tag": "default",
        "dest": MOZILLA_DIR,
    },{
        "repo": "http://hg.mozilla.org/build/buildbot-configs",
        "tag": "default",
        "dest": "buildbot-configs"
    },{
        "repo": "http://hg.mozilla.org/build/tools",
        "tag": "default",
        "dest": "tools"
    },{
        "repo": "http://hg.mozilla.org/build/compare-locales",
        "tag": "RELEASE_AUTOMATION"
    }],
    "hg_l10n_base": "http://hg.mozilla.org/releases/l10n/mozilla-aurora",
    "hg_l10n_tag": "default",
    "l10n_dir": MOZILLA_DIR,
    "env": {
        "JAVA_HOME": "/tools/jdk",
        "PATH": "%(PATH)s:/tools/jdk/bin"
    },
    "merge_locales": True,
    "mozilla_dir": MOZILLA_DIR,
    "mozconfig": "buildbot-configs/mozilla2/android/mozilla-aurora/nightly/l10n-mozconfig",
    "jarsigner": "tools/release/signing/mozpass.py",

    # TODO deleteme
    "locales": ['de', 'es-ES'],
    "no_actions": ['clobber',],
}
