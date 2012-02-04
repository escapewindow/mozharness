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
"""mobile_l10n.py

This currently supports nightly and release single locale repacks for
Android.  This also creates nightly updates.
"""

import os
import re
import sys

# load modules from parent dir
sys.path.insert(1, os.path.dirname(sys.path[0]))

from copy import deepcopy
import re
import subprocess

from mozharness.base.config import parse_config_file
from mozharness.base.errors import BaseErrorList, MakefileErrorList, SSHErrorList
from mozharness.base.log import OutputParser, DEBUG, INFO, WARNING, ERROR, \
     CRITICAL, FATAL, IGNORE
from mozharness.mozilla.signing import MobileSigningMixin
from mozharness.base.vcs.vcsbase import MercurialScript
from mozharness.mozilla.l10n.locales import LocalesMixin



# MobileSingleLocale {{{1
class MobileSingleLocale(LocalesMixin, MobileSigningMixin, MercurialScript):
    config_options = [[
     ['--locale',],
     {"action": "extend",
      "dest": "locales",
      "type": "string",
      "help": "Specify the locale(s) to sign and update"
     }
    ],[
     ['--locales-file',],
     {"action": "store",
      "dest": "locales_file",
      "type": "string",
      "help": "Specify a file to determine which locales to sign and update"
     }
    ],[
     ['--tag-override',],
     {"action": "store",
      "dest": "tag_override",
      "type": "string",
      "help": "Override the tags set for all repos"
     }
    ],[
     ['--user-repo-override',],
     {"action": "store",
      "dest": "user_repo_override",
      "type": "string",
      "help": "Override the user repo path for all repos"
     }
    ],[
     ['--release-config-file',],
     {"action": "store",
      "dest": "release_config_file",
      "type": "string",
      "help": "Specify the release config file to use"
     }
    ],[
     ['--keystore',],
     {"action": "store",
      "dest": "keystore",
      "type": "string",
      "help": "Specify the location of the signing keystore"
     }
    ]]

    def __init__(self, require_config_file=True):
        LocalesMixin.__init__(self)
        MobileSigningMixin.__init__(self)
        MercurialScript.__init__(self,
            config_options=self.config_options,
            all_actions=[
                "clobber",
                "pull",
                "setup",
                "repack",
                "upload-repacks",
                "create-nightly-snippets",
            ],
            require_config_file=require_config_file
        )
        self.base_package_name = None
        self.buildid = None
        self.make_ident_output = None
        self.repack_env = None
        self.revision = None
        self.upload_env = None
        self.version = None

    # Helper methods {{{2
    def query_repack_env(self):
        if self.repack_env:
            return self.repack_env
        c = self.config
        repack_env = self.query_env(partial_env=c.get("repack_env"))
        self.repack_env = repack_env
        return self.repack_env

    def query_upload_env(self):
        if self.upload_env:
            return self.upload_env
        c = self.config
        buildid = self.query_buildid()
        upload_env = self.query_env(partial_env=c.get("upload_env"),
                                    replace_dict={'buildid': buildid})
        self.upload_env = upload_env
        return self.upload_env

    def _query_make_ident_output(self):
        """Get |make ident| output from the objdir.
        Only valid after setup is run.
        """
        if self.make_ident_output:
            return self.make_ident_output
        env = self.query_repack_env()
        dirs = self.query_abs_dirs()
        output = self.get_output_from_command(["make", "ident"],
                                              cwd=dirs['abs_locales_dir'],
                                              env=env,
                                              halt_on_failure=True)
        self.make_ident_output = output
        return output

    def query_buildid(self):
        """Get buildid from the objdir.
        Only valid after setup is run.
        """
        if self.buildid:
            return self.buildid
        r = re.compile("buildid (\d+)")
        output = self._query_make_ident_output()
        for line in output.splitlines():
            m = r.match(line)
            if m:
                self.buildid = m.groups()[0]
        return self.buildid

    def query_revision(self):
        """Get revision from the objdir.
        Only valid after setup is run.
        """
        if self.revision:
            return self.revision
        r = re.compile(r"gecko_revision ([0-9a-f]{12}\+?)")
        output = self._query_make_ident_output()
        for line in output.splitlines():
            m = r.match(line)
            if m:
                self.revision = m.groups()[0]
        return self.revision

    def _query_make_variable(self, variable, make_args=None):
        make = self.query_exe('make')
        env = self.query_repack_env()
        dirs = self.query_abs_dirs()
        if make_args is None:
            make_args = []
        # TODO error checking
        return self.get_output_from_command(
            [make, "echo-variable-%s" % variable] + make_args,
            cwd=dirs['abs_locales_dir'],
            env=env
        )

    def query_base_package_name(self):
        """Get the package name from the objdir.
        Only valid after setup is run.
        """
        if self.base_package_name:
            return self.base_package_name
        self.base_package_name = self._query_make_variable(
            "PACKAGE",
            make_args=['AB_CD=%(locale)s']
        )
        return self.base_package_name

    def query_version(self):
        """Get the package name from the objdir.
        Only valid after setup is run.
        """
        if self.version:
            return self.version
        self.version = self._query_make_variable(
            "MOZ_APP_VERSION",
        )
        return self.version

    # Actions {{{2
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
        else:
            repos = c['repos']
        self.vcs_checkout_repos(repos, parent_dir=dirs['abs_work_dir'],
                                tag_override=c.get('tag_override'))
        self.pull_locale_source()

    def preflight_setup(self):
        if 'clobber' not in self.actions:
            c = self.config
            dirs = self.query_abs_dirs()
            objdir = os.path.join(dirs['abs_work_dir'], c['mozilla_dir'],
                                  c['objdir'])
            self.rmtree(objdir)

    def setup(self):
        c = self.config
        dirs = self.query_abs_dirs()
        mozconfig_path = os.path.join(dirs['abs_mozilla_dir'], '.mozconfig')
        self.copyfile(os.path.join(dirs['abs_work_dir'], c['mozconfig']),
                      mozconfig_path)
        # TODO stop using cat
        cat = self.query_exe("cat")
        hg = self.query_exe("hg")
        make = self.query_exe("make")
        self.run_command([cat, mozconfig_path])
        env = self.query_repack_env()
        self.run_command([make, "-f", "client.mk", "configure"],
                         cwd=dirs['abs_mozilla_dir'],
                         env=env,
                         error_list=MakefileErrorList,
                         halt_on_failure=True)
        for make_dir in c.get('make_dirs', []):
            self.run_command([make],
                             cwd=os.path.join(dirs['abs_objdir'], make_dir),
                             env=env,
                             error_list=MakefileErrorList,
                             halt_on_failure=True)
        self.run_command([make, "wget-en-US"],
                         cwd=dirs['abs_locales_dir'],
                         env=env,
                         error_list=MakefileErrorList,
                         halt_on_failure=True)
        self.run_command([make, "unpack"],
                         cwd=dirs['abs_locales_dir'],
                         env=env,
                         error_list=MakefileErrorList,
                         halt_on_failure=True)
        revision = self.query_revision()
        if not revision:
            self.fatal("Can't determine revision!")
        # TODO do this through VCSMixin instead of hardcoding hg
        self.run_command([hg, "update", "-r", revision],
                         cwd=dirs["abs_mozilla_dir"],
                         env=env,
                         error_list=BaseErrorList,
                         halt_on_failure=True)

    def repack(self):
        # TODO per-locale logs and reporting.
        # TODO query_locales chunking.
        c = self.config
        dirs = self.query_abs_dirs()
        locales = self.query_locales()
        make = self.query_exe("make")
        repack_env = self.query_repack_env()
        base_package_name = self.query_base_package_name()
        base_package_dir = os.path.join(dirs['abs_objdir'], 'dist')
        successful_count = total_count = 0
        for locale in locales:
            total_count += 1
            if self.run_compare_locales(locale):
                self.add_failure(locale, message="%s failed in compare-locales!" % locale)
                continue
            if self.run_command([make, "installers-%s" % locale],
                                cwd=dirs['abs_locales_dir'],
                                env=repack_env,
                                error_list=MakefileErrorList,
                                halt_on_failure=False):
                self.add_failure(locale, message="%s failed in make installers-%s!" % (locale, locale))
                continue
            signed_path = os.path.join(base_package_dir,
                                       base_package_name % {'locale': locale})
            status = self.verify_android_signature(
                signed_path,
                script=c['signature_verification_script'],
                env=repack_env
            )
            if status:
                self.add_failure(locale, message="Errors verifying %s apk!" % locale)
                # No need to rm because upload is per-locale
                continue
            success_count += 1
        self.summarize_success_count(success_count, total_count,
                                     message="Repacked %d of %d apks successfully.")

    def upload_repacks(self):
        c = self.config
        dirs = self.query_abs_dirs()
        locales = self.query_locales()
        make = self.query_exe("make")
        upload_env = self.query_upload_env()
        success_count = total_count = 0
        for locale in locales:
            if self.query_failure(locale):
                self.warning("Skipping previously failed locale %s." % locale)
                continue
            total_count += 1
            if self.run_command([make, "upload", "AB_CD=%s" % locale],
                                cwd=dirs['abs_locales_dir'],
                                env=upload_env,
                                error_list=MakefileErrorList,
                                halt_on_failure=False):
                self.add_failure(locale, message="%s failed in make upload!" % (locale))
                continue
            successful_count += 1
        self.summarize_success_count(success_count, total_count,
                                     message="Uploaded %d of %d apks successfully.")

    def create_nightly_snippets(self):
        c = self.config
        dirs = self.query_abs_dirs()
        env = self.query_repack_env()
        locales = self.query_locales()
        base_package_name = self.query_base_package_name()
        buildid = self.query_buildid()
        version = self.query_version()
        binary_dir = os.path.join(dirs['abs_objdir'], 'dist')
        success_count = total_count = 0
        replace_dict = {
            'buildid': buildid,
            'build_target': c['build_target'],
        }
        for locale in locales:
            total_count += 1
            replace_dict['locale'] = locale
            aus_base_dir = c['aus_base_dir'] % replace_dict
            aus_abs_dir = os.path.join(dirs['abs_work_dir'], 'update',
                                       aus_base_dir)
            binary_path = os.path.join(binary_dir,
                                       base_package_name % {'locale': locale})
            if not self.create_complete_snippet(binary_path, version, aus_abs_dir):
                self.add_failure(locale, message="Errors creating snippet for %s!  Removing snippet directory." % locale)
                self.rmtree(aus_abs_dir)
                continue
            self.run_command("touch", os.path.join(aus_abs_dir, "partial.txt"))
            success_count += 1
        self.summarize_success_count(success_count, total_count,
                                     message="Created %d of %d snippets successfully.")

    def upload_nightly_snippets(self):
        c = self.config
        rc = self.query_release_config()
        dirs = self.query_abs_dirs()
        update_dir = os.path.join(dirs['abs_work_dir'], 'update',)
        if not os.path.exists(update_dir):
            self.error("No such directory %s! Skipping..." % update_dir)
            return
        rsync = self.query_exe("rsync")
        ssh = self.query_exe("ssh")
        aus_upload_dir = c['aus_upload_base_dir']
        cmd = [ssh, '-oIdentityFile=%s' % rc['aus_ssh_key'],
               '%s@%s' % (rc['aus_user'], rc['aus_server']),
               'mkdir', '-p', aus_upload_dir]
        self.run_command(cmd, cwd=dirs['abs_work_dir'],
                         error_list=SSHErrorList)
        cmd = [rsync, '-e']
        cmd += ['%s -oIdentityFile=%s' % (ssh, rc['aus_ssh_key']), '-azv', './']
        cmd += ["%s@%s:%s/" % (rc['aus_user'], rc['aus_server'], aus_upload_dir)]
        self.run_command(cmd, cwd=update_dir, error_list=SSHErrorList)



# main {{{1
if __name__ == '__main__':
    single_locale = MobileSingleLocale()
    single_locale.run()
