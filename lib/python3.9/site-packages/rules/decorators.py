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

"""
Decorators to grant access to an URL based on a dynamic set of rules.
"""

import logging

from functools import wraps
from django.shortcuts import get_object_or_404

from .compat import available_attrs
from .perms import NoRuleMatch, check_matched, redirect_or_denied
from .utils import get_app_model, get_current_app


LOGGER = logging.getLogger(__name__)


def fail_rule(request, app=None):
    """
    Custom rule
    """
    if not app:
        app = get_current_app()
    try:
        redirect, _, _ = check_matched(request, app)
    except NoRuleMatch as _:
        redirect = True
    return redirect


def requires_permissions(function=None, app_url_kwarg='app'):
    """
    Decorator for views that checks that the request is allowed
    to go through based on a set of rules.
    """
    def decorator(view_func):
        @wraps(view_func, assigned=available_attrs(view_func))
        def _wrapped_view(request, *args, **kwargs):
            if app_url_kwarg in kwargs:
                app = get_object_or_404(
                    get_app_model(), slug=kwargs.get(app_url_kwarg))
            else:
                app = None
            redirect = fail_rule(request, app=app)
            if redirect:
                return redirect_or_denied(request, redirect)
            return view_func(request, *args, **kwargs)
        return _wrapped_view

    if function:
        return decorator(function)
    return decorator
