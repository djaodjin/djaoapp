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
from __future__ import absolute_import

import re

from django.core.exceptions import ImproperlyConfigured
from django.urls import base
from django.utils.datastructures import MultiValueDict
from django.utils.regex_helper import normalize

from .compat import (RegexURLResolver as DjangoRegexURLResolver,
    RegexURLPattern as DjangoRegexURLPattern, lru_cache, six)
from .thread_locals import get_current_site


class SitePrefixPattern(object):

    def __init__(self):
        self.converters = {}

    @staticmethod
    def _get_path_prefix():
        path_prefix = ""
        current_site = get_current_site()
        if current_site and current_site.path_prefix:
            path_prefix = "%s/" % current_site.path_prefix
        return path_prefix

    @property
    def regex(self):
        # This is only used by reverse() and cached in _reverse_dict.
        return re.compile(self._get_path_prefix(), re.UNICODE)

    def match(self, path):
        path_prefix = self._get_path_prefix()
        if path.startswith(path_prefix):
            return path[len(path_prefix):], (), {}
        return None

    def check(self):
        return []

    def describe(self):
        return "'{}'".format(self)

    def __str__(self):
        return self._get_path_prefix()


class BaseRegexURLResolver(DjangoRegexURLResolver):
    """
    A URL resolver that always matches the active organization code
    as URL prefix.
    """
    def __init__(self, regex, urlconf_name, *args, **kwargs):
        super(BaseRegexURLResolver, self).__init__(
            regex, urlconf_name, *args, **kwargs)

    @staticmethod
    def _get_path_prefix():
        path_prefix = "_"
        current_site = get_current_site()
        if current_site and current_site.path_prefix:
            path_prefix = current_site.path_prefix
        return path_prefix

    # Implementation Note:
    # Copy/Pasted `RegexURLResolver._populate` here because that was the only
    # way to override `language_code = get_language()` to use a dynamic path
    # prefix `path_prefix = self._get_path_prefix()`.
    def _populate(self):
        # Short-circuit if called recursively in this thread to prevent
        # infinite recursion. Concurrent threads may call this at the same
        # time and will need to continue, so set 'populating' on a
        # thread-local variable.
        #pylint:disable=protected-access,too-many-locals
        if getattr(self._local, 'populating', False):
            return
        try:
            self._local.populating = True
            lookups = MultiValueDict()
            namespaces = {}
            apps = {}
            path_prefix = self._get_path_prefix()
            for url_pattern in reversed(self.url_patterns):
                if isinstance(url_pattern, DjangoRegexURLPattern):
                    self._callback_strs.add(url_pattern.lookup_str)
                # could be RegexURLPattern.regex or RegexURLResolver.regex here.
                p_pattern = url_pattern.regex.pattern
                if p_pattern.startswith('^'):
                    p_pattern = p_pattern[1:]
                if isinstance(url_pattern, DjangoRegexURLResolver):
                    if url_pattern.namespace:
                        namespaces[url_pattern.namespace] = (
                            p_pattern, url_pattern)
                        if url_pattern.app_name:
                            apps.setdefault(
                                url_pattern.app_name, []).append(
                                    url_pattern.namespace)
                    else:
                        parent_pat = url_pattern.regex.pattern
                        for name in url_pattern.reverse_dict:
                            for _, pat, defaults \
                                in url_pattern.reverse_dict.getlist(name):
                                new_matches = normalize(parent_pat + pat)
                                lookups.appendlist(
                                    name,
                                    (
                                        new_matches,
                                        p_pattern + pat,
                                        dict(defaults,
                                             **url_pattern.default_kwargs),
                                    )
                                )
                        for namespace, (prefix, sub_pattern) \
                            in url_pattern.namespace_dict.items():
                            namespaces[namespace] = (
                                p_pattern + prefix, sub_pattern)
                        for app_name, namespace_list in \
                                url_pattern.app_dict.items():
                            apps.setdefault(app_name, []).extend(namespace_list)
                    if not getattr(url_pattern._local, 'populating', False):
                        url_pattern._populate()
                    self._callback_strs.update(url_pattern._callback_strs)
                else:
                    bits = normalize(p_pattern)
                    lookups.appendlist(url_pattern.callback, (
                        bits, p_pattern, url_pattern.default_args))
                    if url_pattern.name is not None:
                        lookups.appendlist(url_pattern.name, (
                            bits, p_pattern, url_pattern.default_args))
            self._reverse_dict[path_prefix] = lookups
            self._namespace_dict[path_prefix] = namespaces
            self._app_dict[path_prefix] = apps
            self._populated = True
        finally:
            self._local.populating = False

    @property
    def reverse_dict(self):
        path_prefix = self._get_path_prefix()
        if path_prefix not in self._reverse_dict:
            self._populate()
        return self._reverse_dict[path_prefix]

    @property
    def namespace_dict(self):
        path_prefix = self._get_path_prefix()
        if path_prefix not in self._namespace_dict:
            self._populate()
        return self._namespace_dict[path_prefix]

    @property
    def app_dict(self):
        path_prefix = self._get_path_prefix()
        if path_prefix not in self._app_dict:
            self._populate()
        return self._app_dict[path_prefix]


try:

    from .urlresolvers_py3_django2 import RegexURLResolver

except (ImportError, SyntaxError): # <= Django2, Python 2

    class RegexURLResolver(BaseRegexURLResolver):
        pass

except ModuleNotFoundError: # <= Django2, Python 3

    class RegexURLResolver(BaseRegexURLResolver):
        pass


class SiteRegexURLResolver(RegexURLResolver):
    """
    A URL resolver that always matches the active organization code
    as URL prefix.
    """
    def __init__(self, regex, urlconf_name, *args, **kwargs):
        super(SiteRegexURLResolver, self).__init__(
            regex, urlconf_name, *args, **kwargs)

    @property
    def regex(self):
        path_prefix = self._get_path_prefix()
        if path_prefix != '_':
            # site will be None when 'manage.py show_urls' is invoked.
            return re.compile('^%s/' % path_prefix, re.UNICODE)
        return re.compile('^', re.UNICODE)


def site_patterns(*args):
    """
    Adds the live organization prefix to every URL pattern within this
    function. This may only be used in the root URLconf, not in an included
    URLconf.
    """
    pattern_list = args
    return [SiteRegexURLResolver(SitePrefixPattern(), pattern_list)]


try:
    from django.urls.resolvers import RegexPattern

    @lru_cache(maxsize=None)
    def get_resolver(urlconf=None):
        if urlconf is None:
            from django.conf import settings
            urlconf = settings.ROOT_URLCONF
        return RegexURLResolver(RegexPattern(r'^/'), urlconf)

    def url_sites(regex, view, kwargs=None, name=None, prefix=''):
        #pylint:disable=unused-argument
        if not view:
            raise ImproperlyConfigured(
                'Empty URL pattern view name not permitted (for pattern %r)'
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
        elif callable(view):
            pattern = RegexPattern(regex, name=name, is_endpoint=True)
            return DjangoRegexURLPattern(pattern, view, kwargs, name)
        else:
            raise TypeError('view must be a callable or a list/tuple'\
                ' in the case of include().')

except ImportError:
    def url_sites(regex, view, kwargs=None, name=None, prefix='',
            pattern=DjangoRegexURLPattern, resolver=RegexURLResolver):
        """
        Modified `django.conf.urls.url` with allows to specify custom
        RegexURLPattern and RegexURLResolver classes.
        """
        #pylint:disable=too-many-arguments
        if isinstance(view, (list, tuple)):
            # For include(...) processing.
            return resolver(regex, view[0], kwargs, *view[1:])
        else:
            if isinstance(view, six.string_types):
                if not view:
                    raise ImproperlyConfigured('Empty URL pattern view'\
                        ' name not permitted (for pattern %r)' % regex)
                if prefix:
                    view = prefix + '.' + view
            return pattern(regex, view, kwargs, name)

    @lru_cache(maxsize=None)
    def get_resolver(urlconf=None):
        if urlconf is None:
            from django.conf import settings
            urlconf = settings.ROOT_URLCONF
        return RegexURLResolver(r'^/', urlconf)


# Severe monkey patching without which calling the top level resolver
# `_reverse_with_prefix` method is not updating caches for *path_prefix*.
base.get_resolver = get_resolver
