# This is a template config file for b2g desktop unittest production.

config = {
    # mozharness options
    "application": "b2g",
    "tooltool_servers": ["http://runtime-binaries.pvt.build.mozilla.org/tooltool/"],

    "exes": {
        'python': '/tools/buildbot/bin/python',
        'virtualenv': ['/tools/buildbot/bin/python', '/tools/misc-python/virtualenv.py'],
        'tooltool.py': "/tools/tooltool.py",
    },

    "find_links": [
        "http://repos/python/packages",
        "http://releng-puppet2.srv.releng.use1.mozilla.com/python/packages/",
        "http://releng-puppet1.srv.releng.use1.mozilla.com/python/packages/",
        "http://releng-puppet2.build.mtv1.mozilla.com/python/packages/",
        "http://releng-puppet2.srv.releng.usw2.mozilla.com/python/packages/",
        "http://releng-puppet1.srv.releng.usw2.mozilla.com/python/packages/",
        "http://releng-puppet2.srv.releng.scl3.mozilla.com/python/packages/",
        "http://releng-puppet2.build.scl1.mozilla.com/python/packages/",
        "http://puppetagain.pub.build.mozilla.org/data/python/packages/",
    ],
    "pip_index": False,

    "buildbot_json_path": "buildprops.json",

    "default_actions": [
        'clobber',
        'read-buildbot-config',
        'download-and-extract',
        'create-virtualenv',
        'install',
        'run-tests',
    ],
    "download_symbols": "ondemand",
    "download_minidump_stackwalk": True,

    # test harness options
    "run_file_names": {
        "mochitest": "runtestsb2g.py",
    },

    "mochitest_options": [
        "--console-level=INFO", "--test-manifest=%(test_manifest)s",
        "--total-chunks=%(total_chunks)s", "--this-chunk=%(this_chunk)s",
        "--profile=%(gaia_profile)s", "--app=%(application)s", "--desktop",
        "--utility-path=%(utility_path)s", "--certificate-path=%(cert_path)s",
    ],
}
