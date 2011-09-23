config = {
    "log_name": "talos",
    "talos_zip": "file:///Users/asasaki/Desktop/talos_ADB.zip",
    "installer_url": "file:///Users/asasaki/Desktop/fennec-8.0a2.multi.android-arm.apk",
    "device_package_name": "org.mozilla.fennec_aurora",
    "virtualenv_path": "/src/talosrunner/venv",
    "device_protocol": "adb",
    "device_port": 5555,
    "device_ip": "10.251.25.95",
    "device_type": "non-tegra",
    "enable_automation": True,
#    "actions": ["check-device"],
    "no_actions": ["preclean", "pull", "download", "unpack"],
    "repos": [{
        "repo": "http://hg.mozilla.org/build/talos",
        "tag": "default",
        "dest": "hg-talos" # this should be talos if no talos_zip
    },{
        "repo": "http://hg.mozilla.org/build/pageloader",
        "tag": "default",
        "dest": "pageloader@mozilla.org"
    },{
        "repo": "http://hg.mozilla.org/users/tglek_mozilla.com/fennecmark",
        "tag": "default",
        "dest": "bench@taras.glek"
    }],
}
