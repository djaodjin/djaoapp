# Copyright (c) 2020, Djaodjin Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
# OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
# OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
# ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from __future__ import absolute_import

import datetime, logging, time, mimetypes, os

import boto3
#pylint:disable=import-error
from six.moves.urllib.parse import urlparse


LOGGER = logging.getLogger(__name__)


class S3Backend(object):

    def __init__(self, remote_location, static_root=None, dry_run=False):
        self.dry_run = dry_run
        self.static_root = static_root
        s3_resource = boto3.resource('s3')
        self.bucket = s3_resource.Bucket(urlparse(remote_location).netloc)
        # self.boto_datetime_format = '%a, %d %b %Y %H:%M:%S %Z'
        # XXX boto seems to have changed the datetime format returned
        #     when reading a S3 key.
        self.boto_datetime_format = '%Y-%m-%dT%H:%M:%S.%fZ'

    def list(self):
        """
        Returns a list of all files (recursively) present in a bucket
        with their timestamp.
        """
        return self.bucket.objects.all()

    def _index_by_key(self):
        index = {}
        for key in self.list():
            index[key.name] = key
        return index


    def _updated_s3_keys(self, local_files):
        # pylint: disable=too-many-locals
        uploads = []
        downloads = []
        s3_keys = self._index_by_key()
        for local_meta in local_files:
            if local_meta['Key'] in s3_keys:
                s3_key = s3_keys[local_meta['Key']]
                s3_datetime = datetime.datetime(*time.strptime(
                        s3_key.last_modified, self.boto_datetime_format)[0:6])
                local_datetime = datetime.datetime(*time.strptime(
                        local_meta['LastModified'],
                        '%a, %d %b %Y %H:%M:%S %Z')[0:6])
                if local_datetime > s3_datetime:
                    uploads += [local_meta['Key']]
                elif local_datetime < s3_datetime:
                    downloads += [local_meta['Key']]
            else:
                uploads += [local_meta['Key']]
        for s3_meta in s3_keys:
            if not s3_meta in local_files:
                downloads += [s3_meta]
        return downloads, uploads

    def download(self, local_files, prefix=''):
        downloads, _ = self._updated_s3_keys(local_files)
        for filename in downloads:
            headers = {}
            pathname = prefix + filename
            content_type = mimetypes.guess_type(pathname)[0]
            if content_type:
                headers['Content-Type'] = content_type
            if self.dry_run:
                dry_run = "(dry run) "
            else:
                dry_run = ""
            LOGGER.info("%sdownload %s to %s", dry_run, filename, pathname)
            if not self.dry_run:
                if not os.path.exists(os.path.dirname(pathname)):
                    os.makedirs(os.path.dirname(pathname))
                self.bucket.download_file(filename, pathname)

    def upload(self, local_files, prefix=""):
        _, uploads = self._updated_s3_keys(local_files)
        for filename in uploads:
            headers = {}
            pathname = prefix + filename
            content_type = mimetypes.guess_type(pathname)[0]
            if content_type:
                headers['Content-Type'] = content_type
            if self.dry_run:
                dry_run = "(dry run) "
            else:
                dry_run = ""
            policy = None
            if self.static_root and pathname.startswith(self.static_root):
                # By convention these are assets for browsers (css,js,etc)
                policy = 'public-read'
            LOGGER.info("%supload %s to %s%s", dry_run, pathname,
                "s3://%s/%s" % (self.bucket.name, filename),
                "(%s)" % policy if policy else "")
            extra_args = {}
            extra_args.update(headers)
            if policy:
                extra_args.update({'ACL': policy})
            if not self.dry_run:
                self.bucket.upload_file(pathname, filename,
                    ExtraArgs=extra_args)
