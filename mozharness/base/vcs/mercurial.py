#!/usr/bin/env python
"""Mercurial VCS support.
"""

import os

from mozharness.base.errors import HgErrorList
from mozharness.base.script import BaseScript

# Mercurial {{{1
class MercurialMixin(object):
    def scm_checkout(self, repo, parent_dir=None, tag="default",
                     dir_name=None, clobber=False, halt_on_failure=True):
        if not dir_name:
            dir_name = os.path.basename(repo)
        if parent_dir:
            dir_path = os.path.join(parent_dir, dir_name)
            self.mkdir_p(parent_dir)
        else:
            dir_path = dir_name
        if clobber and os.path.exists(dir_path):
            self.rmtree(dir_path)
        if not os.path.exists(dir_path):
            command = "hg clone %s %s" % (repo, dir_name)
        else:
            command = "hg --cwd %s pull" % (dir_name)
        self.run_command(command, cwd=parent_dir, halt_on_failure=halt_on_failure,
                        error_list=HgErrorList)
        self.scm_update(dir_path, tag=tag, halt_on_failure=halt_on_failure)

    def scm_update(self, dir_path, tag="default", halt_on_failure=True):
        command = "hg --cwd %s update -C -r %s" % (dir_path, tag)
        self.run_command(command, halt_on_failure=halt_on_failure,
                        error_list=HgErrorList)

    def scm_checkout_repos(self, repo_list, parent_dir=None,
                           clobber=False, halt_on_failure=True):
        c = self.config
        if not parent_dir:
            parent_dir = os.path.join(c['base_work_dir'], c['work_dir'])
        self.mkdir_p(parent_dir)
        for repo_dict in repo_list:
            kwargs = repo_dict.copy()
            kwargs['parent_dir'] = parent_dir
            kwargs['clobber'] = clobber
            kwargs['halt_on_failure'] = halt_on_failure
            self.scm_checkout(**kwargs)

class MercurialScript(MercurialMixin, BaseScript):
    def __init__(self, **kwargs):
        super(MercurialScript, self).__init__(**kwargs)
        
        


# __main__ {{{1
if __name__ == '__main__':
    pass
