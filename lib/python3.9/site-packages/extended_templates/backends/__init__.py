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

from importlib import import_module

from django.core.exceptions import ImproperlyConfigured
from django.template.loader import select_template

from .. import settings
from ..compat import six


def get_email_backend(connection=None):
    return _load_backend(settings.EMAILER_BACKEND)(connection=connection)


def _load_backend(path):
    dot_pos = path.rfind('.')
    module, attr = path[:dot_pos], path[dot_pos + 1:]
    try:
        mod = import_module(module)
    except ImportError as err:
        raise ImproperlyConfigured('Error importing emailer backend %s: "%s"'
            % (path, err))
    except ValueError:
        raise ImproperlyConfigured('Error importing emailer backend. '\
' Is EMAILER_BACKEND a correctly defined list or tuple?')
    try:
        cls = getattr(mod, attr)
    except AttributeError:
        raise ImproperlyConfigured('Module "%s" does not define a "%s" '\
' emailer backend' % (module, attr))
    return cls


class TemplateEmailBackend(object):

    def __init__(self, connection=None):
        self.connection = connection

    #pylint: disable=invalid-name,too-many-arguments
    def send(self, recipients, template, context=None,
             from_email=None, bcc=None, cc=None, reply_to=None,
             attachments=None, fail_silently=False):
        # avoid import loop in utils.py
        from extended_templates.utils import get_template
        if not from_email:
            from_email = settings.DEFAULT_FROM_EMAIL

        if isinstance(template, (list, tuple)):
            tmpl = select_template(template)
        elif isinstance(template, six.string_types):
            tmpl = get_template(template)
        else:
            tmpl = template
        tmpl.send(recipients, context,
            from_email=from_email, bcc=bcc, cc=cc, reply_to=reply_to,
            attachments=attachments, connection=self.connection,
            fail_silently=fail_silently)
