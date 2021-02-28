# Copyright (c) 2019, DjaoDjin inc.
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

#pylint:disable=line-too-long
# There does not seem to be a way to make simple table with line breaks
# in cells.
"""
Convenience module for access of rules application settings,
which enforces default settings when the main settings module
does not contain the appropriate settings.

========================  ======================  =============
 Name                      Default                 Description
========================  ======================  =============
ACCOUNT_MODEL             AUTH_USER_MODEL         Model used in a multi-party implementation.
ACCOUNT_URL_KWARG         None                    Variable name used in url definition to select an account.
DEFAULT_APP_CALLABLE      None                    Function to get the default app.
DEFAULT_APP_ID            SITE_ID                 Primary key to get the default app.
DEFAULT_RULES             ('/', 0, False)         Rules used when creating a new account
EXTRA_MIXIN               object                  Mixin to derive from
PATH_PREFIX_CALLABLE      None                    Function to retrive the path prefix
RULE_OPERATORS            ('', 'login_required')  Rules that can be used to decorate a URL.
SESSION_SERIALIZER        ``UsernameSerializer``  Serializer used to represent sessions.
========================  ======================  =============

To override defaults, add a RULES configuration block to your project
settings.py

Example:

.. code-block:: python

    RULES = {
      'ACCOUNT_MODEL': 'saas.Organization'
    }

"""
from importlib import import_module

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils import inspect

from .compat import is_authenticated, reverse, six


_SETTINGS = {
    'ACCOUNT_MODEL': getattr(settings, 'AUTH_USER_MODEL', None),
    'ACCOUNT_URL_KWARG': None,
    'DEFAULT_APP_CALLABLE': None,
    'DEFAULT_APP_ID': getattr(settings, 'SITE_ID', 1),
    'DEFAULT_FROM_EMAIL': settings.DEFAULT_FROM_EMAIL,
    'DEFAULT_RULES': [('/', 0, False)],
    'EXTRA_MIXIN': object,
    'PATH_PREFIX_CALLABLE': None,
    'RULE_OPERATORS': (
        '',
        'rules.settings.fail_authenticated'),
    'SESSION_SERIALIZER': 'rules.api.serializers.UsernameSerializer'
}
_SETTINGS.update(getattr(settings, 'RULES', {}))

USERNAME_PAT = r'[\w.@+-]+'


def fail_authenticated(request):
    """
    Authenticated
    """
    if not is_authenticated(request):
        return reverse(settings.LOGIN_URL)
    return False


def _load_perms_func(path):
    """
    Load a function from its path as a string.
    """
    if not path:
        return "Any", None, {}
    if callable(path):
        func = path
    elif isinstance(path, six.string_types):
        dot_pos = path.rfind('.')
        module, attr = path[:dot_pos], path[dot_pos + 1:]
        try:
            mod = import_module(module)
        except ImportError as err:
            raise ImproperlyConfigured('Error importing %s: "%s"'
                % (path, err))
        except ValueError:
            raise ImproperlyConfigured('Error importing %s: ' % path)
        try:
            func = getattr(mod, attr)
        except AttributeError:
            raise ImproperlyConfigured('Module "%s" does not define a "%s"'
                % (module, attr))
    else:
        raise ImproperlyConfigured(
            '%s is neither callable or a module path' % path)

    short_name = ""
    for line in func.__doc__.splitlines():
        short_name = line.strip()
        if short_name:
            break
    if not short_name:
        raise ImproperlyConfigured(
            '%s should have at least a one-line documentation' % path)

    parms = {}
    for arg in inspect.get_func_full_args(func):
        if len(arg) > 1:
            parms.update({arg[0]: arg[1]})

    return short_name, func, parms


RULES_APP_MODEL = getattr(settings, 'RULES_APP_MODEL', 'rules.App')

AUTH_USER_MODEL = settings.AUTH_USER_MODEL
ACCOUNT_MODEL = _SETTINGS.get('ACCOUNT_MODEL')
ACCOUNT_URL_KWARG = _SETTINGS.get('ACCOUNT_URL_KWARG')
DEFAULT_APP_CALLABLE = _SETTINGS.get('DEFAULT_APP_CALLABLE')
DEFAULT_APP_ID = _SETTINGS.get('DEFAULT_APP_ID')
DEFAULT_FROM_EMAIL = _SETTINGS.get('DEFAULT_FROM_EMAIL')
DEFAULT_RULES = _SETTINGS.get('DEFAULT_RULES')
EXTRA_MIXIN = _SETTINGS.get('EXTRA_MIXIN')
PATH_PREFIX_CALLABLE = _SETTINGS.get('PATH_PREFIX_CALLABLE')
RULE_OPERATORS = tuple([_load_perms_func(item)
    for item in _SETTINGS.get('RULE_OPERATORS')])
SESSION_SERIALIZER = _SETTINGS.get('SESSION_SERIALIZER')

DB_RULE_OPERATORS = tuple([(idx, item[0])
    for idx, item in enumerate(RULE_OPERATORS)])

# We would use:
#     from django.core.validators import slug_re
#     SLUG_RE = slug_re.pattern
# but that includes ^ and $ which makes it unsuitable for use in URL patterns.
SLUG_RE = r'[a-zA-Z0-9_\-]+'
