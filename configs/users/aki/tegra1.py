config = {
    "log_name": "talos",
    "talos_zip": "http://people.mozilla.org/~asasaki/talos_webserver.zip",
    "browser_url": "http://ftp.mozilla.org/pub/mozilla.org/mobile/nightly/latest-mozilla-aurora-android/fennec-9.0a2.multi.android-arm.apk",
    "device_name": "tegra-029",
    "device_package_name": "org.mozilla.fennec_aurora",
    "devicemanager_debug_level": 5,
    "talos_device_name": "tegra-029",
    "talos_branch": "mobile",
    "graph_server": "graphs-stage.mozilla.org",
    "results_link": "/server/collect.cgi",
    "talos_suites": ["tsvg"],
    "talos_config_file": "remote.config",
    "talos_web_server": "10.251.25.44:8000",
    #"virtualenv_path": "/home/cltbld/aki/venv",
    "device_protocol": "sut",
#    "device_port": "20701",
    "device_ip": "10.250.49.16",
    "device_type": "tegra",
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
