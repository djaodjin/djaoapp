# Copyright (c) 2018, Djaodjin Inc.
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

from __future__ import unicode_literals

import logging, re, subprocess, io, warnings

from bs4 import BeautifulSoup
from django.conf import settings as django_settings
from django.core.exceptions import ImproperlyConfigured
from django.template import TemplateDoesNotExist
from django.template.exceptions import TemplateSyntaxError
from django.template.response import TemplateResponse
from django.utils.module_loading import import_string
from django.utils.functional import cached_property
import weasyprint

from .. import settings
from ..compat import BaseEngine, _dirs_undefined, RemovedInDjango110Warning, six
from ..helpers import build_absolute_uri


LOGGER = logging.getLogger(__name__)


class PdfTemplateResponse(TemplateResponse):
    """
    Response as PDF content.
    """

    #pylint:disable=too-many-arguments
    def __init__(self, request, template, context=None, content_type=None,
                 status=None, **kwargs):
        # Django 1.9 added (charset=None, using=None) to the prototype.
        # Django 1.10 removed (current_app=None)  to the prototype.
        # We donot declare them explicitely but through **kwargs instead
        # so that our prototype is compatible with from Django 1.7
        # through to Django 1.10.
        super(PdfTemplateResponse, self).__init__(request, template,
            context=context, content_type='application/pdf', status=status,
            **kwargs)

    @property
    def rendered_content(self):
        """
        Converts the HTML content generated from the template
        as a Pdf document on the fly.
        """
        html_content = super(PdfTemplateResponse, self).rendered_content
        soup = BeautifulSoup(html_content.encode('utf-8'), 'html.parser')
        for lnk in soup.find_all('a'):
            href = lnk.get('href')
            if href and href.startswith('/'):
                lnk['href'] = build_absolute_uri(self._request, href)
        html_content = soup.prettify()
        cstr = io.BytesIO()
        try:
            doc = weasyprint.HTML(string=html_content)
            doc.write_pdf(cstr)
        except RuntimeError as _:
            raise
        return cstr.getvalue()


class PdfTemplateError(Exception):
    pass


class PdfEngine(BaseEngine):
    #pylint: disable=no-member

    app_dirname = 'pdf'

    def __init__(self, params):
        params = params.copy()
        options = params.pop('OPTIONS').copy()
        super(PdfEngine, self).__init__(params)
        self.file_charset = options.get(
            'file_charset', django_settings.FILE_CHARSET)
        self.loaders = options.get('loaders', [])

    # This is an ugly way to add the search paths for .pdf template files.
    @cached_property
    def template_loaders(self):
        return self.get_template_loaders(self.loaders)

    def get_template_loaders(self, template_loaders):
        loaders = []
        for loader in template_loaders:
            if isinstance(loader, (tuple, list)):
                args = list(loader[1:])
                loader = loader[0]
            else:
                args = []
            if isinstance(loader, six.string_types):
                loader_class = import_string(loader)
                if getattr(loader_class, '_accepts_engine_in_init', False):
                    args.insert(0, self)
                loader = loader_class(self, *args)
                if loader is not None:
                    loaders.append(loader)
            else:
                raise ImproperlyConfigured(
                 "Invalid value in template loaders configuration: %r" % loader)
        return loaders

    def find_template(self, template_name, dirs=None, skip=None):
        tried = []
#        if dirs is None:
#            dirs = self.dirs
#        for search_dir in dirs:

        for loader in self.template_loaders:
            if hasattr(loader, 'get_contents'):
                # From Django 1.9, this is the code that should be executed.
                for origin in loader.get_template_sources(
                        template_name, template_dirs=dirs):
                    if skip is not None and origin in skip:
                        tried.append((origin, 'Skipped'))
                        continue
                    try:
                        contents = loader.get_contents(origin)
                    except TemplateDoesNotExist:
                        tried.append((origin, 'Source does not exist'))
                        continue
                    else:
                        template = Template(
                            contents, origin, origin.template_name)
                        return template, template.origin
            else:
                # This code is there to support Django 1.8 only.
                try:
                    source, template_path = loader.load_template_source(
                        template_name, template_dirs=dirs)
                    origin = self.make_origin(
                        template_path, loader.load_template_source,
                        template_name, dirs)
                    template = Template(source, origin, template_path)
                    return template, template.origin
                except TemplateDoesNotExist:
                    pass
        raise TemplateDoesNotExist(template_name, tried=tried)

    def from_string(self, template_code):
        raise TemplateSyntaxError(
            "The from_string() method is not implemented")

    def get_template(self, template_name, dirs=_dirs_undefined):
        #pylint:disable=arguments-differ
        if template_name and template_name.endswith('.pdf'):
            if dirs is _dirs_undefined:
                dirs = None
            else:
                warnings.warn(
                    "The dirs argument of get_template is deprecated.",
                    RemovedInDjango110Warning, stacklevel=2)

            template, origin = self.find_template(template_name, dirs)
            if not hasattr(template, 'render'):
                # template needs to be compiled
                template = Template(template, origin, template_name)
            return template
        raise TemplateDoesNotExist(template_name)


class Template(object):
    """
    Fills a PDF template
    """

    def __init__(self, template_string, origin=None, name=None):
        #pylint:disable=unused-argument
        self.name = name
        self.origin = origin

    def render(self, context=None, request=None):
        #pylint:disable=unused-argument
        if self.origin:
            template_path = self.origin.name
        else:
            template_path = self.name
        output, err = self.fill_form(context, template_path)
        if err:
            raise PdfTemplateError(err)
        return output

    @staticmethod
    def fill_form(fields, src, pdf_flatform_bin=None):
        if pdf_flatform_bin is None:
            assert hasattr(settings, 'PDF_FLATFORM_BIN'), "PDF generation"\
" requires podofo-flatform (https://github.com/djaodjin/podofo-flatform)."\
" Edit your PDF_FLATFORM_BIN settings accordingly."
            pdf_flatform_bin = settings.PDF_FLATFORM_BIN

        cmd = [pdf_flatform_bin]
        for key, value in six.iteritems(fields):
            if not isinstance(value, six.string_types):
                value = str(value)
            # We substitute non-standard whitespaces here because
            # they interact poorly with the Python utf-8 encoder.
            value = re.sub(r"\s", ' ', value)
            if len(value) > 0:
                # We don't want to end-up with ``--fill key=``
                cmd += ["--fill", '%s=%s' % (key, value)]
        cmd += [src, '-']

        cmdline = cmd[0]
        for param in cmd[1:]:
            try:
                key, value = param.split('=')
                if any(char in value for char in [' ', ';']):
                    value = '"%s"' % value
                cmdline += " %s=%s" % (key, value)
            except ValueError:
                cmdline += " " + param
        LOGGER.info("RUN: %s", ' '.join(cmd))

        return subprocess.check_output(cmd), None
