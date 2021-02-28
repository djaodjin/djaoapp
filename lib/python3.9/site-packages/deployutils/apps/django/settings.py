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

"""
Convenience module for access of deployutils app settings, which enforces
default settings when the main settings module does not contain
the appropriate settings.

In a production environment, the static resources (images, css, js) are served
directly by nginx from MULTITIER_RESOURCES_ROOT. Furthermore the CMS pages are
served by one process while the app is served by another process. This requires
to install the templates from the app repo into the CMS template directory
(MULTITIER_THEMES_DIR) after the TemplateNodes related to the assets
pipeline have been resolved.
"""
import os

from django.conf import settings

_SETTINGS = {
    'ALLOWED_NO_SESSION': [],
    'APP_NAME': getattr(settings, 'APP_NAME',
        os.path.basename(settings.BASE_DIR)),
    'BACKEND_SESSION_STORE': None,
    'DEBUG': getattr(settings, 'DEBUG', None),
    'DEPLOYED_WEBAPP_ROOT': '/var/www',
    'DEPLOYED_SERVERS': None,
    'DJAODJIN_SECRET_KEY': os.getenv('DJAODJIN_SECRET_KEY',
        getattr(settings, 'DJAODJIN_SECRET_KEY', None)),
    'DRY_RUN': getattr(settings, 'DEPLOYUTILS_DRY_RUN', False),
    'INSTALLED_APPS': getattr(settings, 'DEPLOYUTILS_INSTALLED_APPS',
        settings.INSTALLED_APPS),
    'MOCKUP_SESSIONS': {},
    'MULTITIER_RESOURCES_ROOT': getattr(settings, 'DEPLOYUTILS_RESOURCES_ROOT',
        settings.BASE_DIR + '/htdocs/'),
    'MULTITIER_ASSETS_DIR': os.path.join(settings.BASE_DIR, 'htdocs'),
    'MULTITIER_THEMES_DIR': os.path.join(settings.BASE_DIR, 'themes'),
    'RESOURCES_REMOTE_LOCATION': getattr(settings,
        'DEPLOYUTILS_RESOURCES_REMOTE_LOCATION', None),
    'SESSION_COOKIE_NAME': 'sessionid',
}
_SETTINGS.update(getattr(settings, 'DEPLOYUTILS', {}))

ALLOWED_NO_SESSION = _SETTINGS.get('ALLOWED_NO_SESSION')
APP_NAME = _SETTINGS.get('APP_NAME')
BACKEND_SESSION_STORE = _SETTINGS.get('BACKEND_SESSION_STORE')
DEBUG = _SETTINGS.get('DEBUG')
DEPLOYED_WEBAPP_ROOT = _SETTINGS.get('DEPLOYED_WEBAPP_ROOT')
DEPLOYED_SERVERS = _SETTINGS.get('DEPLOYED_SERVERS')
DJAODJIN_SECRET_KEY = _SETTINGS.get('DJAODJIN_SECRET_KEY')
DRY_RUN = _SETTINGS.get('DRY_RUN')
MOCKUP_SESSIONS = _SETTINGS.get('MOCKUP_SESSIONS')
MULTITIER_ASSETS_DIR = _SETTINGS.get('MULTITIER_ASSETS_DIR')
MULTITIER_THEMES_DIR = _SETTINGS.get('MULTITIER_THEMES_DIR')
MULTITIER_RESOURCES_ROOT = _SETTINGS.get('MULTITIER_RESOURCES_ROOT')
if not MULTITIER_RESOURCES_ROOT.endswith('/'):
    MULTITIER_RESOURCES_ROOT = MULTITIER_RESOURCES_ROOT + '/'
RESOURCES_REMOTE_LOCATION = _SETTINGS.get('RESOURCES_REMOTE_LOCATION')
SESSION_COOKIE_NAME = _SETTINGS.get('SESSION_COOKIE_NAME')

INSTALLED_APPS = _SETTINGS.get('INSTALLED_APPS')
SESSION_SAVE_EVERY_REQUEST = getattr(
    settings, 'SESSION_SAVE_EVERY_REQUEST', False)
