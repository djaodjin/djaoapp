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

#pylint:disable=unused-import,no-name-in-module
import six

#pylint:disable=no-name-in-module,import-error
from six.moves.urllib.parse import urlparse, urlunparse

from django.core.exceptions import ImproperlyConfigured


try:
    #pylint: disable=no-name-in-module, unused-import
    from django.utils.module_loading import import_string
except ImportError: # django < 1.7
    #pylint: disable=unused-import
    from django.utils.module_loading import import_by_path as import_string


try:
    from django.template.backends.base import BaseEngine
except ImportError: # django < 1.8
    from django.template import Template as DjangoTemplate
    class BaseEngine(object):
        def __init__(self, params):
            params = params.copy()
            self.name = params.pop('NAME')
            self.dirs = list(params.pop('DIRS'))
            self.app_dirs = bool(params.pop('APP_DIRS'))
            if params:
                raise ImproperlyConfigured(
                    "Unknown parameters: {}".format(", ".join(params)))


try:
    from django.template.engine import _dirs_undefined
except ImportError: # django < 1.8
    _dirs_undefined = object()

try:
    from django.utils.deprecation import RemovedInDjango110Warning
except ImportError: # django < 1.8
    class RemovedInDjango110Warning(PendingDeprecationWarning):
        pass
