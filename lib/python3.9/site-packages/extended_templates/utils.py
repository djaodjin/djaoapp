# Copyright (c) 2017, DjaoDjin inc.
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

import codecs, warnings

import django
from django.template import Template, loader

from .compat import _dirs_undefined, RemovedInDjango110Warning
from .backends.pdf import Template as PdfTemplate
from .backends.eml import Template as EmlTemplate


# The following was derived from code originally posted
# at https://gist.github.com/zyegfryed/918403

def get_template_from_string(source, origin=None, name=None):
    """
    Returns a compiled Template object for the given template code,
    handling template inheritance recursively.
    """
    # This function is deprecated in Django 1.8+
    if name and name.endswith('.eml'):
        return EmlTemplate(source, origin, name)
    if name and name.endswith('.pdf'):
        return PdfTemplate('pdf', origin, name)
    return Template(source, origin, name)


def make_origin(display_name, from_loader, name, dirs):
    # Always return an Origin object, because PdfTemplate need it to render
    # the PDF Form file.
    return loader.LoaderOrigin(display_name, from_loader, name, dirs)


def get_template(template_name, dirs=_dirs_undefined):
    """
    Returns a compiled Template object for the given template name,
    handling template inheritance recursively.
    """
    # Implementation Note:
    # If we do this earlier (i.e. when the module is imported), there
    # is a chance our hook gets overwritten somewhere depending on the
    # order in which the modules are imported.
    loader.get_template_from_string = get_template_from_string
    loader.make_origin = make_origin

    def fake_strict_errors(exception): #pylint: disable=unused-argument
        return ("", -1)

    if template_name.endswith('.pdf'):
        # HACK: Ignore UnicodeError, due to PDF file read
        codecs.register_error('strict', fake_strict_errors)

    if dirs is _dirs_undefined:
        template = loader.get_template(template_name)
    else:
        if django.VERSION[0] >= 1 and django.VERSION[1] >= 8:
            warnings.warn(
                "The dirs argument of get_template is deprecated.",
                RemovedInDjango110Warning, stacklevel=2)
        #pylint:disable=unexpected-keyword-arg
        template = loader.get_template(template_name, dirs=dirs)

    if template_name.endswith('.pdf'):
        # HACK: Ignore UnicodeError, due to PDF file read
        codecs.register_error('strict', codecs.strict_errors)

    return template
