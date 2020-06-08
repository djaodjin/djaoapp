# Copyright (c) 2019, DjaoDjin inc.
# see LICENSE

#pylint: disable=no-name-in-module,unused-import
from functools import WRAPPER_ASSIGNMENTS
import six

#pylint:disable=no-name-in-module,import-error
from six.moves.urllib.parse import urljoin, urlparse, urlunparse
from six import StringIO

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
    from django.core.context_processors import csrf #pylint:disable=import-error

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
