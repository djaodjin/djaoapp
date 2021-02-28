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
Decorates URLs with permission checks.

This module implements `url` and `include` functions that apply a list
of permission checks before calling the underlying view.

The content of this file is inspired from
https://github.com/mila/django-urldecorators.git and patches
that were made in https://github.com:smirolo/django-urldecorators.git
for Django 2.0.
"""
from __future__ import unicode_literals

import logging

from django.conf import urls
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.core.exceptions import ImproperlyConfigured
from functools import wraps

try:
    from django.urls.resolvers import URLPattern as DjangoRegexURLPattern
    from django.urls import URLResolver as DjangoRegexURLResolver
except ImportError: # Django<2.0
    from django.core.urlresolvers import (
        RegexURLPattern as DjangoRegexURLPattern,
        RegexURLResolver as DjangoRegexURLResolver
    )

from .compat import available_attrs, get_func_arg_names, six
from .perms import redirect_or_denied


__all__ = ['include', 'url']


LOGGER = logging.getLogger(__name__)


class DecoratorMixin(object):
    """
    A mixin which adds support for decorating all resolved views
    """
    def __init__(self, *args, **kwargs):
        super(DecoratorMixin, self).__init__(*args, **kwargs)
        self.redirects = []
        self.decorators = []

    def resolve(self, path):
        match = super(DecoratorMixin, self).resolve(path)
        if not match:
            return match
        match.func = self.apply_decorators(match.func)
        return match

    def apply_decorators(self, func):
        """
        Adds checks and decorators into the call sequence.
        """
        for decorator in self.decorators:
            func = decorator(func)

        def decorator(view_func, redirects=[]):
            @wraps(view_func, assigned=available_attrs(view_func))
            def _wrapped_view(request, *view_args, **view_kwargs):
                for fail_func in redirects:
                    # filter out URL keyword arguments which the fail_func
                    # does not accept.
                    kwargs = {}
                    for name in get_func_arg_names(fail_func):
                        value = view_kwargs.get(name)
                        if value is not None:
                            kwargs.update({name: value})
                    LOGGER.debug("calling %s(user=%s, kwargs=%s) ...",
                        fail_func.__name__, request.user, kwargs)
                    redirect = fail_func(request, **kwargs)
                    LOGGER.debug("calling %s(user=%s, kwargs=%s) => %s",
                        fail_func.__name__, request.user, kwargs, redirect)
                    if redirect:
                        return redirect_or_denied(request, redirect,
                            redirect_field_name=REDIRECT_FIELD_NAME)
                return view_func(request, *view_args, **view_kwargs)
            return _wrapped_view

        if func:
            return decorator(func, redirects=self.redirects)
        return decorator


class RegexURLPattern(DecoratorMixin, DjangoRegexURLPattern):
    """
    Django RegexURLPattern with support for decorating resolved views
    with permission checks.
    """


class RegexURLResolver(DecoratorMixin, DjangoRegexURLResolver):
    """
    Django RegexURLResolver with support for decorating resolved views
    with permission checks.
    """


def import_if_string(path):
    if not isinstance(path, six.string_types):
        return path
    try:
        dot = path.rindex('.')
    except ValueError:
        raise ImproperlyConfigured("%s isn't a valid module" % path)
    mod_name, obj_name = path[:dot], path[dot+1:]
    try:
        mod = __import__(mod_name, {}, {}, [''])
    except ImportError as err:
        raise ImproperlyConfigured('Error importing module %s: "%s"'
                                    % (mod_name, err))
    try:
        obj = getattr(mod, obj_name)
    except AttributeError:
        raise ImproperlyConfigured('Module "%s" does not define "%s"'
                                   % (mod_name, obj_name))
    return obj


def include(arg, namespace=None, app_name=None):
    try:
        #pylint:disable=unexpected-keyword-arg
        return urls.include(arg, namespace=namespace, app_name=app_name)
    except TypeError:
        # Django2.0 removed the `app_name` parameter and asks to pass
        # it inside a tuple (`arg`, `app_name`).
        pass
    if not isinstance(arg, tuple):
        arg = (arg, app_name)
    return urls.include(arg, namespace=namespace)


def url(regex, view, kwargs=None, name=None, prefix='',
        redirects=None, decorators=None):
    """
    Extended `django.conf.urls.url` with support to check checks before
    a view function is called.

    Example urls.py file:

        from rules.urldecorators import url, include

        urlpatterns = [
            url(r'^private/$', include('example.private.urls'),
                redirects=[rules.fail_authenticated]),
        ]
    """
    #pylint:disable=too-many-arguments
    if not redirects and not decorators:
        try:
            return urls.url(regex, view, kwargs, name)
        except TypeError:  # Django<1.10
            #pylint:disable=too-many-function-args
            return urls.url(regex, view, kwargs, name, prefix)
    rule = _url(regex, view, kwargs, name, prefix)
    rule.redirects = tuple([import_if_string(check)
        for check in redirects or []])
    rule.decorators = tuple([import_if_string(decorator)
        for decorator in reversed(decorators or [])])
    return rule

try:
    from django.urls.resolvers import RegexPattern

    def _url(regex, view, kwargs=None, name=None, prefix=''):
        #pylint:disable=unused-argument
        if not view:
            raise ImproperlyConfigured(
                "Empty URL pattern view name not permitted (for pattern %r)"
                % regex)
        if isinstance(view, (list, tuple)):
            # For include(...) processing.
            pattern = RegexPattern(regex, is_endpoint=False)
            urlconf_module, app_name, namespace = view
            return RegexURLResolver(
                pattern,
                urlconf_module,
                kwargs,
                app_name=app_name,
                namespace=namespace,
            )
        if callable(view):
            pattern = RegexPattern(regex, name=name, is_endpoint=True)
            return RegexURLPattern(pattern, view, kwargs, name)
        raise TypeError(
            "view must be a callable or a list/tuple in the case of include().")

except ImportError:
    def _url(regex, view, kwargs=None, name=None, prefix='',
             pattern=RegexURLPattern, resolver=RegexURLResolver):
        """
        Modified `django.conf.urls.url` with allows to specify custom
        RegexURLPattern and RegexURLResolver classes.
        """
        #pylint:disable=too-many-arguments
        if isinstance(view, (list, tuple)):
            # For include(...) processing.
            return resolver(regex, view[0], kwargs, *view[1:])
        if isinstance(view, six.string_types):
            if not view:
                raise ImproperlyConfigured(
                "Empty URL pattern view name not permitted (for pattern %r)"
                % regex)
            if prefix:
                view = prefix + '.' + view
        return pattern(regex, view, kwargs, name)
