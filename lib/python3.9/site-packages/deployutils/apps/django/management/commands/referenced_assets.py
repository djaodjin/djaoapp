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

import os, subprocess, sys

from django.conf import settings as django_settings

from ... import settings
from .....copy import shell_command
from . import ResourceCommand, list_local


class Command(ResourceCommand):
    help = "For each asset, indicates if it can safely be said to be"\
" referenced in the code or not."

    def handle(self, *args, **options):
        ResourceCommand.handle(self, *args, **options)
        excludes = ['--exclude=%s' % item for item in ['.git']]
        prefix = settings.MULTITIER_RESOURCES_ROOT
        for key in list_local([django_settings.STATIC_ROOT], prefix):
            filename = key['Key']
            mtime = key['LastModified']
            basename = os.path.basename(filename)
            try:
                shell_command(
                  ['grep', '-rq'] + excludes + [basename, '.'])
                found = 'Y'
            except subprocess.CalledProcessError:
                found = 'N'
            sys.stdout.write('%s %s %s\n' % (found, mtime, filename))
