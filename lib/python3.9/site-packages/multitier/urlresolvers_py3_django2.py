# Copyright (c) 2019, Djaodjin Inc.
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


from django.urls.resolvers import URLPattern, URLResolver
from django.utils.datastructures import MultiValueDict
from django.utils.regex_helper import normalize


from .thread_locals import get_current_site


class RegexURLResolver(URLResolver):
    """
    A URL resolver that always matches the active organization code
    as URL prefix.
    """
    def __init__(self, regex, urlconf_name, *args, **kwargs):
        super(RegexURLResolver, self).__init__(
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
        if getattr(self._local, 'populating', False):
            return
        try:
            self._local.populating = True
            lookups = MultiValueDict()
            namespaces = {}
            apps = {}
            path_prefix = self._get_path_prefix()
            for url_pattern in reversed(self.url_patterns):
                p_pattern = url_pattern.pattern.regex.pattern
                if p_pattern.startswith('^'):
                    p_pattern = p_pattern[1:]
                if isinstance(url_pattern, URLPattern):
                    self._callback_strs.add(url_pattern.lookup_str)
                    bits = normalize(url_pattern.pattern.regex.pattern)
                    lookups.appendlist(
                        url_pattern.callback, (
                            bits, p_pattern,
                            url_pattern.default_args,
                            url_pattern.pattern.converters)
                    )
                    if url_pattern.name is not None:
                        lookups.appendlist(url_pattern.name, (
                            bits, p_pattern,
                            url_pattern.default_args,
                            url_pattern.pattern.converters)
                        )
                else:  # url_pattern is a URLResolver.
                    url_pattern._populate()
                    if url_pattern.app_name:
                        apps.setdefault(url_pattern.app_name, []).append(
                            url_pattern.namespace)
                        namespaces[url_pattern.namespace] = (
                            p_pattern, url_pattern)
                    else:
                        for name in url_pattern.reverse_dict:
                            for matches, pat, defaults, converters in \
                                    url_pattern.reverse_dict.getlist(name):
                                new_matches = normalize(p_pattern + pat)
                                lookups.appendlist(
                                    name,
                                    (
                                        new_matches,
                                        p_pattern + pat,
                                        {**defaults,
                                         **url_pattern.default_kwargs},
                                        {**self.pattern.converters,
                                         **url_pattern.pattern.converters,
                                         **converters}
                                    )
                                )
                        for namespace, (prefix, sub_pattern) in \
                                url_pattern.namespace_dict.items():
                            current_converters = \
                                url_pattern.pattern.converters
                            sub_pattern.pattern.converters.update(
                                current_converters)
                            namespaces[namespace] = (
                                p_pattern + prefix, sub_pattern)
                        for app_name, namespace_list in \
                                url_pattern.app_dict.items():
                            apps.setdefault(app_name, []).extend(
                                namespace_list)
                    self._callback_strs.update(url_pattern._callback_strs)
            self._namespace_dict[path_prefix] = namespaces
            self._app_dict[path_prefix] = apps
            self._reverse_dict[path_prefix] = lookups
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
