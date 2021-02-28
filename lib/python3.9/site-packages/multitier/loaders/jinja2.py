# Copyright (c) 2019, Djaodjin Inc.
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

import hashlib, logging, os

from django.utils._os import safe_join
import jinja2

from multitier.thread_locals import get_current_site


LOGGER = logging.getLogger(__name__)


class Loader(jinja2.FileSystemLoader):
    """
    Jinja2 loader.
    """
    def __init__(self, searchpath, encoding='utf-8', followlinks=False):
        super(Loader, self).__init__(
            searchpath, encoding=encoding, followlinks=followlinks)

    def get_template_dirs(self, template_dirs=None):
        if template_dirs is None:
            template_dirs = self.searchpath
        current_site = get_current_site()
        if current_site:
            loader_template_dirs = []
            for template_dir in current_site.get_template_dirs():
                loader_template_dirs.append(safe_join(template_dir, 'jinja2'))
                loader_template_dirs.append(template_dir)
            template_dirs = loader_template_dirs + list(template_dirs)
        return template_dirs


    def get_source(self, environment, template):
        pieces = jinja2.loaders.split_template_path(template)
        filename = None
        contents = None
        digest = None
        for searchpath in self.get_template_dirs():
            filename = os.path.join(searchpath, *pieces)
            if os.path.isfile(filename):
                LOGGER.debug("found template %s", filename)
                with open(filename, "rb") as template_file:
                    data = template_file.read()
                    digest = hashlib.sha1(data).hexdigest()
                    contents = data.decode(self.encoding)
                break
#            else:
#                LOGGER.debug("tried template %s", filename)
        if filename is not None and contents is not None:
            def uptodate():
                try:
                    with open(filename, "rb") as template_file:
                        file_digest = hashlib.sha1(
                            template_file.read()).hexdigest()
                        return file_digest == digest
                except OSError:
                    return False
            return contents, filename, uptodate
        raise jinja2.exceptions.TemplateNotFound(template)
