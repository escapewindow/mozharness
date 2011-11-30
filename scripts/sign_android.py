#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is Mozilla.
#
# The Initial Developer of the Original Code is
# the Mozilla Foundation <http://www.mozilla.org/>.
# Portions created by the Initial Developer are Copyright (C) 2011
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   Aki Sasaki <aki@mozilla.com>
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****
"""sign_android.py

"""

import os
import sys

# load modules from parent dir
sys.path.insert(1, os.path.dirname(sys.path[0]))

from copy import deepcopy
import getpass
import subprocess

from mozharness.base.errors import SSHErrorList
from mozharness.base.log import OutputParser, DEBUG, INFO, WARNING, ERROR, \
     CRITICAL, FATAL, IGNORE
from mozharness.base.vcs.vcsbase import MercurialScript
from mozharness.l10n.locales import LocalesMixin

# So far this only references the ftp platform name.
SUPPORTED_PLATFORMS = ["android", "android-xul"]
BASE_JARSIGNER_ERROR_LIST = [{
    "substr": "command not found",
    "level": FATAL,
},{
    "substr": "jarsigner error: java.lang.RuntimeException: keystore load: Keystore was tampered with, or password was incorrect",
    "level": FATAL,
    "explanation": "The store passphrase is probably incorrect!",
},{
    "regex": "jarsigner: key associated with .* not a private key",
    "level": FATAL,
    "explanation": "The key passphrase is probably incorrect!",
},{
    "regex": "jarsigner error: java.lang.RuntimeException: keystore load: .* .No such file or directory",
    "level": FATAL,
    "explanation": "The keystore doesn't exist!",
}]
JARSIGNER_ERROR_LIST = BASE_JARSIGNER_ERROR_LIST + [{
    "substr": "jarsigner: unable to open jar file:",
    "level": FATAL,
    "explanation": "The apk is missing!",
}]
TEST_JARSIGNER_ERROR_LIST = BASE_JARSIGNER_ERROR_LIST + [{
    "substr": "jarsigner: unable to open jar file:",
    "level": IGNORE,
}]

class SignAndroid(LocalesMixin, MercurialScript):
    config_options = [[
     ['--locale',],
     {"action": "extend",
      "dest": "locales",
      "type": "string",
      "help": "Specify the locale(s) to sign"
     }
    ],[
     ['--tag-override',],
     {"action": "store",
      "dest": "tag_override",
      "type": "string",
      "help": "Override the tags set for all repos"
     }
    ],[
     ['--platform',],
     {"action": "extend",
      "dest": "platforms",
      "type": "choice",
      "choices": SUPPORTED_PLATFORMS,
      "help": "Specify the platform(s) to sign"
     }
    ],[
     ['--user-repo-override',],
     {"action": "store",
      "dest": "user_repo_override",
      "type": "string",
      "help": "Override the user repo path for all repos"
     }
    ],[
     ['--key-alias',],
     {"action": "store",
      "dest": "key_alias",
      "type": "choice",
      "choices": ['production', 'nightly'],
      "help": "Specify the key alias"
     }
# TODO unsigned url, signed url, ssh key/user/server/path,
# --version
# --buildnum
# --previous-version
# --previous-buildnum
# --keystore
# previous build signed url, --ignore-locale, locales_file
# aus key/user/server/path
# verify aus url?
    ]]

    def __init__(self, require_config_file=True):
        self.store_passphrase = os.environ.get('android_storepass')
        self.key_passphrase = os.environ.get('android_keypass')
        LocalesMixin.__init__(self)
        MercurialScript.__init__(self,
            config_options=self.config_options,
            all_actions=[
                "passphrase",
                "clobber",
                "pull",
                "download-unsigned-bits",
#                "sign",
#                "verify",
#                "upload-signed-bits"
#                "clobber-unsigned-bits",
#                "download-previous-bits",
#                "create-snippets",
#                "upload-snippets",
            ],
            require_config_file=require_config_file
        )

    def passphrase(self):
        if not self.store_passphrase:
            print "(store passphrase): ",
            self.store_passphrase = getpass.getpass()
        if not self.key_passphrase:
            print "(key passphrase): ",
            self.key_passphrase = getpass.getpass()

    def verify_passphrases(self):
        c = self.config
        jarsigner = self.query_exe("jarsigner")
        self.info("Verifying passphrases...")
        # This needs to run silently!
        # Not sure how best to do this in the long term.
        p = subprocess.Popen([jarsigner, "-keystore", c['keystore'],
                             "-storepass", self.store_passphrase,
                             "-keypass", self.key_passphrase,
                             "NOTAREALAPK", c['key_alias']],
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT)
        parser = OutputParser(config=self.config, log_obj=self.log_obj,
                              error_list=TEST_JARSIGNER_ERROR_LIST)
        loop = True
        while loop:
            if p.poll() is not None:
                """Avoid losing the final lines of the log?"""
                loop = False
            for line in p.stdout:
                parser.add_lines(line)
        if parser.num_errors == 0:
            self.info("Passphrases are good.")
        else:
            self.fatal("Unable to verify passphrases!")

    def postflight_passphrase(self):
        self.verify_passphrases()

    def pull(self):
        c = self.config
        dirs = self.query_abs_dirs()
        repos = []
        replace_dict = {}
        if c.get("user_repo_override"):
            replace_dict['user_repo_override'] = c['user_repo_override']
            # deepcopy() needed because of self.config lock bug :(
            for repo_dict in deepcopy(c['repos']):
                repo_dict['repo'] = repo_dict['repo'] % replace_dict
                repos.append(repo_dict)
            print c['repos']
        else:
            repos = c['repos']
        self.vcs_checkout_repos(repos, parent_dir=dirs['abs_work_dir'],
                                tag_override=c.get('tag_override'))

    def download_unsigned_bits(self):
        c = self.config
        dirs = self.query_abs_dirs()

    def preflight_sign(self):
        if self.store_passphrase is None or self.key_passphrase is None:
            self.passphrase()
            self.verify_passphrases()

if __name__ == '__main__':
    sign_android = SignAndroid()
    sign_android.run()
