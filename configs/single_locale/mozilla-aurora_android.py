MOZILLA_DIR = "mozilla-aurora"
JAVA_HOME = "/tools/jdk6"
JARSIGNER = "tools/release/signing/mozpass.py"
OBJDIR = "obj-l10n"
EN_US_BINARY_URL = "http://stage.mozilla.org/pub/mozilla.org/mobile/nightly/latest-mozilla-aurora-android/en-US"
# Use central b/c of robocop hackery
#EN_US_BINARY_URL = "http://stage.mozilla.org/pub/mozilla.org/mobile/nightly/latest-mozilla-central-android/en-US"
STAGE_SERVER = "dev-stage01.build.mozilla.org"
STAGE_USER = "ffxbld"
STAGE_SSH_KEY = "~/.ssh/ffxbld_dsa"
AUS_SERVER = "dev-stage01.build.mozilla.org"
AUS_USER = "ffxbld"
AUS_SSH_KEY = "~/.ssh/ffxbld_dsa"
AUS_UPLOAD_BASE_DIR = "/opt/aus2/incoming/2/Fennec/%(branch)s/%(build_target)s/%(buildid)s/%(locale)s"

config = {
    "log_name": "single_locale",
    "objdir": OBJDIR,
    "locales_file": "%s/mobile/android/locales/all-locales" % MOZILLA_DIR,
    "locales_dir": "mobile/android/locales",
    "ignore_locales": ["en-US", "multi"],
    "repos": [{
        "repo": "http://hg.mozilla.org/releases/mozilla-aurora",
        "revision": "default",
# pre-robocop
#        "revision": "5221f1397829",
        "dest": MOZILLA_DIR,
    },{
        "repo": "http://hg.mozilla.org/build/buildbot-configs",
        "revision": "default",
        "dest": "buildbot-configs"
    },{
        "repo": "http://hg.mozilla.org/build/tools",
        "revision": "default",
        "dest": "tools"
    },{
        "repo": "http://hg.mozilla.org/build/compare-locales",
        "revision": "RELEASE_AUTOMATION"
    }],
    "hg_l10n_base": "http://hg.mozilla.org/releases/l10n/mozilla-aurora",
    "hg_l10n_tag": "default",
    "l10n_dir": MOZILLA_DIR,
    "repack_env": {
        "JAVA_HOME": JAVA_HOME,
        "PATH": JAVA_HOME + "/bin:%(PATH)s",
        "MOZ_OBJDIR": OBJDIR,
        "EN_US_BINARY_URL": EN_US_BINARY_URL,
        "JARSIGNER": "%(abs_work_dir)s/" + JARSIGNER,
        "LOCALE_MERGEDIR": "%(abs_merge_dir)s/",
        "UPLOAD_USER": STAGE_USER,
        "UPLOAD_SSH_KEY": STAGE_SSH_KEY,
        "UPLOAD_HOST": STAGE_SERVER,
        "UPLOAD_TO_TEMP": "1",
    },
    "merge_locales": True,
    "make_dirs": ['config'],
    "mozilla_dir": MOZILLA_DIR,
    # TODO change to MOZILLA_DIR/mobile/android/config/mozconfigs/android/l10n-mozconfig when that lands.
    "mozconfig": "buildbot-configs/mozilla2/android/mozilla-aurora/nightly/l10n-mozconfig",
    "jarsigner": JARSIGNER,

    # TODO ideally we could get this info from a central location.
    # However, the agility of these individual config files might trump that.
    # Upload
    "stage_server": STAGE_SERVER,
    "stage_user": STAGE_USER,
    "stage_ssh_key": STAGE_SSH_KEY,

    # AUS
    "build_target": "Android_arm-eabi-gcc3",
    "aus_server": AUS_SERVER,
    "aus_user": AUS_USER,
    "aus_ssh_key": AUS_SSH_KEY,
    "aus_upload_base_dir": AUS_UPLOAD_BASE_DIR,

    # TODO deleteme
    "locales": ['de', 'es-ES'],
    "no_actions": ['clobber',],
}
