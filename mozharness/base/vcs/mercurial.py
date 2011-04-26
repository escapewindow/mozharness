#!/usr/bin/env python
"""Mercurial VCS support.
"""

import os
import re
import subprocess
from urlparse import urlsplit

# TODO delete
import sys
sys.path.insert(1, os.path.dirname(os.path.dirname(os.path.dirname(sys.path[0]))))

from mozharness.base.errors import HgErrorList, VCSException
from mozharness.base.log import LogMixin
from mozharness.base.script import BaseScript, ShellMixin, OSMixin

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



# MercurialVCS {{{1
#
#from util.commands import run_cmd, get_output, remove_path
#from util.retry import retry
#
#import logging
#log = logging.getLogger(__name__)
class DefaultShareBase:
    pass
DefaultShareBase = DefaultShareBase()

class MercurialVCS(ShellMixin, OSMixin, LogMixin, object):
    def __init__(self, log_obj=None, config=None, vcs_config=None):
        super(MercurialVCS, self).__init__()
        self.branch = None
        self.repo = None
        self.revision = None
        self.log_obj = log_obj
        self.config = config
        # TODO gotta implement this
        # vcs_config = {
        #  repo: repository,
        #  branch: branch,
        #  revision: revision,
        #  hg_host: hg_host,
        #  ssh_username: ssh_username,
        #  ssh_key: ssh_key,
        # }
        self.vcs_config = vcs_config

    def query_revision(self, error_level='error'):
        if self.revision:
            return self.revision
        if 'revision' in self.vcs_config:
            self.revision = self.vcs_config['revision']
        # else: ??? + profit
        if self.revision:
            return self.revision
        else:
            self.log("Can't determine revision in %s" % __name__,
                     level=error_level)

    def query_branch(self, error_level='warning'):
        if self.branch:
            return self.branch
        if 'branch' in self.vcs_config:
            self.branch = self.vcs_config['branch']
        # else: ??? + profit
        if self.branch:
            return self.branch
        else:
            self.log("Can't determine branch in %s" % __name__,
                     level=error_level)

    def query_repo(self, error_level='error'):
        if self.repo:
            return self.repo
        if 'repo' in self.vcs_config:
            self.repo = self.vcs_config['repo']
        # else: ??? + profit
        if self.repo:
            return self.repo
        else:
            self.log("Can't determine repo in %s" % __name__,
                     level=error_level)

    # TODO rename?
    def _make_absolute(self, repo):
        if repo.startswith("file://"):
            path = repo[len("file://"):]
            repo = "file://%s" % os.path.abspath(path)
        elif "://" not in repo:
            repo = os.path.abspath(repo)
        return repo

    # TODO get these from vcs_config?
    def make_hg_url(self, hg_host, repo_path, protocol='http', revision=None,
                    filename=None):
        """construct a valid hg url from a base hg url (hg.mozilla.org),
        repo_path, revision and possible filename"""
        base = '%s://%s' % (protocol, hg_host)
        repo = '/'.join(p.strip('/') for p in [base, repo_path])
        if not filename:
            if not revision:
                return repo
            else:
                return '/'.join([p.strip('/') for p in [repo, 'rev', revision]])
        else:
            revision = self.query_revision()
            return '/'.join([p.strip('/') for p in [repo, 'raw-file', revision, filename]])

    # TODO self.repo
    def get_repo_name(self, repo):
        return repo.rstrip('/').split('/')[-1]

    # TODO self.repo
    def get_repo_path(self, repo):
        repo = self._make_absolute(repo)
        if repo.startswith("/"):
            return repo.lstrip("/")
        else:
            return urlsplit(repo).path.lstrip("/")

    def get_revision_from_path(self, path):
        """Returns which revision directory `path` currently has checked out."""
        return self.get_output_from_command(
            ['hg', 'parent', '--template', '{node|short}'], cwd=path
        )

    def get_branch_from_path(self, path):
        return self.get_output_from_command(['hg', 'branch'], cwd=path).strip()

    def get_branches_from_path(self, path):
        branches = []
        for line in self.get_output_from_command(['hg', 'branches', '-c'],
                                                 cwd=path).splitlines():
            branches.append(line.split()[0])
        return branches

    def hg_ver(self):
        """Returns the current version of hg, as a tuple of
        (major, minor, build)"""
        ver_string = self.get_output_from_command(['hg', '-q', 'version'])
        match = re.search("\(version ([0-9.]+)\)", ver_string)
        if match:
            bits = match.group(1).split(".")
            if len(bits) < 3:
                bits += (0,)
            ver = tuple(int(b) for b in bits)
        else:
            ver = (0, 0, 0)
        self.debug("Running hg version %s", ver)
        return ver

    def update(self, dest, branch=None, revision=None):
        """Updates working copy `dest` to `branch` or `revision`.  If
        neither is set then the working copy will be updated to the latest
        revision on the current branch.  Local changes will be discarded.
        """
        # If we have a revision, switch to that
        if revision is not None:
            cmd = ['hg', 'update', '-C', '-r', revision]
            self.run_command(cmd, cwd=dest, error_list=HgErrorList)
        else:
            # Check & switch branch
            local_branch = self.get_output_from_command(['hg', 'branch'],
                                                        cwd=dest).strip()

            cmd = ['hg', 'update', '-C']

            # If this is different, checkout the other branch
            if branch and branch != local_branch:
                cmd.append(branch)

            self.run_command(cmd, cwd=dest, error_list=HgErrorList)
        return self.get_revision_from_path(dest)

    def clone(self, repo, dest, branch=None, revision=None, update_dest=True):
        """Clones hg repo and places it at `dest`, replacing whatever else
        is there.  The working copy will be empty.

        If `revision` is set, only the specified revision and its ancestors
        will be cloned.

        If `update_dest` is set, then `dest` will be updated to `revision`
        if set, otherwise to `branch`, otherwise to the head of default.
        """
        if os.path.exists(dest):
            self.rmtree(dest)

        cmd = ['hg', 'clone']
        if not update_dest:
            cmd.append('-U')

        if revision:
            cmd.extend(['-r', revision])
        elif branch:
            # hg >= 1.6 supports -b branch for cloning
            ver = self.hg_ver()
            if ver >= (1, 6, 0):
                cmd.extend(['-b', branch])

        cmd.extend([repo, dest])
        self.run_command(cmd, error_list=HgErrorList)

        if update_dest:
            return self.update(dest, branch, revision)

    def common_args(self, revision=None, branch=None, ssh_username=None,
                    ssh_key=None):
        """Fill in common hg arguments, encapsulating logic checks that
        depend on mercurial versions and provided arguments
        """
        args = []
        if ssh_username or ssh_key:
            opt = ['-e', 'ssh']
            if ssh_username:
                opt[1] += ' -l %s' % ssh_username
            if ssh_key:
                opt[1] += ' -i %s' % ssh_key
            args.extend(opt)
        if revision:
            args.extend(['-r', revision])
        elif branch:
            if self.hg_ver() >= (1, 6, 0):
                args.extend(['-b', branch])
        return args

    def pull(self, repo, dest, update_dest=True, **kwargs):
        """Pulls changes from hg repo and places it in `dest`.

        If `revision` is set, only the specified revision and its ancestors
        will be pulled.

        If `update_dest` is set, then `dest` will be updated to `revision`
        if set, otherwise to `branch`, otherwise to the head of default.
        """
        # Convert repo to an absolute path if it's a local repository
        repo = self._make_absolute(repo)
        cmd = ['hg', 'pull']
        cmd.extend(self.common_args(**kwargs))
        cmd.append(repo)
        self.run_command(cmd, cwd=dest, error_list=HgErrorList)

        if update_dest:
            branch = self.query_branch()
        revision = None
        if 'revision' in kwargs and kwargs['revision']:
            revision = kwargs['revision']
        return self.update(dest, branch=branch, revision=revision)

    # Defines the places of attributes in the tuples returned by `out'
    REVISION, BRANCH = 0, 1

    def out(self, src, remote, **kwargs):
        """Check for outgoing changesets present in a repo"""
        cmd = ['hg', '-q', 'out', '--template', '{node} {branches}\n']
        cmd.extend(self.common_args(**kwargs))
        cmd.append(remote)
        if os.path.exists(src):
            try:
                revs = []
                for line in self.get_output_from_command(cmd, cwd=src).rstrip().split("\n"):
                    try:
                        rev, branch = line.split()
                    # Mercurial displays no branch at all if the revision
                    # is on "default"
                    except ValueError:
                        rev = line.rstrip()
                        branch = "default"
                    revs.append((rev, branch))
                return revs
            except subprocess.CalledProcessError, inst:
                # In some situations, some versions of Mercurial return "1"
                # if no changes are found, so we need to ignore this return
                # code
                if inst.returncode == 1:
                    return []
                # TODO self.error
                raise

#def push(src, remote, push_new_branches=True, **kwargs):
#    cmd = ['hg', 'push']
#    cmd.extend(self.common_args(**kwargs))
#    if push_new_branches:
#        cmd.append('--new-branch')
#    cmd.append(remote)
#    run_cmd(cmd, cwd=src)
#
#def mercurial(repo, dest, branch=None, revision=None, update_dest=True,
#              shareBase=DefaultShareBase, allowUnsharedLocalClones=False):
#    """Makes sure that `dest` is has `revision` or `branch` checked out from
#    `repo`.
#
#    Do what it takes to make that happen, including possibly clobbering
#    dest.
#
#    If allowUnsharedLocalClones is True and we're trying to use the share
#    extension but fail, then we will be able to clone from the shared repo to
#    our destination.  If this is False, the default, then if we don't have the
#    share extension we will just clone from the remote repository.
#    """
#    dest = os.path.abspath(dest)
#    if shareBase is DefaultShareBase:
#        shareBase = os.environ.get("HG_SHARE_BASE_DIR", None)
#
#    if shareBase:
#        # Check that 'hg share' works
#        try:
#            log.info("Checking if share extension works")
#            output = get_output(['hg', 'help', 'share'], dont_log=True)
#            if 'no commands defined' in output:
#                # Share extension is enabled, but not functional
#                log.info("Disabling sharing since share extension doesn't seem to work (1)")
#                shareBase = None
#            elif 'unknown command' in output:
#                # Share extension is disabled
#                log.info("Disabling sharing since share extension doesn't seem to work (2)")
#                shareBase = None
#        except subprocess.CalledProcessError:
#            # The command failed, so disable sharing
#            log.info("Disabling sharing since share extension doesn't seem to work (3)")
#            shareBase = None
#
#    # If the working directory already exists and isn't using share we update
#    # the working directory directly from the repo, ignoring the sharing
#    # settings
#    if os.path.exists(dest):
#        if not os.path.exists(os.path.join(dest, ".hg", "sharedpath")):
#            try:
#                return pull(repo, dest, update_dest=update_dest, branch=branch, revision=revision)
#            except subprocess.CalledProcessError:
#                log.warning("Error pulling changes into %s from %s; clobbering", dest, repo)
#                log.debug("Exception:", exc_info=True)
#                remove_path(dest)
#
#    # If that fails for any reason, and sharing is requested, we'll try to
#    # update the shared repository, and then update the working directory from
#    # that.
#    if shareBase:
#        sharedRepo = os.path.join(shareBase, get_repo_path(repo))
#        dest_sharedPath = os.path.join(dest, '.hg', 'sharedpath')
#        if os.path.exists(dest_sharedPath):
#            # Make sure that the sharedpath points to sharedRepo
#            dest_sharedPath_data = os.path.normpath(open(dest_sharedPath).read())
#            norm_sharedRepo = os.path.normpath(os.path.join(sharedRepo, '.hg'))
#            if dest_sharedPath_data != norm_sharedRepo:
#                # Clobber!
#                log.info("We're currently shared from %s, but are being requested to pull from %s (%s); clobbering", dest_sharedPath_data, repo, norm_sharedRepo)
#                remove_path(dest)
#
#        try:
#            log.info("Updating shared repo")
#            mercurial(repo, sharedRepo, branch=branch, revision=revision,
#                update_dest=False, shareBase=None)
#            if os.path.exists(dest):
#                return self.update(dest, branch=branch, revision=revision)
#
#            try:
#                log.info("Trying to share %s to %s", sharedRepo, dest)
#                return share(sharedRepo, dest, branch=branch, revision=revision)
#            except subprocess.CalledProcessError:
#                if not allowUnsharedLocalClones:
#                    # Re-raise the exception so it gets caught below.
#                    # We'll then clobber dest, and clone from original repo
#                    raise
#
#                log.warning("Error calling hg share from %s to %s;"
#                            "falling back to normal clone from shared repo",
#                            sharedRepo, dest)
#                # Do a full local clone first, and then update to the
#                # revision we want
#                # This lets us use hardlinks for the local clone if the OS
#                # supports it
#                clone(sharedRepo, dest, update_dest=False)
#                return self.update(dest, branch=branch, revision=revision)
#        except subprocess.CalledProcessError:
#            log.warning("Error updating %s from sharedRepo (%s): ", dest, sharedRepo)
#            log.debug("Exception:", exc_info=True)
#            remove_path(dest)
#
#    if not os.path.exists(os.path.dirname(dest)):
#        os.makedirs(os.path.dirname(dest))
#    # Share isn't available or has failed, clone directly from the source
#    return clone(repo, dest, branch, revision, update_dest=update_dest)
#
#def apply_and_push(localrepo, remote, changer, max_attempts=10,
#                   ssh_username=None, ssh_key=None):
#    """This function calls `changer' to make changes to the repo, and tries
#       its hardest to get them to the origin repo. `changer' must be a
#       callable object that receives two arguments: the directory of the local
#       repository, and the attempt number. This function will push ALL
#       changesets missing from remote."""
#    assert callable(changer)
#    branch = get_branch_from_path(localrepo)
#    changer(localrepo, 1)
#    for n in range(1, max_attempts+1):
#        try:
#            new_revs = out(src=localrepo, remote=remote,
#                           ssh_username=ssh_username,
#                           ssh_key=ssh_key)
#            if len(new_revs) < 1:
#                raise VCSException("No revs to push")
#            push(src=localrepo, remote=remote, ssh_username=ssh_username,
#                 ssh_key=ssh_key)
#            return
#        except subprocess.CalledProcessError, e:
#            log.debug("Hit error when trying to push: %s" % str(e))
#            if n == max_attempts:
#                log.debug("Tried %d times, giving up" % max_attempts)
#                for r in reversed(new_revs):
#                    run_cmd(['hg', 'strip', r[REVISION]], cwd=localrepo)
#                raise VCSException("Failed to push")
#            pull(remote, localrepo, update_dest=False,
#                 ssh_username=ssh_username, ssh_key=ssh_key)
#            # After we successfully rebase or strip away heads the push is
#            # is attempted again at the start of the loop
#            try:
#                run_cmd(['hg', 'rebase'], cwd=localrepo)
#            except subprocess.CalledProcessError, e:
#                log.debug("Failed to rebase: %s" % str(e))
#                self.update(localrepo, branch=branch)
#                for r in reversed(new_revs):
#                    run_cmd(['hg', 'strip', r[REVISION]], cwd=localrepo)
#                changer(localrepo, n+1)
#
#def share(source, dest, branch=None, revision=None):
#    """Creates a new working directory in "dest" that shares history with
#       "source" using Mercurial's share extension"""
#    run_cmd(['hg', 'share', '-U', source, dest])
#    return self.update(dest, branch=branch, revision=revision)
#
#def cleanOutgoingRevs(reponame, remote, username, sshKey):
#    outgoingRevs = retry(out, kwargs=dict(src=reponame, remote=remote,
#                                          ssh_username=username,
#                                          ssh_key=sshKey))
#    for r in reversed(outgoingRevs):
#        run_cmd(['hg', 'strip', r[REVISION]], cwd=reponame)


        
        


# __main__ {{{1
if __name__ == '__main__':
    pass
