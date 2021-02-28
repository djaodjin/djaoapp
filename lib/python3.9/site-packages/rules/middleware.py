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

from __future__ import unicode_literals

import logging
from django.middleware.csrf import CsrfViewMiddleware
from django.utils.cache import patch_vary_headers
from rest_framework.authentication import get_authorization_header
from rest_framework.views import APIView

from .compat import six
from .perms import find_rule
from .utils import get_current_app


LOGGER = logging.getLogger(__name__)

ACCESS_CONTROL_ALLOW_HEADERS = 'Access-Control-Allow-Headers'
ACCESS_CONTROL_ALLOW_ORIGIN = 'Access-Control-Allow-Origin'
ACCESS_CONTROL_ALLOW_CREDENTIALS = 'Access-Control-Allow-Credentials'

ACCESS_CONTROL_ALLOW_HEADERS_ALLOWED = \
    "Origin, X-Requested-With, Content-Type, Accept, X-CSRFToken, Authorization"


class RulesMiddleware(CsrfViewMiddleware):
    """
    Disables CSRF check if the HTTP request is forwarded.
    Pass OPTIONS HTTP request regardless since authorization header is not
    sent along by browser (CORS).
    """

    def patch_set_cookies(self, response, domain):
        if not response.cookies:
            return
        for key in response.cookies:
            response.cookies[key]['domain'] = domain

    def process_view(self, request, view_func, view_args, view_kwargs):
        view_class = getattr(view_func, 'view_class', None)
        if hasattr(view_class, 'conditional_forward'):
            app = get_current_app(request)
            request.matched_rule, request.matched_params = find_rule(
                request, app)
            if (request.matched_rule and request.matched_rule.is_forward
                and request.method not in ('GET', 'HEAD', 'OPTIONS', 'TRACE')):
                # We are forwarding the request so the CSRF is delegated
                # to the application handling the forwarded request.
                #pylint:disable=protected-access
                request._dont_enforce_csrf_checks = True
                LOGGER.debug("dont enforce csrf checks on %s %s",
                    request.method, request.path)

        auth = get_authorization_header(request).split()
        if auth and auth[0].lower() in [b'basic', b'bearer']:
            # We need to support API calls from the command line.
            #pylint:disable=protected-access
            request._dont_enforce_csrf_checks = True
            LOGGER.debug("dont enforce csrf checks on %s %s because"\
                " we have an authorization header",
                request.method, request.path)

        # CORS will first send an OPTIONS request with no authorization header
        # and expect to get a 200 OK response.
        if request.method.lower() == 'options':
            if view_class and isinstance(view_class, APIView):
                # Duplicates what Django does before calling `dispatch`
                view = view_class(**view_func.initkwargs)
                view.setup(request, *view_args, **view_kwargs)
                if not hasattr(view, 'request'):
                    raise AttributeError("%s instance has no 'request'"
                        " attribute. Did you override setup() and forget"
                        " to call super()?" % view_class.__name__)
                if hasattr(view, 'initialize_request'):
                    # Duplicates what rest_framework does before calling
                    # `options` minus testing for permissions since we won't
                    # have a user (no Authorization header).
                    request = view.initialize_request(
                        request, *view_args, **view_kwargs)
                    view.headers = view.default_response_headers
                    view.format_kwarg = view.get_format_suffix(**view_kwargs)
                    request.accepted_renderer, request.accepted_media_type = \
                        view.perform_content_negotiation(request)
                    version, scheme = view.determine_version(
                        request, *view_args, **view_kwargs)
                    request.version, request.versioning_scheme = version, scheme
                    response = view.options(request, *view_args, **view_kwargs)
                    view.response = view.finalize_response(
                        request, response, *view_args, **view_kwargs)
                    return view.response

                return view.options(request, *view_args, **view_kwargs)

        return super(RulesMiddleware, self).process_view(
            request, view_func, view_args, view_kwargs)

    def process_response(self, request, response):
        #pylint:disable=no-self-use

        # Sets the CORS headers as appropriate.
        origin = request.META.get('HTTP_ORIGIN')
        if not origin:
            return super(RulesMiddleware, self).process_response(
                request, response)

        origin_parsed = six.moves.urllib.parse.urlparse(origin)
        if not origin_parsed.netloc:
            return super(RulesMiddleware, self).process_response(
                request, response)

        parts = request.get_host().split(':')
        host = parts[0].lower()
        port = parts[1] if len(parts) > 1 else None
        origin_parts = origin_parsed.netloc.split(':')
        origin_host = origin_parts[0].lower()
        origin_port = origin_parts[1] if len(origin_parts) > 1 else None
        if host != origin_host or port != origin_port:
            if origin_host.startswith('www.'):
                origin_host = origin_host[4:]
            if host == origin_host or host.endswith('.%s' % origin_host):
                patch_vary_headers(response, ['Origin'])
                response[ACCESS_CONTROL_ALLOW_HEADERS] = \
                    ACCESS_CONTROL_ALLOW_HEADERS_ALLOWED
                response[ACCESS_CONTROL_ALLOW_ORIGIN] = origin
                response[ACCESS_CONTROL_ALLOW_CREDENTIALS] = "true"
                # Patch cookies with `Domain=`
                self.patch_set_cookies(response, origin_host)
            else:
                logging.getLogger('django.security.SuspiciousOperation').info(
                    "request %s was not initiated by origin %s",
                    request.get_raw_uri(), origin)
        return super(RulesMiddleware, self).process_response(
            request, response)
