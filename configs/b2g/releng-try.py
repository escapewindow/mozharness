#!/usr/bin/env python
import os
config = {
    "default_actions": [
        'clobber',
        'checkout-sources',
        'get-blobs',
        'update-source-manifest',
        'build',
        'build-symbols',
        'prep-upload',
        'upload',
    ],
    "upload": {
        "default": {
            "ssh_key": os.path.expanduser("~/.ssh/b2gtry_dsa"),
            "ssh_user": "b2gtry",
            "upload_remote_host": "pvtbuilds2.dmz.scl3.mozilla.com",
            "upload_remote_path": "/pub/mozilla.org/b2g/try-builds/%(user)s-%(rev)s/%(branch)s-%(target)s",
            "filelist_key": "upload_files",
            "upload_dep_target_exclusions": [],
        },
        "public": {
            "ssh_key": os.path.expanduser("~/.ssh/b2gtry_dsa"),
            "ssh_user": "b2gtry",
            "upload_remote_host": "stage.mozilla.org",
            "post_upload_cmd": "post_upload.py --tinderbox-builds-dir %(user)s-%(revision)s -p b2g -i %(buildid)s --revision %(revision)s --who %(user)s --builddir try-%(target)s --release-to-try-builds",
            "filelist_key": "public_upload_files",
        },
    },
    "tooltool_servers": ["http://runtime-binaries.pvt.build.mozilla.org/tooltool/"],
    "gittool_share_base": "/builds/git-shared/git",
    "gittool_base_mirror_urls": [],
    "hgtool_share_base": "/builds/hg-shared",
    "hgtool_base_mirror_urls": ["http://hg-internal.dmz.scl3.mozilla.com"],
    "hgtool_base_bundle_urls": ["http://ftp.mozilla.org/pub/mozilla.org/firefox/bundles"],
    "sendchange_masters": ["buildbot-master81.build.mozilla.org:9301"],
    "exes": {
        "tooltool.py": "/tools/tooltool.py",
        "buildbot": "/tools/buildbot/bin/buildbot",
    },
    "env": {
        "CCACHE_DIR": "/builds/ccache",
        "CCACHE_COMPRESS": "1",
        "CCACHE_UMASK": "002",
        "GAIA_OPTIMIZE": "1",
        "WGET_OPTS": "-c -q",
    },
    "purge_minsize": 20,
    #"clobberer_url": "http://clobberer-stage.pvt.build.mozilla.org/index.php",
    #"clobberer_url": "http://clobberer.pvt.build.mozilla.org/index.php",
    "is_automation": True,
    "force_clobber": True,
    "repo_mirror_dir": "/builds/git-shared/repo",
    "repo_remote_mappings": {
        'https://android.googlesource.com/': 'https://git.mozilla.org/external/aosp',
        'git://codeaurora.org/': 'https://git.mozilla.org/external/caf',
        'https://git.mozilla.org/b2g': 'https://git.mozilla.org/b2g',
        'git://github.com/mozilla-b2g/': 'https://git.mozilla.org/b2g',
        'git://github.com/mozilla/': 'https://git.mozilla.org/b2g',
        'https://git.mozilla.org/releases': 'https://git.mozilla.org/releases',
        'http://android.git.linaro.org/git-ro/': 'https://git.mozilla.org/external/linaro',
        'git://github.com/apitrace/': 'https://git.mozilla.org/external/apitrace',
    },
}
