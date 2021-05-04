# Copyright (c) 2021, DjaoDjin inc.
# see LICENSE

#pylint: disable=no-name-in-module,unused-import,import-error,bad-except-order
#pylint: disable=invalid-name,unused-argument
from functools import WRAPPER_ASSIGNMENTS
import six

from six.moves.urllib.parse import urljoin, urlparse, urlunparse
from six import StringIO

try:
    from django.urls import URLPattern, URLResolver
except ImportError:
    from django.urls import (RegexURLPattern as URLPattern,
        RegexURLResolver as URLResolver)


def get_original_route(urlpat):
    if hasattr(urlpat, 'pattern'):
        # Django 2.0
        return str(urlpat.pattern)
    # Django < 2.0
    return urlpat.regex.pattern


try:
    from django.utils.decorators import available_attrs
except ImportError: # django < 3.0
    def available_attrs(fn):
        return WRAPPER_ASSIGNMENTS

try:
    from django.utils.encoding import python_2_unicode_compatible
except ImportError: # django < 3.0
    python_2_unicode_compatible = six.python_2_unicode_compatible


try:
    from django.template.context_processors import csrf
except ImportError: # django < 1.8
    from django.core.context_processors import csrf

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


def is_authenticated(request):
    if hasattr(request, 'user'):
        if callable(request.user.is_authenticated):
            return request.user.is_authenticated()
        return request.user.is_authenticated
    return False
