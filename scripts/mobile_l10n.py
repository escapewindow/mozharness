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

# So far this only references the ftp platform name.
SUPPORTED_PLATFORMS = ["android", "android-xul"]
JARSIGNER_ERROR_LIST = [{
    "substr": "command not found",
    "level": FATAL,
},{
    "substr": "jarsigner error: java.lang.RuntimeException: keystore load: Keystore was tampered with, or password was incorrect",
    "level": FATAL,
    "explanation": "The store passphrase is probably incorrect!",
},{
    "regex": re.compile("jarsigner: key associated with .* not a private key"),
    "level": FATAL,
    "explanation": "The key passphrase is probably incorrect!",
},{
    "regex": re.compile("jarsigner error: java.lang.RuntimeException: keystore load: .* .No such file or directory"),
    "level": FATAL,
    "explanation": "The keystore doesn't exist!",
},{
    "substr": "jarsigner: unable to open jar file:",
    "level": FATAL,
    "explanation": "The apk is missing!",
}]
TEST_JARSIGNER_ERROR_LIST = [{
    "substr": "jarsigner: unable to open jar file:",
    "level": IGNORE,
}] + JARSIGNER_ERROR_LIST



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
     ['--platform',],
     {"action": "store",
      "dest": "platform",
      "type": "choice",
      "choices": SUPPORTED_PLATFORMS,
      "help": "Specify the platform to sign"
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
     ['--version',],
     {"action": "store",
      "dest": "version",
      "type": "string",
      "help": "Specify the current version"
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
            ],
            require_config_file=require_config_file
        )
        self.repack_env = None
        self.upload_env = None
        self.buildid = None
        self.revision = None
        self.make_ident_output = None

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

    def _query_local_build_id(self):
        if self.buildid:
            return self.buildid
        r = re.compile("buildid (\d+)")
        output = self._query_make_ident_output()
        for line in output.splitlines():
            m = r.match(line)
            if m:
                self.buildid = m.groups()[0]
        return self.buildid

    def _query_local_revision(self):
        if self.revision:
            return self.revision
        r = re.compile(r"gecko_revision ([0-9a-f]{12}\+?)")
        output = self._query_make_ident_output()
        for line in output.splitlines():
            m = r.match(line)
            if m:
                self.revision = m.groups()[0]
        return self.revision

    def query_buildid(self, platform=None, base_url=None, buildnum=None,
                      version=None):
        # TODO enable release-style buildid queries a la sign_android.py
        return self._query_local_build_id()

    def query_revision(self):
        return self._query_local_revision()

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
        successful_repacks = total_repacks = 0
        for locale in locales:
            total_repacks += 1
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
            # TODO verify signature
            successful_repacks += 1
        level=INFO
        if successful_repacks < total_repacks:
            level=ERROR
        self.add_summary("Repacked %d of %d apks successfully." % (successful_repacks, total_repacks), level=level)

    def upload_repacks(self):
        c = self.config
        dirs = self.query_abs_dirs()
        locales = self.query_locales()
        make = self.query_exe("make")
        upload_env = self.query_upload_env()
        successful_uploads = total_uploads = 0
        for locale in locales:
            if self.query_failure(locale):
                self.warning("Skipping previously failed locale %s." % locale)
                continue
            total_uploads += 1
            if self.run_command([make, "upload", "AB_CD=%s" % locale],
                                cwd=dirs['abs_locales_dir'],
                                env=upload_env,
                                error_list=MakefileErrorList,
                                halt_on_failure=False):
                self.add_failure(locale, message="%s failed in make upload!" % (locale))
                continue
            successful_uploads += 1
        level=INFO
        if successful_uploads < total_uploads:
            level=ERROR
        self.add_summary("Uploaded %d of %d apks successfully." % (successful_uploads, total_uploads), level=level)
        # TODO updates to a different function.
        # make echo-variable-PACKAGE AB_CD=es-ES
        # TODO create snippets
        # TODO upload snippets
        # TODO final add_summaries

    def verify_signatures(self):
        c = self.config
        rc = self.query_release_config()
        dirs = self.query_abs_dirs()
        verification_error_list = BaseErrorList + [{
            "regex": re.compile(r'''^Invalid$'''),
            "level": FATAL,
            "explanation": "Signature is invalid!"
        },{
            "substr": "filename not matched",
            "level": ERROR,
        },{
            "substr": "ERROR: Could not unzip",
            "level": ERROR,
        },{
            "regex": re.compile(r'''Are you sure this is a (nightly|release) package'''),
            "level": FATAL,
            "explanation": "Not signed!"
        }]
        locales = self.query_locales()
        env = self.query_repack_env()
        for platform in c['platforms']:
            for locale in locales:
                signed_path = '%s/%s/%s' % (platform, locale,
                    c['apk_base_name'] % {'version': rc['version'],
                                          'locale': locale})
                self.run_command([c['signature_verification_script'],
                                  '--tools-dir=tools/',
                                  '--%s' % c['key_alias'],
                                  '--apk=%s' % signed_path],
                                 cwd=dirs['abs_work_dir'],
                                 env=env,
                                 error_list=verification_error_list)

        c = self.config
        if not c['platforms']:
            self.info("No platforms to rsync! Skipping...")
            return
        rc = self.query_release_config()
        dirs = self.query_abs_dirs()
        rsync = self.query_exe("rsync")
        ssh = self.query_exe("ssh")
        ftp_upload_dir = c['ftp_upload_base_dir'] % {
            'version': rc['version'],
            'buildnum': rc['buildnum'],
        }
        cmd = [ssh, '-oIdentityFile=%s' % rc['ftp_ssh_key'],
               '%s@%s' % (rc['ftp_user'], rc['ftp_server']),
               'mkdir', '-p', ftp_upload_dir]
        self.run_command(cmd, cwd=dirs['abs_work_dir'],
                         error_list=SSHErrorList)
        cmd = [rsync, '-e']
        cmd += ['%s -oIdentityFile=%s' % (ssh, rc['ftp_ssh_key']), '-azv']
        cmd += c['platforms']
        cmd += ["%s@%s:%s/" % (rc['ftp_user'], rc['ftp_server'], ftp_upload_dir)]
        self.run_command(cmd, cwd=dirs['abs_work_dir'],
                         error_list=SSHErrorList)

    def create_snippets(self):
        c = self.config
        rc = self.query_release_config()
        dirs = self.query_abs_dirs()
        locales = self.query_locales()
        replace_dict = {
            'version': rc['version'],
            'buildnum': rc['buildnum'],
        }
        total_count = {'snippets': 0, 'links': 0}
        successful_count = {'snippets': 0, 'links': 0}
        for platform in c['update_platforms']:
            buildid = self.query_buildid(platform, c['buildid_base_url'])
            old_buildid = self.query_buildid(platform, c['old_buildid_base_url'],
                                             buildnum=rc['old_buildnum'],
                                             version=rc['old_version'])
            if not buildid:
                self.add_summary("Can't get buildid for %s! Skipping..." % platform, level=ERROR)
                continue
            replace_dict['platform'] = platform
            replace_dict['buildid'] = buildid
            for locale in locales:
                replace_dict['locale'] = locale
                parent_dir = '%s/%s/%s' % (dirs['abs_work_dir'],
                                           platform, locale)
                replace_dict['apk_name'] = c['apk_base_name'] % replace_dict
                signed_path = '%s/%s' % (parent_dir, replace_dict['apk_name'])
                if not os.path.exists(signed_path):
                    self.add_summary("Unable to create snippet for %s:%s: apk doesn't exist!" % (platform, locale), level=ERROR)
                    continue
                replace_dict['size'] = self.query_filesize(signed_path)
                replace_dict['sha512_hash'] = self.query_sha512sum(signed_path)
                for channel, channel_dict in c['update_channels'].items():
                    total_count['snippets'] += 1
                    total_count['links'] += 1
                    replace_dict['url'] = channel_dict['url'] % replace_dict
                    # Create previous link
                    previous_dir = os.path.join(dirs['abs_work_dir'], 'update',
                                                channel_dict['dir_base_name'] % (replace_dict),
                                                'Fennec', rc['old_version'],
                                                c['update_platform_map'][platform],
                                                old_buildid, locale, channel)
                    self.mkdir_p(previous_dir)
                    self.run_command(["touch", "partial.txt"],
                                     cwd=previous_dir, error_list=BaseErrorList)
                    status = self.run_command(
                        ['ln', '-s',
                         '../../../../../snippets/%s/%s/latest-%s' % (platform, locale, channel),
                         'complete.txt'],
                        cwd=previous_dir, error_list=BaseErrorList
                    )
                    if not status:
                        successful_count['links'] += 1
                    # Create snippet
                    contents = channel_dict['template'] % replace_dict
                    snippet_dir = "%s/update/%s/Fennec/snippets/%s/%s" % (
                      dirs['abs_work_dir'],
                      channel_dict['dir_base_name'] % (replace_dict),
                      platform, locale)
                    snippet_file = "%s/latest-%s" % (snippet_dir, channel)
                    self.info("Creating snippet for %s %s %s" % (platform, locale, channel))
                    self.mkdir_p(snippet_dir)
                    try:
                        fh = open(snippet_file, 'w')
                        fh.write(contents)
                        fh.close()
                    except:
                        self.add_summary("Unable to write to %s!" % snippet_file, level=ERROR)
                        self.info("File contents: \n%s" % contents)
                    else:
                        successful_count['snippets'] += 1
        level = INFO
        for k in successful_count.keys():
            if successful_count[k] < total_count[k]:
                level = ERROR
            self.add_summary("Created %d of %d %s successfully." % \
                             (successful_count[k], total_count[k], k),
                             level=level)

    def upload_snippets(self):
        c = self.config
        rc = self.query_release_config()
        dirs = self.query_abs_dirs()
        update_dir = os.path.join(dirs['abs_work_dir'], 'update',)
        if not os.path.exists(update_dir):
            self.error("No such directory %s! Skipping..." % update_dir)
            return
        rsync = self.query_exe("rsync")
        ssh = self.query_exe("ssh")
        aus_upload_dir = c['aus_upload_base_dir'] % {
            'version': rc['version'],
            'buildnum': rc['buildnum'],
        }
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
