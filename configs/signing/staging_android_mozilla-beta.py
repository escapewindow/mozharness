#!/usr/bin/env python

import os

LOCALES = ["en-US", "multi"]
VERSION = "9.0b3"
BUILDNUM = 1
TAG = "FENNEC_9_0b3_RELEASE"
AUS_SERVER = "dev-stage01.build.mozilla.org"
FTP_SERVER = "dev-stage01.build.mozilla.org"
FTP_UPLOAD_BASE_DIR = "/pub/mozilla.org/mobile/%(version)s-candidates/build%(buildnum)d"
#DOWNLOAD_BASE_URL = "http://%s%s" % (FTP_SERVER, FTP_UPLOAD_BASE_DIR)
DOWNLOAD_BASE_URL = "http://ftp.mozilla.org/pub/mozilla.org/mobile/candidates/%(version)s-candidates/build%(buildnum)d"
APK_BASE_NAME = "fennec-%(version)s.%(locale)s.android-arm.apk"

#BASE_WORK_DIR = "%s/signing-work/fennec-%s" % (os.environ['HOME'], VERSION)
BASE_WORK_DIR = "%s/signing-work/fennec-%s" % (os.getcwd(), VERSION)
WORK_DIR = "build%s" % str(BUILDNUM)

JARSIGNER = "/tools/jdk6/bin/jarsigner"
STORE_ALIAS = "nightly"

config = {
    "locales": LOCALES,
    "log_name": "sign_android",
    "base_work_dir": BASE_WORK_DIR,
    "work_dir": WORK_DIR,
    "tag_override": TAG,
    "platforms": ['android'],
    "apk_base_name": APK_BASE_NAME,
    "download_base_url": DOWNLOAD_BASE_URL,
    "user_repo_override": "build",
    "repos": [{
        "repo": "http://hg.mozilla.org/%(user_repo_override)s/tools",
        "dest": "tools",
    },{
        "repo": "http://hg.mozilla.org/%(user_repo_override)s/buildbot-configs",
        "dest": "configs",
    }],
}
