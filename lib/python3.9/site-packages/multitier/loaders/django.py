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
from __future__ import absolute_import

import logging

import django
from django.conf import settings
from django.template.loaders.filesystem import Loader as FilesystemLoader
from django.utils._os import safe_join

from multitier.thread_locals import get_current_site
from multitier.compat import Origin


LOGGER = logging.getLogger(__name__)


class Loader(FilesystemLoader):

    def __init__(self, engine):
        super(Loader, self).__init__(engine)
        self.encoding = 'utf-8'

    def searchpath(self, template_dirs=None):
        if not template_dirs:
            try:
                template_dirs = self.get_dirs() #pylint:disable=no-member
            except AttributeError: # django < 1.8
                template_dirs = settings.TEMPLATE_DIRS
        current_site = get_current_site()
        if current_site:
            loader_template_dirs = []
            for template_dir in current_site.get_template_dirs():
                loader_template_dirs.append(safe_join(template_dir, 'django'))
                loader_template_dirs.append(template_dir)
            template_dirs = loader_template_dirs + list(template_dirs)
        return template_dirs

    def get_template_sources(self, template_name, template_dirs=None):
        try:
            for template_dir in self.searchpath(template_dirs=template_dirs):
                try:
                    template_path = safe_join(template_dir, template_name)
                    if django.VERSION[0] <= 1 and django.VERSION[1] < 9:
                        yield template_path
                    else:
                        yield Origin(
                            name=template_path,
                            template_name=template_name,
                            loader=self)
                except UnicodeDecodeError:
                    # The template dir name was a bytestring that wasn't
                    # valid UTF-8.
                    raise
                except ValueError:
                    # The joined path was located outside
                    # of this particular template_dir (it might be
                    # inside another one, so this isn't fatal).
                    pass

        except AttributeError as attr_err:
            # Something bad appended. We don't even have a request.
            # The middleware might be misconfigured.
            LOGGER.warning(
                "%s, your middleware might be misconfigured.", attr_err)
