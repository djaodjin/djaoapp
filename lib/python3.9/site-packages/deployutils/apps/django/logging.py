# Copyright (c) 2020, Djaodjin Inc.
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

from __future__ import absolute_import

import logging, json, os

from django.core.handlers.wsgi import WSGIRequest
from django.views.debug import ExceptionReporter

from ... import crypt
from .compat import get_installed_distributions, is_anonymous, six
from .thread_local import get_request


class RequestFilter(logging.Filter):

    def filter(self, record):
        """
        Adds username, remote_addr and http_user_agent to the record.
        """
        request = get_request()
        if request:
            user = getattr(request, 'user', None)
            if user and not is_anonymous(request):
                record.username = user.username
            else:
                record.username = '-'
            meta = getattr(request, 'META', {})
            record.remote_addr = meta.get('REMOTE_ADDR', '-')
            record.http_user_agent = meta.get('HTTP_USER_AGENT', '-')
            if not hasattr(record, 'request'):
                record.request = request
        else:
            record.username = '-'
            record.remote_addr = '-'
            record.http_user_agent = '-'
        return True


class JSONFormatter(logging.Formatter):
    """
    JSON log formatter.
    """

    _whitelists = {
        'record': [
            'asctime',
            'event',
            'http_user_agent',
            'log_level',
            'message',
            'http_path',
            'remote_addr',
            'http_method',
            'http_version',
            'username'
        ],
        'traceback': [
            'server_time',
            'sys_version_info',
            'exception_type',
            'frames',
            'template_info',
            'sys_executable',
            'django_version_info',
            'exception_value',
            'sys_path',
            'filtered_POST',
            'settings',
            'postmortem',
            'template_does_not_exist'
        ],
        'meta': [
            'CONTENT_LENGTH',
            'CONTENT_TYPE',
            'CSRF_COOKIE',
            'GATEWAY_INTERFACE',
            'HTTP_ACCEPT',
            'HTTP_ACCEPT_ENCODING',
            'HTTP_ACCEPT_LANGUAGE',
            'HTTP_CACHE_CONTROL',
            'HTTP_CONNECTION',
            'HTTP_COOKIE',
            'HTTP_DNT',
            'HTTP_HOST',
            'HTTP_UPGRADE_INSECURE_REQUESTS',
            'HTTP_USER_AGENT',
            'LOGNAME',
            'PWD',
            'QUERY_STRING',
            'REMOTE_ADDR',
            'REMOTE_HOST',
            'REQUEST_METHOD',
            'SECURITYSESSIONID',
            'SERVER_NAME',
            'SERVER_PORT',
            'SERVER_PROTOCOL',
            'SERVER_SOFTWARE',
            'TMPDIR',
            'USER',
            'VIRTUAL_ENV',
            'wsgi.version',
            'wsgi.url_scheme',
        ],
        'settings': [
            'ABSOLUTE_URL_OVERRIDES',
            'ADMINS',
            'ALLOWED_HOSTS',
            'ALLOWED_INCLUDE_ROOTS',
            'APPEND_SLASH',
            'APP_NAME',
            'ASSETS_DEBUG',
            'AUTHENTICATION_BACKENDS',
            'BASE_DIR',
            'CSRF_COOKIE_AGE',
            'CSRF_COOKIE_DOMAIN',
            'CSRF_COOKIE_HTTPONLY',
            'CSRF_COOKIE_NAME',
            'CSRF_COOKIE_PATH',
            'CSRF_COOKIE_SECURE',
            'CSRF_FAILURE_VIEW',
            'CSRF_HEADER_NAME',
            'CSRF_TRUSTED_ORIGINS',
            'DEBUG',
            'DEBUG_PROPAGATE_EXCEPTIONS',
            'DEFAULT_FILE_STORAGE',
            'DEFAULT_FROM_EMAIL',
            'EMAILER_BACKEND',
            'EMAIL_BACKEND',
            'EMAIL_HOST',
            'EMAIL_HOST_PASSWORD',
            'EMAIL_HOST_USER'
            'EMAIL_PORT',
            'EMAIL_SSL_CERTFILE',
            'EMAIL_SSL_KEYFILE',
            'EMAIL_SUBJECT_PREFIX',
            'EMAIL_TIMEOUT',
            'EMAIL_USE_SSL',
            'EMAIL_USE_TLS',
            'FILE_UPLOAD_DIRECTORY_PERMISSIONS',
            'FILE_UPLOAD_HANDLERS',
            'FILE_UPLOAD_MAX_MEMORY_SIZE',
            'FILE_UPLOAD_PERMISSIONS',
            'FILE_UPLOAD_TEMP_DIR',
            'INSTALLED_APPS',
            'MAIL_TOADDRS',
            'MANAGERS',
            'MAX_UPLOAD_SIZE',
            'MIDDLEWARE_CLASSES',
            'PASSWORD_HASHERS',
            'SECURE_BROWSER_XSS_FILTER',
            'SECURE_CONTENT_TYPE_NOSNIFF',
            'SECURE_HSTS_INCLUDE_SUBDOMAINS',
            'SECURE_HSTS_SECONDS',
            'SECURE_PROXY_SSL_HEADER',
            'SECURE_REDIRECT_EXEMPT',
            'SECURE_SSL_HOST',
            'SECURE_SSL_REDIRECT',
            'SERVER_EMAIL',
            'SESSION_CACHE_ALIAS',
            'SESSION_COOKIE_AGE',
            'SESSION_COOKIE_DOMAIN',
            'SESSION_COOKIE_HTTPONLY',
            'SESSION_COOKIE_NAME',
            'SESSION_COOKIE_PATH',
            'SESSION_COOKIE_SECURE',
            'SESSION_ENGINE',
            'SESSION_EXPIRE_AT_BROWSER_CLOSE',
            'SESSION_FILE_PATH',
            'SESSION_SAVE_EVERY_REQUEST',
            'SESSION_SERIALIZER',
            'USE_X_FORWARDED_HOST',
            'USE_X_FORWARDED_PORT',
            'WSGI_APPLICATION',
            'X_FRAME_OPTIONS',
        ]
    }

    translated = {
        'asctime': 'time_local',
        'levelname': 'log_level',
        'path_info': 'http_path',
        'request_method': 'http_method',
        'server_protocol': 'http_version'
    }

    def usesTime(self):
        return True

    def __init__(self, fmt=None, datefmt=None, whitelists=None, replace=False):
        super(JSONFormatter, self).__init__(fmt=fmt, datefmt=datefmt)
        if whitelists and replace:
            self.whitelists = whitelists
        elif whitelists:
            self.whitelists = self._whitelists
            for key, values in six.iteritems(whitelists):
                if not key in self.whitelists:
                    self.whitelists[key] = []
                self.whitelists[key] += values
        else:
            self.whitelists = self._whitelists

    def format(self, record):
        record.message = record.getMessage()
        if self.usesTime():
            record.asctime = self.formatTime(record, self.datefmt)

        record_dict = {
            attr_name: record.__dict__[attr_name]
            for attr_name in record.__dict__
            if attr_name in self.whitelists.get('record')
        }
        for from_key, to_key in six.iteritems(self.translated):
            if hasattr(record, from_key):
                record_dict.update({to_key: getattr(record, from_key)})

        record_dict.update({'process': os.getpid()})

        if hasattr(record, 'request'):
            user = getattr(record.request, 'user', None)
            if user and not is_anonymous(record.request):
                record_dict.update({'username': user.username})
        if not 'username' in record_dict:
            record_dict.update({'username': '-'})

        if (hasattr(record, 'request') and
            isinstance(record.request, WSGIRequest)):
            request = record.request
            record_dict.update({
                'http_method': getattr(request, 'method', "-"),
                'http_path': getattr(request, 'path_info', "-"),
                'http_version': request.META.get('SERVER_PROTOCOL', '-'),
                'http_host': request.META.get('HTTP_HOST', '-'),
                'http_user_agent': request.META.get('HTTP_USER_AGENT', '-'),
                'remote_addr': request.META.get('REMOTE_ADDR', '-'),
            })
        else:
            request = None
            record_dict.update({
                'http_method': "-",
                'http_path': "-",
                'http_version': "-",
                'http_host': "-",
                'http_user_agent': record_dict.get('http_user_agent', "-"),
                'remote_addr': record_dict.get('remote_addr', "-"),
            })

        if record.exc_info:
            exc_info_dict = self.formatException(
                record.exc_info, request=request)
            if exc_info_dict:
                record_dict.update(exc_info_dict)

        formatted = {}
        formatted.update(record_dict)
        formatted.update({
            'message': json.dumps(record_dict, cls=crypt.JSONEncoder)})
        return self._fmt % formatted

    def formatException(self, exc_info, request=None):
        #pylint:disable=too-many-locals,arguments-differ
        reporter = ExceptionReporter(request, is_email=True, *exc_info)
        traceback_data = reporter.get_traceback_data()
        filtered_traceback_data = {}

        if request:
            request_dict = {
                'http_method': request.method,
                'http_path': request.path_info}
            params = {}
            for key, val in six.iteritems(request.GET):
                params.update({key: val})
            if params:
                request_dict.update({'GET': params})
            params = {}
            for key, val in six.iteritems(request.POST):
                params.update({key: val})
            if params:
                request_dict.update({'POST': params})
            params = {}
            for key, val in six.iteritems(request.FILES):
                params.update({key: val})
            if params:
                request_dict.update({'FILES': params})
            params = {}
            for key, val in six.iteritems(request.COOKIES):
                params.update({key: val})
            if params:
                request_dict.update({'COOKIES': params})
            params = {}
            for key in self.whitelists.get('meta', []):
                value = request.META.get(key, None)
                if value is not None:
                    params.update({key: value})
            if params:
                request_dict.update({'META': params})
            filtered_traceback_data.update({'request_data': request_dict})

        for frame in traceback_data.get('frames', []):
            frame.pop('tb', None)

        for key in self.whitelists.get('traceback', []):
            value = traceback_data.get(key, None)
            if value is not None:
                if key == 'settings':
                    value = {}
                    for settings_key in self.whitelists.get(key, []):
                        settings_value = traceback_data[key].get(
                            settings_key, None)
                        if settings_value is not None:
                            value.update({settings_key: settings_value})
                if key == 'frames':
                    frames = value
                    value = []
                    for frame in frames:
                        frame_dict = {}
                        for frame_key, frame_val in six.iteritems(frame):
                            frame_dict.update({frame_key: str(frame_val)})
                        value += [frame_dict]
                filtered_traceback_data.update({key: value})

        # Pip packages
        installed_packages = get_installed_distributions(local_only=False)
        filtered_traceback_data.update({
            'installed_packages':
            [{'name': package.project_name,
              'version': package.version,
              'location': package.location}
             for package in installed_packages]
        })

        return filtered_traceback_data
