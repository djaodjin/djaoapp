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

import hashlib, os

from django.conf import settings as django_settings

from . import ResourceCommand


class Command(ResourceCommand):
    help = "Rename all .mp4 resources to _sha1_.mp4"

    def handle(self, *args, **options):
        ResourceCommand.handle(self, *args, **options)
        cryptic_media(django_settings.MEDIA_ROOT)


def cryptic_media(rootdir):
    for filename in os.listdir(rootdir):
        pathname = os.path.join(rootdir, filename)
        if os.path.isdir(pathname):
            cryptic_media(pathname)
        else:
            parts = os.path.splitext(os.path.basename(pathname))
            if parts:
                ext = parts[-1]
                if ext in ['.mp4']:
                    dirname = os.path.dirname(pathname)
                    basename = ' '.join(parts[:-1])
                    cryptic_name = os.path.join(dirname,
                        '%s%s' % (hashlib.sha1(basename).hexdigest(), ext))
                    os.rename(pathname, cryptic_name)
