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

"""
Convenience module for access of multitier application settings, which enforces
default settings when the main settings module does not contain
the appropriate settings.
"""
import os

from django.conf import settings

# `MULTITIER_SITE_MODEL` cannot be included in `_SETTINGS` because
# of the way Django handles swappable models.
MULTITIER_SITE_MODEL = getattr(
    settings, 'MULTITIER_SITE_MODEL', 'multitier.Site')

_SETTINGS = {
    'ACCOUNT_MODEL': settings.AUTH_USER_MODEL,
    'ACCOUNT_GET_CURRENT': None,
    'ACCOUNT_URL_KWARG': None,
    'DEBUG_SQLITE3_PATHS': [],
    'DEFAULT_DOMAIN': 'localhost:8000',
    'DEFAULT_SITE': getattr(settings, 'APP_NAME', 'default'),
    'DEFAULT_URLS': [],
    'DEFAULT_FROM_EMAIL': settings.DEFAULT_FROM_EMAIL,
    'ROUTER_APPS': ('auth', 'sessions', 'contenttypes'),
    'ROUTER_TABLES': [],
    'THEMES_DIRS': [os.path.join(settings.BASE_DIR, 'themes')],
    'STATICFILES_DIRS': settings.STATICFILES_DIRS,
    'SECRET_KEY': settings.SECRET_KEY
}
_SETTINGS.update(getattr(settings, 'MULTITIER', {}))

SLUG_RE = r'[a-zA-Z0-9\-]+'

ACCOUNT_GET_CURRENT = _SETTINGS.get('ACCOUNT_GET_CURRENT')
ACCOUNT_MODEL = _SETTINGS.get('ACCOUNT_MODEL')
ACCOUNT_URL_KWARG = _SETTINGS.get('ACCOUNT_URL_KWARG')
DEBUG_SQLITE3_PATHS = _SETTINGS.get('DEBUG_SQLITE3_PATHS')
DEFAULT_DOMAIN = _SETTINGS.get('DEFAULT_DOMAIN')
DEFAULT_FROM_EMAIL = _SETTINGS.get('DEFAULT_FROM_EMAIL')
DEFAULT_SITE = _SETTINGS.get('DEFAULT_SITE')
DEFAULT_URLS = _SETTINGS.get('DEFAULT_URLS')
ROUTER_APPS = _SETTINGS.get('ROUTER_APPS')
ROUTER_TABLES = _SETTINGS.get('ROUTER_TABLES')
SECRET_KEY = _SETTINGS.get('SECRET_KEY')
STATICFILES_DIRS = _SETTINGS.get('STATICFILES_DIRS')
THEMES_DIRS = _SETTINGS.get('THEMES_DIRS')
