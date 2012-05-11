HG_SHARE_BASE_DIR = "/builds/hg-shared"
MOZILLA_DIR = "mozilla-beta"

config = {
    "log_name": "source_release",
    "release_config_file": "buildbot-configs/mozilla/release-fennec-mozilla-beta.py",
    "repos": [{
        "repo": "http://hg.mozilla.org/releases/mozilla-beta",
        "revision": "default",
        "dest": "mozilla-beta",
    },{
        "repo": "http://hg.mozilla.org/build/buildbot-configs",
        "revision": "default",
        "dest": "buildbot-configs"
    }],
    'vcs_share_base': HG_SHARE_BASE_DIR,
    'source_repo_nicks': ['mobile'],
    'source_type': 'bundle',
    'revision_source': 'hgweb',
    'hgweb_server': 'http://hg.mozilla.org',

#    "upload_env": {
#        "UPLOAD_USER": STAGE_USER,
#        "UPLOAD_SSH_KEY": STAGE_SSH_KEY,
#        "UPLOAD_HOST": STAGE_SERVER,
#        "UPLOAD_TO_TEMP": "1",
#        "MOZ_PKG_VERSION": "%(version)s",
#    },
    "base_post_upload_cmd": "post_upload.py -p mobile -n 1 -v %(version)s --release-to-mobile-candidates-dir --nightly-dir=candidates",
    "mozilla_dir": MOZILLA_DIR,
    "mozconfig": "%s/mobile/android/config/mozconfigs/android/release" % MOZILLA_DIR,
}
