# Copyright (c) 2020, DjaoDjin inc.
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

import copy, json, logging
from collections import OrderedDict

from django.dispatch import receiver
from django.template import loader, Template
from django.template.backends.django import DjangoTemplates
from django.test.signals import template_rendered
from django.test.utils import instrumented_test_render

from . import settings
from .compat import six
from .signals import template_loaded

try:
    from threading import local
except ImportError:
    #pylint: disable=import-error,no-name-in-module
    from django.utils._threading_local import local

_thread_locals = local() #pylint: disable=invalid-name

LOGGER = logging.getLogger(__name__)


# signals hook for Django Templates. Jinja2 templates are done through
# a custom Environment.
#pylint:disable=protected-access
for engine in loader._engine_list():
    if isinstance(engine, DjangoTemplates):
        if Template._render != instrumented_test_render:
            Template.original_render = Template._render
            Template._render = instrumented_test_render
            break

def _add_editable_styles_context(context=None, less_variables=None):
    if context is None:
        context = {}
    if 'editable_styles' not in context:
        if less_variables is None:
            less_variables = {}
        styles_context = copy.deepcopy(settings.BOOTSTRAP_EDITABLE_VARIABLES)
        for _, section_attributes in styles_context:
            for attribute in section_attributes:
                attribute['value'] = less_variables.get(
                    attribute['property'], attribute.get('default', ''))
        context['editable_styles'] = styles_context
    return context


@receiver(template_loaded, dispatch_uid="pages_template_loaded")
def _store_template_info(sender, **kwargs): #pylint: disable=unused-argument
    template = kwargs['template']
    if template.name in settings.TEMPLATES_BLACKLIST:
        # We don't show templates that cannot be edited.
        return
    if not hasattr(_thread_locals, 'templates'):
        _thread_locals.templates = OrderedDict()
    if not template.name in _thread_locals.templates:
        # For some reasons the Django/Jinja2 framework might load the same
        # templates multiple times.
        _thread_locals.templates.update({template.name:
            {"name": template.name, "index": len(_thread_locals.templates)}})

def enable_instrumentation():
    _thread_locals.templates = OrderedDict()
    template_loaded.connect(_store_template_info)
    template_rendered.connect(_store_template_info)

def disable_instrumentation():
    template_rendered.disconnect(_store_template_info)
    template_loaded.disconnect(_store_template_info)

def get_edition_tools_context_data():
    context = {}
    if hasattr(_thread_locals, 'templates'):
        context.update({'templates': json.dumps(
            list(six.itervalues(_thread_locals.templates)))})
    context = _add_editable_styles_context(context=context)
    return context
