# Copyright (c) 2021, Djaodjin Inc.
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
Convenience module for access of signup app settings, which enforces
default settings when the main settings module does not contain
the appropriate settings.

AWS_REGION       region used to create STS temporary credentials
AWS_UPLOAD_ROLE  role to assume in order to load directly from browser to S3
AWS_ACCOUNT_ID   account id for the role

DISABLED_AUTHENTICATION
    total lock down. A page will be displayed on login, registration,
    password reset, etc. but no new authentication can be performed.

DISABLED_REGISTRATION
   prevent new users from registering

REQUIRE_RECAPTCHA
   Requires to answer a recaptcha in registration
"""

from django.conf import settings

_SETTINGS = {
    'ACCOUNT_ACTIVATION_DAYS': getattr(settings, 'ACCOUNT_ACTIVATION_DAYS', 2),
    'ACCOUNT_MODEL': getattr(settings, 'AUTH_USER_MODEL', None),
    'AUTH_USER_MODEL': getattr(settings, 'AUTH_USER_MODEL'),
    'AWS_ACCOUNT_ID': None,
    'AWS_EXTERNAL_ID': "",
    'AWS_REGION': getattr(settings, 'AWS_REGION', None),
    'AWS_UPLOAD_ROLE': None,
    'AWS_S3_BUCKET_NAME': getattr(settings, 'AWS_S3_BUCKET_NAME', None),
    'BYPASS_VERIFICATION_KEY_EXPIRED_CHECK': False,
    'DEFAULT_FROM_EMAIL': getattr(settings, 'DEFAULT_FROM_EMAIL'),
    'DISABLED_AUTHENTICATION': False,
    'DISABLED_REGISTRATION': False,
    'EMAIL_DYNAMIC_VALIDATOR': None,
    'EXTRA_FIELD': None,
    'JWT_ALGORITHM': 'HS256',
    'JWT_SECRET_KEY': getattr(settings, 'SECRET_KEY'),
    'LDAP': {
        'SERVER_URI': None,
        'USER_SERCH_DN': None
    },
    'LOGIN_THROTTLE': None,
    'LOGOUT_CLEAR_COOKIES' : None,
    'MFA_MAX_ATTEMPTS': 3,
    'NOTIFICATIONS_OPT_OUT': True,
    'PASSWORD_RESET_THROTTLE': None,
    'PICTURE_STORAGE_CALLABLE': None,
    'RANDOM_SEQUENCE': [],
    'REQUIRES_RECAPTCHA': False
}
_SETTINGS.update(getattr(settings, 'SIGNUP', {}))

ACCOUNT_MODEL = _SETTINGS.get('ACCOUNT_MODEL')
AUTH_USER_MODEL = _SETTINGS.get('AUTH_USER_MODEL')
AWS_REGION = _SETTINGS.get('AWS_REGION')
AWS_UPLOAD_ROLE = _SETTINGS.get('AWS_UPLOAD_ROLE')
AWS_ACCOUNT_ID = _SETTINGS.get('AWS_ACCOUNT_ID')
AWS_EXTERNAL_ID = _SETTINGS.get('AWS_EXTERNAL_ID')
AWS_S3_BUCKET_NAME = _SETTINGS.get('AWS_S3_BUCKET_NAME')
BYPASS_VERIFICATION_KEY_EXPIRED_CHECK = _SETTINGS.get(
    'BYPASS_VERIFICATION_KEY_EXPIRED_CHECK')
DEFAULT_FROM_EMAIL = _SETTINGS.get('DEFAULT_FROM_EMAIL')
DISABLED_AUTHENTICATION = _SETTINGS.get('DISABLED_AUTHENTICATION')
DISABLED_REGISTRATION = _SETTINGS.get('DISABLED_REGISTRATION')
EMAIL_DYNAMIC_VALIDATOR = _SETTINGS.get('EMAIL_DYNAMIC_VALIDATOR')
EXTRA_FIELD = _SETTINGS.get('EXTRA_FIELD')
JWT_SECRET_KEY = _SETTINGS.get('JWT_SECRET_KEY')
JWT_ALGORITHM = _SETTINGS.get('JWT_ALGORITHM')
KEY_EXPIRATION = _SETTINGS.get('ACCOUNT_ACTIVATION_DAYS')
LDAP_SERVER_URI = _SETTINGS.get('LDAP', {}).get('SERVER_URI', None)
LDAP_USER_SEARCH_DN = _SETTINGS.get('LDAP', {}).get('USER_SERCH_DN', None)
LOGIN_THROTTLE = _SETTINGS.get('LOGIN_THROTTLE')
LOGOUT_CLEAR_COOKIES = _SETTINGS.get('LOGOUT_CLEAR_COOKIES')
MFA_MAX_ATTEMPTS = _SETTINGS.get('MFA_MAX_ATTEMPTS')
NOTIFICATIONS_OPT_OUT = _SETTINGS.get('NOTIFICATIONS_OPT_OUT')
PASSWORD_RESET_THROTTLE = _SETTINGS.get('PASSWORD_RESET_THROTTLE')
PICTURE_STORAGE_CALLABLE = _SETTINGS.get('PICTURE_STORAGE_CALLABLE')
RANDOM_SEQUENCE = _SETTINGS.get('RANDOM_SEQUENCE')
REQUIRES_RECAPTCHA = _SETTINGS.get('REQUIRES_RECAPTCHA')

LOGIN_URL = getattr(settings, 'LOGIN_URL')
LOGIN_REDIRECT_URL = getattr(settings, 'LOGIN_REDIRECT_URL')

EMAIL_VERIFICATION_PAT = r'[a-f0-9]{40}'
FULL_NAME_PAT = r"^([^\W\d_]|[ \.\'\-])+$"
USERNAME_PAT = r'[\w.@+-]+'

RANDOM_SEQUENCE_IDX = 0
