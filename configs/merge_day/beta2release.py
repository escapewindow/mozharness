import os
import sys

config = {
    "log_name": "beta2release",

    "branding_dirs": ["mobile/android/config/mozconfigs/android/",
                      "mobile/android/config/mozconfigs/android-armv6/",
                      "mobile/android/config/mozconfigs/android-x86/"],
    "branding_files": ["release", "l10n-release", "l10n-nightly", "nightly"],

    # Disallow sharing, since we want pristine .hg directories.
    # "vcs_share_base": None,
    # "hg_share_base": None,
    "tools_repo_url": "https://hg.mozilla.org/build/tools",
    "tools_repo_revision": "default",
    "from_repo_url": "ssh://hg.mozilla.org/releases/mozilla-beta",
    "to_repo_url": "ssh://hg.mozilla.org/releases/mozilla-release",

    "tag_base_name": "RELEASE_",

    # any hg command line options
    "exes": {
        "hg": [
            "hg", "--config",
            "hostfingerprints.hg.mozilla.org=af:27:b9:34:47:4e:e5:98:01:f6:83:2b:51:c9:aa:d8:df:fb:1a:27",
        ],
        "hgtool.py": [
            sys.executable,
            os.path.join(os.getcwd(), 'build', 'tools', 'buildfarm', 'utils', 'hgtool.py'),
        ],
    }
}
#    parser.add_argument("--hg-user", default="ffxbld <release@mozilla.com>",
#                        help="Mercurial username to be passed to hg -u")
#    parser.add_argument("--remove-locale", dest="remove_locales", action="append",
#                        required=True,
#                        help="Locales to be removed from release shipped-locales")
