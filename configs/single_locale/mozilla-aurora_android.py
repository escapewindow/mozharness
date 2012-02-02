MOZILLA_DIR = "mozilla-aurora"
JAVA_HOME = "/tools/jdk6"
OBJDIR = "obj-l10n"
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
        "JAVA_HOME": JAVA_HOME,
        "PATH": JAVA_HOME + "/bin:%(PATH)s",
        "MOZ_OBJDIR": OBJDIR,
    },
    "merge_locales": True,
    "make_dirs": ['config'],
    "mozilla_dir": MOZILLA_DIR,
    # TODO change to MOZILLA_DIR/mobile/android/config/mozconfigs/android/l10n-mozconfig when that lands.
    "mozconfig": "buildbot-configs/mozilla2/android/mozilla-aurora/nightly/l10n-mozconfig",
    "jarsigner": "tools/release/signing/mozpass.py",

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
