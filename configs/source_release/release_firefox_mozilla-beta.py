HG_SHARE_BASE_DIR = "/builds/hg-shared"
MOZILLA_DIR = "mozilla-beta"

config = {
    "log_name": "source_release",
    "release_config_file": "buildbot-configs/mozilla/release-firefox-mozilla-beta.py",
    "repos": [{
        "repo": "http://hg.mozilla.org/releases/mozilla-beta",
        "dest": "mozilla-beta",
    },{
        "repo": "http://hg.mozilla.org/build/buildbot-configs",
        "dest": "buildbot-configs"
    }],
    'vcs_share_base': HG_SHARE_BASE_DIR,
    'source_repo_nicks': ['mozilla'],
    'source_type': 'text',
    'revision_source': 'hgweb',
    'hgweb_server': 'https://hg.mozilla.org',
    'configure_env': {
        'MOZ_OBJDIR': 'objdir',
        'MOZ_PKG_PRETTYNAMES': '1',
        'MOZ_PKG_APPNAME': 'firefox',
    },

#    "upload_env": {
#        "UPLOAD_USER": STAGE_USER,
#        "UPLOAD_SSH_KEY": STAGE_SSH_KEY,
#        "UPLOAD_HOST": STAGE_SERVER,
#        "UPLOAD_TO_TEMP": "1",
#        "MOZ_PKG_VERSION": "%(version)s",
#    },
    "base_post_upload_cmd": "post_upload.py -p firefox -n 1 -v %(version)s --nightly-dir=candidates",
    "mozilla_dir": MOZILLA_DIR,
}
