FTP_SERVER = "dev-stage01.build.sjc1.mozilla.com"
#FTP_SERVER = "stage.mozilla.org"
FTP_USER = "ffxbld"
FTP_SSH_KEY = "~/.ssh/ffxbld_dsa"
FTP_UPLOAD_BASE_DIR = "/pub/mozilla.org/mobile/candidates/%(version)s-candidates/build%(buildnum)d"
#DOWNLOAD_BASE_URL = "http://%s%s" % (FTP_SERVER, FTP_UPLOAD_BASE_DIR)
DOWNLOAD_BASE_URL = "http://ftp.mozilla.org/pub/mozilla.org/mobile/candidates/%(version)s-candidates/build%(buildnum)d"
APK_BASE_NAME = "fennec-%(version)s.%(locale)s.android-arm.apk"
HG_SHARE_BASE_DIR = "/builds/hg-shared"

config = {
    "log_name": "partner_repack",
    "locales_file": "buildbot-configs/mozilla/l10n-changesets_mobile-release.json",
    "additional_locales": ['en-US'],
    "platforms": ["android"],
    "repos": [{
        "repo": "http://hg.mozilla.org/build/buildbot-configs",
        "revision": "default",
    }],
    'vcs_share_base': HG_SHARE_BASE_DIR,
    "ftp_upload_base_dir": FTP_UPLOAD_BASE_DIR,
    "ftp_ssh_key": FTP_SSH_KEY,
    "ftp_user": FTP_USER,
    "installer_base_names": {
        "android": APK_BASE_NAME,
    },
    "download_unsigned_base_subdir": "unsigned/%(platform)s/%(locale)s",
    "download_base_url": DOWNLOAD_BASE_URL,

    "release_config_file": "buildbot-configs/mozilla/release-fennec-mozilla-release.py",
}
