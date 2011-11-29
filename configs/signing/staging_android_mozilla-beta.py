#!/usr/bin/env python

import os

LOCALES = ["en-US", "multi"]
VERSION = "9.0b3"
BUILDNUM = 1
PRODUCT = "fennec"
TAG = "FENNEC_9_0b3_RELEASE"

BASE_WORK_DIR = "%s/signing-work/%s-%s" % (os.environ['HOME'], PRODUCT, VERSION)
WORK_DIR = "build%s" % str(BUILDNUM)

config = {
    "locales": LOCALES,
    "log_name": "sign_android",
    "base_work_dir": BASE_WORK_DIR,
    "work_dir": WORK_DIR,
    "tag_override": TAG,
    "user_repo_override": "build",
    "repos": [{
        "repo": "http://hg.mozilla.org/%(user_repo_override)s/tools",
        "dest": "tools",
    },{
        "repo": "http://hg.mozilla.org/%(user_repo_override)s/buildbot-configs",
        "dest": "configs",
    }],
}
