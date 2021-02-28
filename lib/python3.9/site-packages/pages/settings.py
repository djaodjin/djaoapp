# Copyright (c) 2017, DjaoDjin inc.
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

import os

from django.conf import settings

def theme_dir(account): #pylint:disable=unused-argument
    if account:
        return os.path.join(settings.BASE_DIR, 'themes', account)
    return os.path.join(settings.BASE_DIR, 'themes')

_SETTINGS = {
    'ACCOUNT_MODEL': getattr(settings, 'AUTH_USER_MODEL', None),
    'ACCOUNT_URL_KWARG': None,
    'ACTIVE_THEME_CALLABLE': None,
    'APP_NAME': getattr(settings, 'APP_NAME',
        os.path.basename(settings.BASE_DIR)),
    'AWS_STORAGE_BUCKET_NAME':
        getattr(settings, 'AWS_STORAGE_BUCKET_NAME',
            getattr(settings, 'APP_NAME',
                None)),
    'BUCKET_NAME_FROM_FIELDS': ['bucket_name'],
    'DEFAULT_ACCOUNT_CALLABLE': '',
    'DEFAULT_STORAGE_CALLABLE': '',
    'EXTRA_MIXIN': object,
    'MEDIA_PREFIX': '',
    'MEDIA_URL': getattr(settings, 'MEDIA_URL'),
    'MEDIA_ROOT': getattr(settings, 'MEDIA_ROOT'),
    'PUBLIC_ROOT': getattr(settings, 'STATIC_ROOT'),
    'PUBLIC_WHITELIST': None,
    'TEMPLATES_BLACKLIST': [],
    'TEMPLATES_WHITELIST': None,
    'THEME_DIR_CALLABLE': theme_dir,
}

_SETTINGS.update(getattr(settings, 'PAGES', {}))

ACCOUNT_MODEL = _SETTINGS.get('ACCOUNT_MODEL')
ACCOUNT_URL_KWARG = _SETTINGS.get('ACCOUNT_URL_KWARG')
APP_NAME = _SETTINGS.get('APP_NAME')
AWS_STORAGE_BUCKET_NAME = _SETTINGS.get('AWS_STORAGE_BUCKET_NAME')
BUCKET_NAME_FROM_FIELDS = _SETTINGS.get('BUCKET_NAME_FROM_FIELDS')
DEFAULT_ACCOUNT_CALLABLE = _SETTINGS.get('DEFAULT_ACCOUNT_CALLABLE')
DEFAULT_STORAGE_CALLABLE = _SETTINGS.get('DEFAULT_STORAGE_CALLABLE')
EXTRA_MIXIN = _SETTINGS.get('EXTRA_MIXIN')
MEDIA_PREFIX = _SETTINGS.get('MEDIA_PREFIX')
MEDIA_URL = _SETTINGS.get('MEDIA_URL')
MEDIA_ROOT = _SETTINGS.get('MEDIA_ROOT')
PUBLIC_ROOT = _SETTINGS.get('PUBLIC_ROOT')
PUBLIC_WHITELIST = _SETTINGS.get('PUBLIC_WHITELIST')
TEMPLATES_BLACKLIST = _SETTINGS.get('TEMPLATES_BLACKLIST')
TEMPLATES_WHITELIST = _SETTINGS.get('TEMPLATES_WHITELIST')
ACTIVE_THEME_CALLABLE = _SETTINGS.get('ACTIVE_THEME_CALLABLE')
THEME_DIR_CALLABLE = _SETTINGS.get('THEME_DIR_CALLABLE')

SLUG_RE = r'[a-zA-Z0-9_\-]+'
PATH_RE = r'(/[a-zA-Z0-9\-]+)*'

# Sanitizer settings
ALLOWED_TAGS = [
    'a',
    'span',
    'h1',
    'h2',
    'h3',
    'b',
    'pre',
    'em',
    'li',
    'ol',
    'strong',
    'ul',
    'i',
    'div',
    'br',
    'p',
    'img'
]

ALLOWED_ATTRIBUTES = {
    '*': ['style'],
    'a': ['href', 'title'],
    'img': ['src', 'title', 'style']
}

ALLOWED_STYLES = ['text-align', 'max-width', 'line-height']

BOOTSTRAP_EDITABLE_VARIABLES = [
    ('Colors', [
        {'property': '@gray-base', 'default': '#000', 'editor': 'color'},
        {'property': '@gray-darker', 'default': 'lighten(@gray-base, 13.5%)',
         'editor': 'color'},
        {'property': '@gray-dark', 'default': 'lighten(@gray-base, 20%)',
         'editor': 'color'},
        {'property': '@gray', 'default': 'lighten(@gray-base, 33.5%)',
         'editor': 'color'},
        {'property': '@gray-light', 'default': 'lighten(@gray-base, 46.7%)',
         'editor': 'color'},
        {'property': '@gray-lighter', 'default': 'lighten(@gray-base, 93.5%)',
         'editor': 'color'},
        {'property': '@brand-primary', 'default': 'darken(#428bca, 6.5%)',
         'editor': 'color'},
        {'property': '@brand-success', 'default': '#5cb85c',
         'editor': 'color'},
        {'property': '@brand-info', 'default': '#5bc0de',
         'editor': 'color'},
        {'property': '@brand-warning', 'default': '#f0ad4e',
         'editor': 'color'},
        {'property': '@brand-danger', 'default': '#d9534f',
         'editor': 'color'},
    ]),
    ('Buttons', [
        {'property': '@btn-font-weight', 'default': 'normal'},
        {'property': '@btn-default-color', 'default': '#333',
         'editor': 'color'},
        {'property': '@btn-default-bg', 'default': '#fff',
         'editor': 'color'},
        {'property': '@btn-default-border', 'default': '#ccc',
         'editor': 'color'},
        {'property': '@btn-primary-color', 'default': '#fff',
         'editor': 'color'},
        {'property': '@btn-primary-bg', 'default': '@brand-primary',
         'editor': 'color'},
        {'property': '@btn-primary-border',
         'default': 'darken(@btn-primary-bg, 5%)',
         'editor': 'color'},
        {'property': '@btn-success-color', 'default': '#fff',
         'editor': 'color'},
        {'property': '@btn-success-bg', 'default': '@brand-success',
         'editor': 'color'},
        {'property': '@btn-success-border',
         'default': 'darken(@btn-success-bg, 5%)',
         'editor': 'color'},
        {'property': '@btn-info-color', 'default': '#fff',
         'editor': 'color'},
        {'property': '@btn-info-bg', 'default': '@brand-info',
         'editor': 'color'},
        {'property': '@btn-info-border', 'default': 'darken(@btn-info-bg, 5%)',
         'editor': 'color'},
        {'property': '@btn-warning-color', 'default': '#fff',
         'editor': 'color'},
        {'property': '@btn-warning-bg', 'default': '@brand-warning',
         'editor': 'color'},
        {'property': '@btn-warning-border',
         'default': 'darken(@btn-warning-bg, 5%)',
         'editor': 'color'},
        {'property': '@btn-danger-color', 'default': '#fff',
         'editor': 'color'},
        {'property': '@btn-danger-bg', 'default': '@brand-danger',
         'editor': 'color'},
        {'property': '@btn-danger-border',
         'default': 'darken(@btn-danger-bg, 5%)',
         'editor': 'color'},
        {'property': '@btn-link-disabled-color', 'default': '@gray-light',
         'editor': 'color'},

    ]),
    ('Typography', [
        {'property': '@font-family-sans-serif',
         'default': '"Helvetica Neue", Helvetica, Arial, sans-serif'},
        {'property': '@font-family-serif',
         'default': 'Georgia, "Times New Roman", Times, serif'},
        {'property': '@font-family-monospace',
         'default': 'Menlo, Monaco, Consolas, "Courier New", monospace'},
        {'property': '@font-family-base', 'default': '@font-family-sans-serif'},
        {'property': '@font-size-base', 'default': '14px'},
        {'property': '@font-size-large',
         'default': 'ceil((@font-size-base * 1.25))'},
        {'property': '@font-size-small',
         'default': 'ceil((@font-size-base * 0.85))'},
        {'property': '@font-size-h1',
         'default': 'floor((@font-size-base * 2.6))'},
        {'property': '@font-size-h2',
         'default': 'floor((@font-size-base * 2.15))'},
        {'property': '@font-size-h3',
         'default': 'ceil((@font-size-base * 1.7))'},
        {'property': '@font-size-h4',
         'default': 'ceil((@font-size-base * 1.25))'},
        {'property': '@font-size-h5',
         'default': '@font-size-base'},
        {'property': '@font-size-h6',
         'default': 'ceil((@font-size-base * 0.85))'},
        {'property': '@line-height-base', 'default': '1.428571429'},
        {'property': '@line-height-computed',
         'default': 'floor((@font-size-base * @line-height-base))'},
        {'property': '@headings-font-family', 'default': 'inherit'},
        {'property': '@headings-font-weight', 'default': '500'},
        {'property': '@headings-line-height', 'default': '1.1'},
        {'property': '@headings-color', 'default': 'inherit',
         'editor': 'color'},
    ]),
]
