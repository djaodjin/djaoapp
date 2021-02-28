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

from django import template
from django.templatetags.static import StaticNode

from ..compat import urljoin
from ..mixins import build_absolute_uri
from ..thread_locals import get_current_site


register = template.Library()


class MultitierStaticNode(StaticNode):

    def url(self, context):
        path = super(MultitierStaticNode, self).url(context)
        return site_prefixed(path)


@register.tag('static')
def do_static(parser, token):
    """
    A template tag that returns the URL to a file
    using a ``multitier.Site``

    Usage::

        {% static path [as varname] %}

    Examples::

        {% static "myapp/css/base.css" %}
        {% static variable_with_path %}
        {% static "myapp/css/base.css" as admin_base_css %}
        {% static variable_with_path as varname %}

    """
    return MultitierStaticNode.handle_token(parser, token)


@register.filter()
def absolute_uri(request):
    return build_absolute_uri(request)


@register.filter()
def asset(path):
    """
    Adds the appropriate url or path prefix.

    While ``{% static path [as varname] %}`` would work in the context
    of Django templates, ``{{ path|asset }}`` works in both Django and Jinja2
    templates.
    """
    return site_prefixed(path)


@register.filter()
def site_prefixed(path):
    if path is None:
        path = ''
    site = get_current_site()
    if site and site.path_prefix:
        path_prefix = '/%s' % site.path_prefix
    else:
        path_prefix = ''
    if path:
        # We have an actual path instead of generating a prefix that will
        # be placed in front of static urls (ie. {{'pricing'|site_prefixed}}
        # insted of {{''|site_prefixed}}{{ASSET_URL}}).
        path_prefix += '/'
        if path.startswith('/'):
            path = path[1:]
    return urljoin(path_prefix, path)
