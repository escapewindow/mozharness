#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****
'''Python usage, esp. virtualenv.
'''

import os

from mozharness.base.errors import VirtualenvErrorList
from mozharness.base.log import WARNING, FATAL

# Virtualenv {{{1
virtualenv_config_options = [[
 ["--venv-path", "--virtualenv-path"],
 {"action": "store",
  "dest": "virtualenv_path",
  "default": "venv",
  "help": "Specify the path to the virtualenv top level directory"
 }
],
[["--virtualenv"],
 {"action": "store",
  "dest": "virtualenv",
  "help": "Specify the virtualenv executable to use"
  }
],
[["--pypi-url"],
 {"action": "store",
  "dest": "pypi_url",
  "help": "Base URL of Python Package Index (default http://pypi.python.org/simple/)"
  }
],
[["--find-links"],
{"action": "extend",
 "dest": "find_links",
 "help": "URL to look for packages at"
}
]]

class VirtualenvMixin(object):
    '''BaseScript mixin, designed to create and use virtualenvs.

    Config items:
     * virtualenv_path points to the virtualenv location on disk.
     * virtualenv_modules lists the module names.
     * MODULE_url list points to the module URLs (optional)
    Requires virtualenv to be in PATH.
    Depends on OSMixin
    '''
    python_paths = {}
    site_packages_path = None

    def query_virtualenv_path(self):
        c = self.config
        dirs = self.query_abs_dirs()
        if 'abs_virtualenv_dir' in dirs:
            return dirs['abs_virtualenv_dir']
        if os.path.isabs(c['virtualenv_path']):
            return c['virtualenv_path']
        return os.path.join(dirs['abs_work_dir'], c['virtualenv_path'])

    def query_python_path(self, binary="python"):
        """Return the path of a binary inside the virtualenv, if
        c['virtualenv_path'] is set; otherwise return the binary name.
        Otherwise return None
        """
        self._check_existing_virtualenv()
        if binary not in self.python_paths:
            bin_dir = 'bin'
            if self._is_windows():
                bin_dir = 'Scripts'
            virtualenv_path = self.query_virtualenv_path()
            if virtualenv_path:
                self.python_paths[binary] = os.path.abspath(os.path.join(virtualenv_path, bin_dir, binary))
            else:
                self.python_paths[binary] = self.query_exe(binary)
        return self.python_paths[binary]

    def query_python_site_packages_path(self):
        if self.site_packages_path:
            return self.site_packages_path
        python = self.query_python_path()
        self.site_packages_path = self.get_output_from_command(
            [python, '-c',
             'from distutils.sysconfig import get_python_lib; ' + \
             'print(get_python_lib())'])
        return self.site_packages_path

    def package_versions(self, pip_freeze_output=None, error_level=WARNING):
        """
        reads packages from `pip freeze` output and returns a dict of
        {package_name: 'version'}
        """
        packages = {}

        if pip_freeze_output is None:
            # get the output from `pip freeze`
            pip = self.query_python_path("pip")
            if not pip:
                self.log("package_versions: Program pip not in path", level=error_level)
                return {}
            pip_freeze_output = self.get_output_from_command([pip, "freeze"], silent=True)
            if not isinstance(pip_freeze_output, basestring):
                self.fatal("package_versions: Error encountered running `pip freeze`: %s" % pip_freeze_output)

        for line in pip_freeze_output.splitlines():
            # parse the output into package, version
            line = line.strip()
            if not line:
                # whitespace
                continue
            if line.startswith('-'):
                # not a package, probably like '-e http://example.com/path#egg=package-dev'
                continue
            if '==' not in line:
                self.fatal("pip_freeze_packages: Unrecognized output line: %s" % line)
            package, version = line.split('==', 1)
            packages[package] = version

        return packages

    def is_python_package_installed(self, package_name, error_level=WARNING):
        """
        Return whether the package is installed
        """
        packages = self.package_versions(error_level=error_level).keys()
        return package_name.lower() in [package.lower() for package in packages]

    def _check_existing_virtualenv(self, error_level=WARNING):
        if 'VIRTUAL_ENV' in os.environ:
            self.log("VIRTUAL_ENV %s set; this may break mozharness virtualenv calls!" % os.environ['VIRTUAL_ENV'],
                     level=error_level)
            return True

    def install_module(self, module, module_url=None, install_method=None):
        """
        Install module via pip.

        module_url can be a url to a python package tarball, a path to
        a directory containing a setup.py (absolute or relative to work_dir)
        or None, in which case it will default to the module name.
        """
        c = self.config
        dirs = self.query_abs_dirs()
        venv_path = self.query_virtualenv_path()
        self.info("Installing %s into virtualenv %s" % (module, venv_path))
        if not module_url:
            module_url = module
        if install_method in (None, 'pip'):
            pip = self.query_python_path("pip")
            command = [pip, "install"]
            pypi_url = c.get("pypi_url")
            if pypi_url:
                command += ["--pypi-url", pypi_url]
            virtualenv_cache_dir = c.get("virtualenv_cache_dir")
            if virtualenv_cache_dir:
                self.mkdir_p(virtualenv_cache_dir)
                command += ["--download-cache", virtualenv_cache_dir]
        elif install_method == 'easy_install':
            # Allow easy_install to be overridden by
            # self.config['exes']['easy_install']
            default = 'easy_install'
            if self._is_windows():
                # Don't invoke `easy_install` directly on windows since
                # the 'install' in the executable name hits UAC
                # - http://answers.microsoft.com/en-us/windows/forum/windows_7-security/uac-message-do-you-want-to-allow-the-following/bea30ad8-9ef8-4897-aab4-841a65f7af71
                # - https://bugzilla.mozilla.org/show_bug.cgi?id=791840
                default = [self.query_python_path(), self.query_python_path('easy_install-script.py')]
            command = self.query_exe('easy_install', default=default, return_type="list")
        else:
            self.fatal("install_module() doesn't understand an install_method of %s!" % install_method)

        # Add --find-links pages to look at
        for link in c.get('find_links', []):
            command.extend(["--find-links", link])

        # Allow for errors while building modules, but require a
        # return status of 0.
        if self.run_command(command + [module_url],
                            error_list=VirtualenvErrorList,
                            cwd=dirs['abs_work_dir']) != 0:
            self.fatal("Unable to install %s!" % module_url)

    def create_virtualenv(self, modules=None):
        """
        Create a python virtualenv.

        The virtualenv exe can be defined in c['virtualenv'] or
        c['exes']['virtualenv'], as a string (path) or list (path +
        arguments).

        c['virtualenv_python_dll'] is an optional config item that works
        around an old windows virtualenv bug.

        virtualenv_modules can be a list of module names to install, e.g.

            virtualenv_modules = ['module1', 'module2']

        or it can be a list of dicts that define a module: url-or-path,
        or a combination.

            virtualenv_modules = [
                'module1',
                {'module2': 'http://url/to/package'},
                {'module3': os.path.join('path', 'to', 'setup_py', 'dir')},
            ]
        """
        c = self.config
        dirs = self.query_abs_dirs()
        venv_path = self.query_virtualenv_path()
        self._check_existing_virtualenv()
        self.info("Creating virtualenv %s" % venv_path)
        virtualenv = c.get('virtualenv', self.query_exe('virtualenv'))
        if isinstance(virtualenv, str):
            if not os.path.exists(virtualenv) and not self.which(virtualenv):
                self.add_summary("The executable '%s' is not found; not creating virtualenv!" % virtualenv, level=FATAL)
                return -1
            # allow for [python, virtualenv] in config
            virtualenv = [virtualenv]

        # https://bugs.launchpad.net/virtualenv/+bug/352844/comments/3
        # https://bugzilla.mozilla.org/show_bug.cgi?id=700415#c50
        if c.get('virtualenv_python_dll'):
            # We may someday want to copy a differently-named dll, but
            # let's not think about that right now =\
            dll_name = os.path.basename(c['virtualenv_python_dll'])
            target = self.query_python_path(dll_name)
            scripts_dir = os.path.dirname(target)
            self.mkdir_p(scripts_dir)
            self.copyfile(c['virtualenv_python_dll'], target)
        else:
            self.mkdir_p(dirs['abs_work_dir'])

        # make this list configurable?
        for module in ('distribute', 'pip'):
            if c.get('%s_url' % module):
                self.download_file(c['%s_url' % module],
                                   parent_dir=dirs['abs_work_dir'])

        virtualenv_options = c.get('virtualenv_options',
                                   ['--no-site-packages', '--distribute'])

        self.run_command(virtualenv + virtualenv_options + [venv_path],
                         cwd=dirs['abs_work_dir'],
                         error_list=VirtualenvErrorList,
                         halt_on_failure=True)
        if not modules:
            modules = c.get('virtualenv_modules', [])
        for module in modules:
            module_url = module
            if isinstance(module, dict):
                (module, module_url) = module.items()[0]
            else:
                module_url = self.config.get('%s_url' % module, module_url)
            install_method = 'pip'
            if module in ('pywin32',):
                install_method = 'easy_install'
            self.install_module(module, module_url,
                                install_method=install_method)
        self.info("Done creating virtualenv %s." % venv_path)



# __main__ {{{1

if __name__ == '__main__':
    '''TODO: unit tests.
    '''
    pass
