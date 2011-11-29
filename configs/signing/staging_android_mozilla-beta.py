#!/usr/bin/env python

import os

LOCALES = ["en-US", "multi"]
VERSION = "9.0b3"
BUILDNUM = 1
PRODUCT = "fennec"
BASE_WORK_DIR = os.getcwd()   # this will be ~/signing-work/PRODUCT-VERSION
WORK_DIR = "build%s" % str(BUILDNUM)

config = {
    "locales": LOCALES,
    "log_name": "sign_android",
    "repos": [{
        "repo": "http://hg.mozilla.org/build/tools",
        "dest": "tools",
    },{
        "repo": "http://hg.mozilla.org/build/buildbot-configs",
        "dest": "configs",
    }],
}
