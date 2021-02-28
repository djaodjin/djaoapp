# Copyright (c) 2019, DjaoDjin inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED
# TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
# OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
# OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
# ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import logging, os, shutil, tempfile, zipfile
from io import BytesIO

from django.http import HttpResponse
from django.views.generic import TemplateView, View
from deployutils.apps.django.themes import package_theme

from .. import settings
from ..mixins import AccountMixin, ThemePackageMixin


LOGGER = logging.getLogger(__name__)


class ThemePackagesView(AccountMixin, TemplateView):

    template_name = "pages/theme.html"


class ThemePackageDownloadView(ThemePackageMixin, View):

    @staticmethod
    def get_template_dirs():
        return None

    @staticmethod
    def write_zipfile(zipf, dir_path, dir_option=""):
        for dirname, _, files in os.walk(dir_path):
            for filename in files:
                abs_file_path = os.path.join(
                    dirname, filename)
                rel_file_path = os.path.join(
                    dir_option,
                    abs_file_path.replace("%s/" % dir_path, ''))
                LOGGER.debug("zip %s as %s", abs_file_path, rel_file_path)
                zipf.write(abs_file_path, rel_file_path)
        return zipf

    def get(self, *args, **kwargs): #pylint:disable=unused-argument
        from_static_dir = self.get_statics_dir(self.theme)
        from_templates_dir = self.get_templates_dir(self.theme)

        content = BytesIO()
        build_dir = tempfile.mkdtemp(prefix="pages-")
        try:
            package_theme(self.theme, build_dir,
                excludes=settings.TEMPLATES_BLACKLIST,
                template_dirs=self.get_template_dirs())
            with zipfile.ZipFile(content, mode="w") as zipf:
                zipf = self.write_zipfile(zipf, from_static_dir,
                    os.path.join(self.theme, 'public'))
                zipf = self.write_zipfile(zipf,
                    os.path.join(build_dir, 'templates'),
                    os.path.join(self.theme, 'templates'))
                zipf = self.write_zipfile(zipf, from_templates_dir,
                    os.path.join(self.theme, 'templates'))
        finally:
            shutil.rmtree(build_dir)
        content.seek(0)

        resp = HttpResponse(content.read(), content_type='application/x-zip')
        resp['Content-Disposition'] = 'attachment; filename="{}"'.format(
                "%s.zip" % self.theme)
        return resp
