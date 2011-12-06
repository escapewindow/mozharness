#!/usr/bin/env python

import os

LOCALES = ["en-US", "multi"]
#VERSION = "9.0b3"
#BUILDNUM = 1
TAG = "FENNEC_9_0b3_RELEASE"
AUS_SERVER = "dev-stage01.build.mozilla.org"
FTP_SERVER = "dev-stage01.build.mozilla.org"
FTP_UPLOAD_BASE_DIR = "/pub/mozilla.org/mobile/%(version)s-candidates/build%(buildnum)d"
#DOWNLOAD_BASE_URL = "http://%s%s" % (FTP_SERVER, FTP_UPLOAD_BASE_DIR)
DOWNLOAD_BASE_URL = "http://ftp.mozilla.org/pub/mozilla.org/mobile/candidates/%(version)s-candidates/build%(buildnum)d"
APK_BASE_NAME = "fennec-%(version)s.%(locale)s.android-arm.apk"
# because sign_android-0.8.sh renamed these wrong :(
BUILDID_BASE_URL = DOWNLOAD_BASE_URL + "/%(platform)_info.txt"
OLD_BUILDID_BASE_URL = DOWNLOAD_BASE_URL + "/linux-android_info.txt"
FFXBLD_SSH_KEY = '%s/.ssh/ffxbld_dsa' % os.environ['HOME']
CLTBLD_SSH_KEY = '%s/.ssh/cltbld_dsa' % os.environ['HOME']

RELEASE_UPDATE_URL = "http://download.mozilla.org/?product=fennec-%(version)s-complete&os=%(platform)s&lang=%(locale)s"
BETATEST_UPDATE_URL = "http://stage.mozilla.org/pub/mozilla.org/mobile/candidates/%(version)s-candidates/build%(buildnum)d/%(apk_name)s"
SNIPPET_TEMPLATE = """version=1
type=complete
url=%(url)s
hashFunction=sha512
hashValue=%(sha512_hash)s
size=%(size)d
build=%(buildid)s
appv=%(version)s
extv=%(version)s
"""

KEYSTORE = "%s/.android/android.keystore" % os.environ['HOME']
#BASE_WORK_DIR = "%s/signing-work/fennec-%s" % (os.environ['HOME'], VERSION)
BASE_WORK_DIR = "%s/signing-work/fennec-%s" % (os.getcwd(), VERSION)
WORK_DIR = "build%s" % str(BUILDNUM)

JARSIGNER = "/tools/jdk6/bin/jarsigner"
KEY_ALIAS = "nightly"

config = {
    "log_name": "sign_android",
    "base_work_dir": BASE_WORK_DIR,
    "work_dir": WORK_DIR,

    "locales": LOCALES,
    "locales_file": "buildbot-configs/mozilla/l10n-changesets_mobile-beta.json",
    "release_config_file": "buildbot-configs/mozilla/staging_release-fennec-mozilla-beta.py",

    "platforms": ['android'],
    "update_platforms": ['android'],
    "update_channels": {
        'release': {
            'url': RELEASE_UPDATE_URL,
            'template': SNIPPET_TEMPLATE,
        },
        'betatest': {
            'url': BETATEST_UPDATE_URL,
            'template': SNIPPET_TEMPLATE,
        },
        'releasetest': {
            'url': RELEASE_UPDATE_URL,
            'template': SNIPPET_TEMPLATE,
        },
    },
    "ftp_upload_base_dir": FTP_UPLOAD_BASE_DIR,

    "apk_base_name": APK_BASE_NAME,
    "unsigned_apk_base_name": 'gecko-unsigned-unaligned.apk',
    "download_base_url": DOWNLOAD_BASE_URL,
    "download_unsigned_base_subdir": "unsigned/%(platform)s/%(locale)s",
    "download_signed_base_subdir": "%(platform)s/%(locale)s",
    "buildid_base_url": OLD_BUILDID_BASE_URL,
    "old_buildid_base_url": OLD_BUILDID_BASE_URL,

    "keystore": KEYSTORE,
    "key_alias": KEY_ALIAS,
    "exes": {
        "jarsigner": "/usr/bin/jarsigner",
        "zipalign": "/Users/asasaki/wrk/android-tools/android-sdk-mac_x86/tools/zipalign",
    },
    "signature_verification_script": "tools/release/signing/verify-android-signature.sh",

    "user_repo_override": "build",
    "tag_override": TAG,
    "repos": [{
        "repo": "http://hg.mozilla.org/%(user_repo_override)s/tools",
        "dest": "tools",
    },{
        "repo": "http://hg.mozilla.org/%(user_repo_override)s/buildbot-configs",
        "dest": "buildbot-configs",
    }],
}
