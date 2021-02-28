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

import codecs, logging, os, warnings

from bs4 import BeautifulSoup
import django
from django.core.mail import EmailMultiAlternatives
from django.template import engines
from django.utils.html import strip_tags
from django.utils._os import safe_join
from django.template import TemplateDoesNotExist
from premailer.premailer import (Premailer as BasePremailer,
    ExternalNotFoundError)

from .. import settings
from ..compat import (BaseEngine, _dirs_undefined, RemovedInDjango110Warning,
    urlparse)
from ..helpers import get_assets_dirs


LOGGER = logging.getLogger(__name__)


class Premailer(BasePremailer):
    """
    Special Premail that overrides _load_external in order to search multiple
    paths as well as prevent loading http resources.
    """

    def _load_external(self, url):
        parts = urlparse(url)
        rel_path = parts.path
        if url.startswith(settings.STATIC_URL):
            rel_path = rel_path[len(settings.STATIC_URL):]
        for base_path in get_assets_dirs():
            stylefile = safe_join(base_path, rel_path)
            if os.path.exists(stylefile):
                LOGGER.debug("looking for '%s' as '%s'... yes", url, stylefile)
                with codecs.open(stylefile, encoding='utf-8') as css_file:
                    css_body = css_file.read()
                return css_body
            LOGGER.debug("looking for '%s' as '%s'... no", url, stylefile)
        raise ExternalNotFoundError(url)


class EmlTemplateError(Exception):
    pass


class EmlEngine(BaseEngine):
    #pylint: disable=no-member

    app_dirname = 'eml'
    template_context_processors = tuple([])

    def __init__(self, params):
        params = params.copy()
        options = params.pop('OPTIONS').copy()
        self.engine = engines[options.get('engine', 'django')]
        super(EmlEngine, self).__init__(params)

    @staticmethod
    def get_templatetag_libraries(custom_libraries):
        """
        Return a collation of template tag libraries from installed
        applications and the supplied custom_libraries argument.
        """
        #pylint: disable=no-name-in-module,import-error
        from django.template.backends.django import get_installed_libraries
        libraries = get_installed_libraries()
        libraries.update(custom_libraries)
        return libraries

    def find_template(self, template_name, dirs=None, skip=None):
        tried = []
        for loader in self.template_loaders:
            if hasattr(loader, 'get_contents'):
                # From Django 1.9, this is the code that should be executed.
                try:
                    template = Template(loader.get_template(
                        template_name, template_dirs=dirs, skip=skip,
                    ))
                    return template, template.origin
                except TemplateDoesNotExist as err:
                    tried.extend(err.tried)
            else:
                # This code is there to support Django 1.8 only.
                from ..compat import DjangoTemplate
                try:
                    source, template_path = loader.load_template_source(
                        template_name, template_dirs=dirs)
                    origin = self.make_origin(
                        template_path, loader.load_template_source,
                        template_name, dirs)
                    template = Template(
                        DjangoTemplate(source, origin, template_path, self))
                    return template, template.origin
                except TemplateDoesNotExist:
                    pass
        raise TemplateDoesNotExist(template_name, tried=tried)

    def from_string(self, template_code):
        return Template(self.engine.from_string(template_code), engine=self)

    def get_template(self, template_name, dirs=_dirs_undefined):
        #pylint:disable=arguments-differ
        if template_name and template_name.endswith('.eml'):
            if dirs is _dirs_undefined:
                return Template(self.engine.get_template(
                    template_name), engine=self)
            if django.VERSION[0] >= 1 and django.VERSION[1] >= 8:
                warnings.warn(
                    "The dirs argument of get_template is deprecated.",
                    RemovedInDjango110Warning, stacklevel=2)
            return Template(self.engine.get_template(
                template_name, dirs=dirs), engine=self)
        raise TemplateDoesNotExist(template_name)


class Template(object):
    """
    Sends an email to a list of recipients (i.e. email addresses).
    """

    def __init__(self, template, engine=None):
        self.engine = engine
        self.template = template
        self.origin = template.origin
        if self.origin:
            self.name = self.origin.name

    def render(self, context=None, request=None):
        return self.template.render(context=context, request=request)

    #pylint: disable=invalid-name,too-many-arguments
    def _send(self, recipients, context, from_email=None, bcc=None, cc=None,
              reply_to=None, attachments=None,
              connection=None, fail_silently=False):
        #pylint: disable=too-many-locals
        subject = None
        plain_content = None
        headers = {'Reply-To': reply_to} if reply_to else None
        request = getattr(context, 'request', context.get('request', None))

        html_content = Premailer(
            self.render(context=context, request=request),
            include_star_selectors=True).transform()

        if not plain_content:
            # Defaults to content stripped of html tags
            if not html_content:
                raise EmlTemplateError(
                    "Template %s does not contain PLAIN nor HTML content."
                    % self.origin.name)
            soup = BeautifulSoup(html_content, 'html.parser')
            plain_content = strip_tags(soup.find('body').prettify())
            subject = soup.title.string.strip()

        # Create the email, attach the HTML version.
        if not subject:
            raise EmlTemplateError(
                "Template %s is missing a subject." % self.origin.name)

        # XXX implement inline attachments,
        #     reference: https://djangosnippets.org/snippets/3001/
        msg = EmailMultiAlternatives(
            subject, plain_content, from_email, recipients, bcc=bcc, cc=cc,
            attachments=attachments, headers=headers, connection=connection)
        if html_content:
            msg.attach_alternative(html_content, "text/html")
        msg.send(fail_silently=fail_silently)

    #pylint: disable=invalid-name,too-many-arguments
    def send(self, recipients, context,
             from_email=None, bcc=None, cc=None, reply_to=None,
             attachments=None, connection=None, fail_silently=False):
        #pylint: disable=no-member
        if not from_email:
            from_email = settings.DEFAULT_FROM_EMAIL

        if hasattr(context, 'template') and context.template is None:
            with context.bind_template(self):
                context.template_name = self.name
                return self._send(recipients, context, from_email=from_email,
                    bcc=bcc, cc=cc, reply_to=reply_to, attachments=attachments,
                    connection=connection, fail_silently=fail_silently)
        else:
            return self._send(recipients, context, from_email=from_email,
                bcc=bcc, cc=cc, reply_to=reply_to, attachments=attachments,
                connection=connection, fail_silently=fail_silently)
