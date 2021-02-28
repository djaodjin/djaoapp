# Copyright (c) 2017, DjaoDjin inc.
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

from functools import wraps

from django.template.response import TemplateResponse
from django.utils.decorators import available_attrs

from .locals import (enable_instrumentation, disable_instrumentation,
    get_edition_tools_context_data)
from .views.pages import inject_edition_tools as _inject_edition_tools

def inject_edition_tools(function=None):
    """
    Inject the edition tools into the HTML response.
    """
    def decorator(view_func):
        @wraps(view_func, assigned=available_attrs(view_func))
        def _wrapped_view(request, *args, **kwargs):
            enable_instrumentation()
            response = view_func(request, *args, **kwargs)
            disable_instrumentation()
            if isinstance(response, TemplateResponse):
                # We could use ``SingleTemplateResponse`` to catch both
                # django and restframework responses. Unfortunately
                # the content_type on restframework responses is set
                # very late (render), while at the same time django
                # defaults it to text/html until then.
                response.render()
                soup = _inject_edition_tools(response, request,
                    context=get_edition_tools_context_data())
                if soup:
                    # str(soup) instead of soup.prettify() to avoid
                    # trailing whitespace on a reformatted HTML textarea
                    response.content = str(soup)
            return response
        return _wrapped_view

    if function:
        return decorator(function)
    return decorator
