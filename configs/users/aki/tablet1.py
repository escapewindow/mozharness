config = {
    "log_name": "talos",

    # this talos_zip has the --develop webserver patch
    "talos_zip": "http://people.mozilla.org/~asasaki/talos_webserver.zip",

    "browser_url": "http://ftp.mozilla.org/pub/mozilla.org/mobile/nightly/latest-mozilla-aurora-android/fennec-9.0a2.multi.android-arm.apk",
    "device_name": "aki_tablet",
    "device_package_name": "org.mozilla.fennec_aurora",
    "talos_branch": "mobile",

    # set graph_server to "''" to not use a graph_server
#    "graph_server": "graphs-stage.mozilla.org",
    "graph_server": "''",

    "results_link": "/server/collect.cgi",
    "talos_suites": ["tpan"],
    "talos_config_file": "remote.config",

    # this needs to be set to either your_IP:8000, or an existing webserver
    # that serves talos.
    "talos_webserver": "10.251.25.44:8000",

    # Set this to start a webserver automatically
    "start_python_webserver": True,

    # adb or sut
    "device_protocol": "adb",

    # set this for adb-over-ip or sut.
    "device_ip": "10.251.28.128",

    # setting this to tegra250 will add tegra-specific behavior
    "device_type": "non-tegra",

    # enable_automation will run steps that may be undesirable for the
    # average user.
    "enable_automation": True,

#    "actions": ["check-device"],
#    "no_actions": ["preclean", "pull", "download", "unpack"],
    "repos": [{
#        "repo": "http://hg.mozilla.org/build/talos",
#        "tag": "default",
#        "dest": "talos" # this should be talos if no talos_zip
#    },{
        "repo": "http://hg.mozilla.org/build/pageloader",
        "tag": "default",
        "dest": "talos/mobile_profile/extensions/pageloader@mozilla.org"
    },{
        "repo": "http://hg.mozilla.org/users/tglek_mozilla.com/fennecmark",
        "tag": "default",
        "dest": "talos/mobile_profile/extensions/bench@taras.glek"
    }],
}
