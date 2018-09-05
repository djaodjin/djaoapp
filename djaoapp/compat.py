# Copyright (c) 2018, DjaoDjin inc.
# see LICENSE

#pylint:disable=no-name-in-module,unused-import

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

def is_authenticated(request):
    if callable(request.user.is_authenticated):
        return request.user.is_authenticated()
    return request.user.is_authenticated
