MOZILLA_DIR = "mozilla-aurora"
JAVA_HOME = "/tools/jdk6"
JARSIGNER = "tools/release/signing/mozpass.py"
OBJDIR = "obj-l10n"
EN_US_BINARY_URL = "http://stage.mozilla.org/pub/mozilla.org/mobile/nightly/latest-mozilla-aurora-android"
STAGE_SERVER = "dev-stage01.build.sjc1.mozilla.com"
STAGE_USER = "ffxbld"
STAGE_SSH_KEY = "~/.ssh/ffxbld_dsa"
AUS_SERVER = "dev-stage01.build.sjc1.mozilla.com"
AUS_USER = "ffxbld"
AUS_SSH_KEY = "~/.ssh/ffxbld_dsa"
AUS_UPLOAD_BASE_DIR = "/opt/aus2/incoming/2/Fennec/%(branch)s/%(build_target)s/%(buildid)s/%(locale)s"

config = {
    "log_name": "single_locale",
    "objdir": OBJDIR,
    "locales_file": "%s/mobile/android/locales/all-locales" % MOZILLA_DIR,
    "locales_dir": "mobile/android/locales",
    "ignore_locales": ["en-US"],
    "repos": [{
        "repo": "http://hg.mozilla.org/releases/mozilla-aurora",
        "revision": "default",
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
    },
    # TODO ideally we could get this info from a central location.
    # However, the agility of these individual config files might trump that.
    "upload_env": {
        "UPLOAD_USER": STAGE_USER,
        "UPLOAD_SSH_KEY": STAGE_SSH_KEY,
        "UPLOAD_HOST": STAGE_SERVER,
        "POST_UPLOAD_CMD": "post_upload.py -b mozilla-aurora-android-l10n -p mobile -i %(buildid)s --release-to-latest --release-to-dated",
        "UPLOAD_TO_TEMP": "1",
    },
    "enable_upload": True,
    "enable_updaates": True,
    "merge_locales": True,
    "make_dirs": ['config'],
    "mozilla_dir": MOZILLA_DIR,
    # TODO change to MOZILLA_DIR/mobile/android/config/mozconfigs/android/l10n-mozconfig when that lands.
    "mozconfig": "buildbot-configs/mozilla2/android/mozilla-aurora/nightly/l10n-mozconfig",
    "jarsigner": JARSIGNER,

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
