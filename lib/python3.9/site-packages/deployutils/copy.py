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
from __future__ import unicode_literals

import logging, os, subprocess, zipfile
import requests

from .filesys import list_local


LOGGER = logging.getLogger(__name__)


def _resources_files(abs_paths=False):
    remotes = []
    ignores = ['*~', '.DS_Store']
    with open('.gitignore') as gitignore:
        for line in gitignore.readlines():
            if line.startswith('#'):
                # ignore comment lines
                continue
            if abs_paths:
                pathname = os.path.join(os.getcwd(), line.strip())
            else:
                pathname = line.strip()
            if pathname.endswith(os.sep):
                # os.path.basename will not work as expected if pathname
                # ends with a '/'.
                pathname = pathname[:-1]
                ignores += [pathname]
            elif (os.path.exists(pathname)
                and not os.path.basename(pathname).startswith('.')):
                remotes += [pathname]
            else:
                ignores += [pathname]
    return remotes, ignores


def download(remote_location, remotes=None, prefix="", dry_run=False):
    """
    Download resources from a stage server.
    """
    if remotes is None:
        remotes, _ = _resources_files(
            abs_paths=remote_location.startswith('s3://'))
    if remote_location.startswith('s3://'):
        from .s3 import S3Backend
        backend = S3Backend(remote_location, dry_run=dry_run)
        backend.download(list_local(remotes, prefix), prefix)
    else:
        dest_root = '.'
        shell_command([
                '/usr/bin/rsync',
                '-thrRvz', '--rsync-path', '/usr/bin/rsync',
                '%s/./' % remote_location, dest_root], dry_run=dry_run)


def download_theme(args, base_url, api_key, prefix=None):
    """
    Downloads a project theme.
    """
    api_themes_url = base_url + '/api/themes/'
    resp = requests.get(api_themes_url, auth=(api_key, ""))
    LOGGER.info("GET %s returns %d %s",
        api_themes_url, resp.status_code, resp.text)


def shell_command(cmd, dry_run=False):
    """
    Run a shell command.
    """
    if cmd[0] == '/usr/bin/rsync':
        if dry_run:
            cmd = [cmd[0], '-n'] + cmd[1:]
        LOGGER.info('run: %s', ' '.join(cmd))
        subprocess.check_call(cmd)
    else:
        LOGGER.info('run: %s', ' '.join(cmd))
        if not dry_run:
            subprocess.check_call(cmd)


def upload(remote_location, remotes=None, ignores=None,
           static_root="/static/", prefix="", dry_run=False):
    # pylint:disable=too-many-arguments
    """
    Upload resources to a stage server.
    """
    if remotes is None:
        remotes, ignores = _resources_files(
            abs_paths=remote_location.startswith('s3://'))
    if remote_location.startswith('s3://'):
        from deployutils.s3 import S3Backend
        backend = S3Backend(remote_location,
            static_root=static_root, dry_run=dry_run)
        backend.upload(list_local(remotes, prefix), prefix)
    else:
        excludes = []
        if ignores:
            for ignore in ignores:
                excludes += ['--exclude', ignore]
        # -O omit to set mod times on directories to avoid permissions error.
        shell_command(['/usr/bin/rsync']
            + excludes + ['-pOthrRvz', '--rsync-path', '/usr/bin/rsync']
            + remotes + [remote_location], dry_run=dry_run)


def upload_theme(args, base_url, api_key, prefix=None):
    """
    Uploads a new theme for a project.
    """
    def zipdir(path, ziph, prefix=None):
        # ziph is zipfile handle
        for root, dirs, files in os.walk(path):
            for filename in files:
                if not filename.endswith('~'):
                    pathname = os.path.join(root, filename)
                    if prefix:
                        arcname = os.path.join(prefix, pathname)
                    else:
                        arcname = pathname
                    ziph.write(pathname, arcname)

    if not args:
        raise ValueError(
            "A single zip file or a list of directories must be present")

    src = args[0]
    if os.path.isfile(src) and zipfile.is_zipfile(src):
        if len(args) != 1:
            raise ValueError(
                "You should specify a single zip file only.")
        zip_filename = src
    elif os.path.isdir(src):
        if prefix:
            zip_filename = "%s.zip" % prefix
        else:
            zip_filename = "%s.zip" % os.path.basename(os.path.normpath(src))
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for src in args:
                base_name = os.path.abspath(os.path.normpath(src))
                root_dir = os.path.dirname(base_name)
                base_dir = os.path.basename(base_name)
                cwd = os.getcwd()
                os.chdir(root_dir)
                zipdir(base_dir, zipf, prefix=prefix)
                os.chdir(cwd)
    else:
        raise ValueError("%s is neither a single zip nor a list of directoies"
            % str(args))
    api_themes_url = base_url + '/api/themes/'
    files = {'file': (os.path.basename(zip_filename), open(zip_filename, 'rb'))}
    resp = requests.post(api_themes_url, files=files, auth=(api_key, ""))
    LOGGER.info("POST %s returns %d %s",
        api_themes_url, resp.status_code, resp.text)
