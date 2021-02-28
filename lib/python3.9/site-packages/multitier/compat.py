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

#pylint: disable=unused-import
import six

#pylint:disable=no-name-in-module,import-error
from six.moves.urllib.parse import urlparse, urlunparse, urljoin

try:
  from functools import lru_cache
except ImportError: # python < 3
  from django.utils.lru_cache import lru_cache

try:
    from django.utils.encoding import python_2_unicode_compatible
except ImportError: # django < 3.0
    python_2_unicode_compatible = six.python_2_unicode_compatible

try:
    from django.urls import (NoReverseMatch, URLPattern as RegexURLPattern,
        URLResolver as RegexURLResolver, reverse, reverse_lazy)
except ImportError: # <= Django 1.10, Python<3.6
    from django.core.urlresolvers import (NoReverseMatch, RegexURLPattern,
        RegexURLResolver, reverse, reverse_lazy)
except ModuleNotFoundError: #pylint:disable=undefined-variable
    # <= Django 1.10, Python>=3.6
    from django.core.urlresolvers import (NoReverseMatch, RegexURLPattern,
        RegexURLResolver, reverse, reverse_lazy)


try:
    from django.utils.module_loading import import_string
except ImportError: # django < 1.7
    from django.utils.module_loading import import_by_path as import_string


try:
    from django.template import Origin
except ImportError:
    Origin = None


def get_model_class(full_name, settings_meta=None):
    """
    Returns a model class loaded from *full_name*. *settings_meta* is the name
    of the corresponding settings variable (used for error messages).
    """
    from django.core.exceptions import ImproperlyConfigured

    try:
        app_label, model_name = full_name.split('.')
    except ValueError:
        raise ImproperlyConfigured(
            "%s must be of the form 'app_label.model_name'" % full_name)
    return get_app_model_class(app_label, model_name, settings_meta)


def get_app_model_class(app_label, model_name, settings_meta=None):
    """
    Returns a model class loaded from *full_name*. *settings_meta* is the name
    of the corresponding settings variable (used for error messages).
    """
    from django.core.exceptions import ImproperlyConfigured
    model_class = None
    try:
        from django.apps import apps
        model_class = apps.get_model(app_label, model_name)
    except ImportError: # django < 1.7
        #pylint: disable=no-name-in-module
        from django.db.models import get_model
        model_class = get_model(app_label, model_name)

    if model_class is None:
        if settings_meta is None:
            settings_meta = 'settings'
        raise ImproperlyConfigured(
            "%s refers to model '%s' that has not been installed"
            % (settings_meta, app_label + '.' + model_name))
    return model_class


try:
    from django.utils.deprecation import MiddlewareMixin
except ImportError: # django < 1.11
    class MiddlewareMixin(object):
        pass
