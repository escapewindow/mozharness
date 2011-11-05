config = {
    "log_name": "talos",

    # this talos_zip has the --develop webserver patch
    "talos_zip": "http://people.mozilla.org/~asasaki/talos_webserver.zip",

    "browser_url": "http://ftp.mozilla.org/pub/mozilla.org/mobile/nightly/latest-mozilla-aurora-android/fennec-9.0a2.multi.android-arm.apk",
    "device_name": "tegra-029",
    "device_package_name": "org.mozilla.fennec_aurora",
    "talos_device_name": "tegra-029",
    "talos_branch": "mobile",

    # set graph_server to a real graph server if you want to publish your
    # results (the device needs to be in the database already or you'll
    # get errors)
    "graph_server": "graphs-stage.mozilla.org",

    "results_link": "/server/collect.cgi",
    "talos_suites": ["tpan"],
    "talos_config_file": "remote.config",

    # this needs to be set to either your_IP:8000, or an existing webserver
    # that serves talos.
#    "talos_webserver": "10.251.25.44:8000",
    "talos_webserver": "bm-remote.build.mozilla.org",

    # adb or sut
    "device_protocol": "sut",

    # set this to >0 if you want devicemanager output.
    # beware, this will send binary characters to your terminal
#    "devicemanager_debug_level": 2,

    # set this for adb-over-ip or sut.
    "device_ip": "10.250.49.16",

    # setting this to tegra250 will add tegra-specific behavior
    "device_type": "tegra250",

    # enable_automation will run steps that may be undesirable for the
    # average user.
    "enable_automation": True,

#    "actions": ["check-device"],
#    "no_actions": ["preclean", "pull", "download", "unpack"],
    "repos": [{
#        "repo": "http://hg.mozilla.org/build/talos",
#        "tag": "default",
#        "dest": "talos", # this should be talos if no talos_zip
#    },{
        "repo": "http://hg.mozilla.org/build/pageloader",
        "tag": "default",
        "dest": "talos/mobile_profile/extensions/pageloader@mozilla.org",
    },{
        "repo": "http://hg.mozilla.org/users/tglek_mozilla.com/fennecmark",
        "tag": "default",
        "dest": "talos/mobile_profile/extensions/bench@taras.glek",
    }],
}
