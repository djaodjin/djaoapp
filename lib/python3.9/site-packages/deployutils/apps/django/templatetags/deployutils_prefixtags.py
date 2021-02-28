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

from django import template

from .. import settings
from ..compat import urljoin

register = template.Library()


@register.filter()
def asset(path):
    """
    *Mockup*: adds the appropriate url or path prefix.
    """
    return site_prefixed(path)


@register.filter()
def site_prefixed(path):
    """
    *Mockup*: adds the path prefix when required.
    """
    if path is None:
        path = ''
    path_prefix = ''
    if settings.DEBUG and hasattr(settings, 'APP_NAME'):
        candidate = '/%s' % settings.APP_NAME
        if not path.startswith(candidate):
            path_prefix = candidate
    if path:
        # We have an actual path instead of generating a prefix that will
        # be placed in front of static urls (ie. {{'pricing'|site_prefixed}}
        # insted of {{''|site_prefixed}}{{ASSET_URL}}).
        path_prefix += '/'
        if path.startswith('/'):
            path = path[1:]
    return urljoin(path_prefix, path)
