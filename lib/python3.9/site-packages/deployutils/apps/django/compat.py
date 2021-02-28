# Copyright (c) 2020, Djaodjin Inc.
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

#pylint: disable=unused-import,import-error,import-outside-toplevel
#pylint: disable=no-name-in-module,bad-except-order
import six
from six.moves.urllib.parse import urljoin, urlparse, urlunparse

try:
    from inspect import signature

    def check_signature(func, *args):
        sig = signature(func)
        sig.bind(*args)

except ImportError: # Python<3.3

    import inspect

    def check_signature(func, *args):
        inspect.getcallargs(func, *args) #pylint:disable=deprecated-method


try:
    from pip._internal.utils.misc import get_installed_distributions
except ImportError: # pip < 10
    from pip.utils import get_installed_distributions

try:
    from django.templatetags.static import do_static
except ImportError: # django < 2.1
    from django.contrib.staticfiles.templatetags import do_static

try:
    from django.utils.module_loading import import_string
except ImportError: # django < 1.7
    from django.utils.module_loading import import_by_path as import_string


try:
    from django.urls import NoReverseMatch, reverse, reverse_lazy
except ImportError: # <= Django 1.10, Python<3.6
    from django.core.urlresolvers import NoReverseMatch, reverse, reverse_lazy
except ModuleNotFoundError: #pylint:disable=undefined-variable
    # <= Django 1.10, Python>=3.6
    from django.core.urlresolvers import NoReverseMatch, reverse, reverse_lazy


try:
    from django.template.base import DebugLexer
except ImportError: # django < 1.8
    from django.template.debug import DebugLexer as BaseDebugLexer

    class DebugLexer(BaseDebugLexer):

        def __init__(self, template_string):
            super(DebugLexer, self).__init__(template_string, origin=None)

try:
    from django.template.base import TokenType
except ImportError: # django < 2.1
    from django.template.base import (TOKEN_TEXT, TOKEN_VAR, TOKEN_BLOCK,
        TOKEN_COMMENT)
    class TokenType(object):
        TEXT = TOKEN_TEXT
        VAR = TOKEN_VAR
        BLOCK = TOKEN_BLOCK
        COMMENT = TOKEN_COMMENT


class DjangoTemplate(object):

    @property
    def template_builtins(self):
        from django.template.base import builtins
        return builtins

    @property
    def template_libraries(self):
        from django.template.base import libraries
        return libraries


def get_html_engine():
    try:
        from django.template import engines
        from django.template.utils import InvalidTemplateEngineError
        try:
            try:
                builtins = engines['html'].engine.template_builtins
            except AttributeError:
                builtins = None
            return engines['html'], None, builtins
        except InvalidTemplateEngineError:
            engine = engines['django'].engine
            return engine, engine.template_libraries, engine.template_builtins
    except ImportError: # django < 1.8
        return DjangoTemplate()


try:
    from django.utils.deprecation import MiddlewareMixin
except ImportError: # django < 1.11
    class MiddlewareMixin(object):
        pass


def is_authenticated(request):
    if hasattr(request, 'user'):
        if callable(request.user.is_authenticated):
            return request.user.is_authenticated()
        return request.user.is_authenticated
    return False


def is_anonymous(request):
    if hasattr(request, 'user'):
        if callable(request.user.is_anonymous):
            return request.user.is_anonymous()
        return request.user.is_anonymous
    return False
