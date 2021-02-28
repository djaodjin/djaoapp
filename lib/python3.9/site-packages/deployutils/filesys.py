# Copyright (c) 2017, Djaodjin Inc.
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

import datetime, os

from pytz import utc


def fingerprint(dirnames, prefix=None, previous=[]):
    #pylint:disable=dangerous-default-value
    """
    Returns a list of paths available from *dirname*. When previous
    is specified, returns a list of additional files only.

    Example:
    [{ "Key": "abc.txt",
       "LastModified": "Mon, 05 Jan 2015 12:00:00 UTC"},
     { "Key": "def.txt",
       "LastModified": "Mon, 05 Jan 2015 12:00:001 UTC"},
    ]
    """
    results = []
    for dirname in dirnames:
        for filename in os.listdir(dirname):
            fullpath = os.path.join(dirname, filename)
            if os.path.isdir(fullpath):
                results += fingerprint(
                    [fullpath], prefix=filename, previous=previous)
            else:
                fullname = fullpath
                if prefix and fullname.startswith(prefix):
                    fullname = fullname[len(prefix):]
                found = False
                for prevpath in previous:
                    if fullname == prevpath['Key']:
                        found = True
                        break
                if not found:
                    mtime = datetime.datetime.fromtimestamp(
                        os.path.getmtime(fullpath), tz=utc)
                    results += [{"Key": fullname,
                                 "LastModified": mtime.strftime(
                                     '%a, %d %b %Y %H:%M:%S %Z')}]
    return results


def list_local(paths, prefix=None):
    """
    Returns a list of all files (recursively) present in a directory
    with their timestamp.

    Example:
    [{ "Key": "abc.txt",
       "LastModified": "Mon, 05 Jan 2015 12:00:00 UTC"},
     { "Key": "def.txt",
       "LastModified": "Mon, 05 Jan 2015 12:00:001 UTC"},
    ]
    """
    results = []
    for path in paths:
        if os.path.isdir(path):
            for filename in os.listdir(path):
                fullpath = os.path.join(path, filename)
                if os.path.isdir(fullpath):
                    results += list_local([fullpath], prefix)
                else:
                    fullname = fullpath
                    if prefix and fullname.startswith(prefix):
                        fullname = fullname[len(prefix):]
                    mtime = datetime.datetime.fromtimestamp(
                        os.path.getmtime(fullpath), tz=utc)
                    results += [{"Key": fullname,
                        "LastModified": mtime.strftime(
                                '%a, %d %b %Y %H:%M:%S %Z')}]
        else:
            fullpath = path
            fullname = fullpath
            if prefix and fullname.startswith(prefix):
                fullname = fullname[len(prefix):]
            mtime = datetime.datetime.fromtimestamp(
                os.path.getmtime(fullpath), tz=utc)
            results += [{"Key": fullname,
                "LastModified": mtime.strftime(
                        '%a, %d %b %Y %H:%M:%S %Z')}]
    return results
