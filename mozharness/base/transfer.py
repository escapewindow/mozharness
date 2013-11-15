#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****
"""Generic ways to upload + download files.
"""

import mimetypes
import os
import sys
import time
import urllib2
import urlparse
try:
    import simplejson as json
    assert json
except ImportError:
    import json

from mozharness.base.errors import SSHErrorList
from mozharness.base.log import ERROR


# TransferMixin {{{1
class TransferMixin(object):
    """
    Generic transfer methods.

    Dependent on BaseScript.
    """
    s3connection = None

    def rsync_upload_directory(self, local_path, ssh_key, ssh_user,
                               remote_host, remote_path,
                               rsync_options=None,
                               error_level=ERROR,
                               create_remote_directory=True,
                               ):
        """
        Create a remote directory and upload the contents of
        a local directory to it via rsync+ssh.

        Return None on success, not None on failure.
        """
        dirs = self.query_abs_dirs()
        self.info("Uploading the contents of %s to %s:%s" % (local_path, remote_host, remote_path))
        rsync = self.query_exe("rsync")
        ssh = self.query_exe("ssh")
        if rsync_options is None:
            rsync_options = ['-azv']
        if not os.path.isdir(local_path):
            self.log("%s isn't a directory!" % local_path,
                     level=ERROR)
            return -1
        if create_remote_directory:
            mkdir_error_list = [{
                'substr': r'''exists but is not a directory''',
                'level': ERROR
            }] + SSHErrorList
            if self.run_command([ssh, '-oIdentityFile=%s' % ssh_key,
                                 '%s@%s' % (ssh_user, remote_host),
                                 'mkdir', '-p', remote_path],
                                cwd=dirs['abs_work_dir'],
                                return_type='num_errors',
                                error_list=mkdir_error_list):
                self.log("Unable to create remote directory %s:%s!" % (remote_host, remote_path), level=error_level)
                return -2
        if self.run_command(
            [rsync, '-e', '%s -oIdentityFile=%s' % (ssh, ssh_key)] +
            rsync_options +
            ['.', '%s@%s:%s/' % (ssh_user, remote_host, remote_path)],
            cwd=local_path,
            return_type='num_errors',
            error_list=SSHErrorList,
        ):
            self.log("Unable to rsync %s to %s:%s!" % (local_path, remote_host, remote_path), level=error_level)
            return -3

    def rsync_download_directory(self, ssh_key, ssh_user, remote_host,
                                 remote_path, local_path,
                                 rsync_options=None,
                                 error_level=ERROR,
                                 ):
        """
        Create a remote directory and upload the contents of
        a local directory to it via rsync+ssh.

        Return None on success, not None on failure.
        """
        self.info("Downloading the contents of %s:%s to %s" % (remote_host, remote_path, local_path))
        rsync = self.query_exe("rsync")
        ssh = self.query_exe("ssh")
        if rsync_options is None:
            rsync_options = ['-azv']
        if not os.path.isdir(local_path):
            self.log("%s isn't a directory!" % local_path,
                     level=error_level)
            return -1
        if self.run_command(
            [rsync, '-e', '%s -oIdentityFile=%s' % (ssh, ssh_key)] +
            rsync_options + ['%s@%s:%s/' % (ssh_user, remote_host, remote_path),
                             '.'],
            cwd=local_path,
            return_type='num_errors',
            error_list=SSHErrorList
        ):
            self.log("Unable to rsync %s:%s to %s!" % (remote_host, remote_path, local_path), level=error_level)
            return -3

    def load_json_from_url(self, url, timeout=30):
        """ Loads json from a url, returns the loaded json
            """
        self.debug("Attempting to download %s; timeout=%i" % (url, timeout))
        r = urllib2.urlopen(url, timeout=timeout)
        j = json.load(r)
        return j

    def query_s3connection(self, error_level=ERROR):
        """ Imports boto and creates a connection.  Requires boto in venv.

            This assumes the credentials are in ~/.boto and only has a single
            connection available.  If we need more complex support, we'll
            have to write it (maybe with a dict of key/value self.s3connections?)
            """
        if self.s3connection:
            return self.s3connection
        if not hasattr(self, 'query_python_site_packages_path'):
            self.log("This script doesn't inherit VirtualenvMixin; can't import boto!",
                     level=error_level)
            return
        site_packages_path = self.query_python_site_packages_path()
        sys.path.append(site_packages_path)
        try:
            import boto
            try:
                from boto.s3.connection import S3Connection
                self.s3connection = S3Connection()
                return self.s3connection
            except boto.exception.NoAuthHandlerFound:
                self.log("Auth problems; do you have a ~/.boto ?",
                         level=error_level)
        except ImportError:
            self.log("Can't import boto!",
                     level=error_level)

    def upload_file_to_s3(self, bucket_name, file_path, key_name,
                          metadata=None, error_level=ERROR):
        """ Based on https://github.com/catlee/blobber/blob/master/blobber/amazons3_backend.py
            """
        if not os.path.exists(file_path):
            self.log("%s doesn't exist!" % file_path, level=error_level)
            return
        file_name = os.path.basename(file_path)
        conn = self.query_s3connection(error_level=error_level)
        try:
            bucket = conn.get_bucket(bucket_name)
        except Exception, e:
            self.log("upload_file_to_s3: Can't get bucket; %s!" % str(e), level=error_level)
            return
        bucket_key = bucket.get_key(key_name)

        # build metadata and headers
        if metadata is None:
            metadata = {}
        mimetype = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'
        metadata.update({
            'upload_time': int(time.time()),
            'filesize': os.path.getsize(file_path),
            'filename': file_name,
            'mimetype': mimetype,
        })
        headers = {
            'Content-Type': mimetype,
            'Content-Disposition': 'inline; filename="%s"' % (file_name),
        }

        with self.opened(file_path, "r") as (fd, err):
            if err:
                self.log("Can't open %s for reading!" % file_path, level=error_level)
                return
            if bucket_key:
                # if object exists in bucket then reset storage method
                timestamp = bucket_key.last_modified
                bucket_key.change_storage_class("STANDARD")

                # make sure the timestamp has been refreshed
                bucket_key = bucket.get_key(key_name)
                new_timestamp = bucket_key.last_modified
                if timestamp == new_timestamp:
                    # upload file should refreshing timestamp failed
                    bucket_key.update_metadata(metadata)
                    bucket_key.set_contents_from_file(fd, headers=headers)
                    bucket_key.set_acl('public-read')
                else:
                    # update metadata should refreshing timestamp succeeded
                    bucket_key = bucket.copy_key(
                        bucket_key.name, bucket_key.bucket.name,
                        bucket_key.name, metadata, preserve_acl=True,
                        headers=headers)
            else:
                # if object does not exist, upload it
                bucket_key = bucket.new_key(key_name)
                bucket_key.update_metadata(metadata)
                bucket_key.set_contents_from_file(fd, headers=headers)
                bucket_key.set_acl('public-read')

        # return the blob URL
        s3_base_url = self.config.get("s3_base_url", "http://" + bucket_name + ".s3.amazonaws.com")
        url = urlparse.urljoin(s3_base_url, key_name)
        return url
