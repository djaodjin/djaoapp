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

import json, logging, re

from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.sites.requests import RequestSite
from django.core.exceptions import FieldError, SuspiciousOperation
from django.http import HttpResponse, SimpleCookie
from django.template.response import TemplateResponse
from django.views.generic import UpdateView, TemplateView
import requests
from requests.exceptions import RequestException
from deployutils.apps.django.settings import SESSION_COOKIE_NAME

from .. import settings
from ..compat import get_model, http_cookies, six
from ..mixins import AppMixin, SessionDataMixin
from ..perms import (check_permissions as base_check_permissions,
    find_rule, redirect_or_denied)
from ..utils import JSONEncoder, get_app_model


LOGGER = logging.getLogger(__name__)


class DisallowedCookieName(SuspiciousOperation):
    """
    Cookie header contains invalid value
    """


class SessionProxyMixin(SessionDataMixin):
    """
    Proxy to the application

    Check permissions associated to the request and forwards request
    when appropriate.
    """
    redirect_field_name = REDIRECT_FIELD_NAME
    login_url = None

    def check_permissions(self, request):
        redirect_url, self.rule, self.session = base_check_permissions(
            request, self.app,
            redirect_field_name=self.redirect_field_name,
            login_url=self.login_url)
        response = None
        if redirect_url:
            response = redirect_or_denied(
                request, redirect_url, self.redirect_field_name)
        if not response and self.session:
            # XXX Insert into self.request.session so we can use the same
            #     code on self-hosted templates.
            last_visited = self.session.get('last_visited', None)
            if last_visited:
                if not isinstance(last_visited, six.string_types):
                    last_visited = last_visited.isoformat()
                self.request.session.update({
                    'last_visited': last_visited})
        return (response, self.rule.is_forward if self.rule else False)

    def get_context_data(self, **kwargs):
        context = super(SessionProxyMixin, self).get_context_data(**kwargs)
        context.update({
            'forward_session': json.dumps(
                self.session, indent=2, cls=JSONEncoder),
            'forward_session_cookie': self.forward_session_header,
            'forward_url': '%s%s' % (self.app.entry_point, self.request.path),
        })
        return context

# Implementation Note:
# We cannot override ``dispatch()`` because djangorestframework happens
# to do user authentication there. Also doing so prevent injection
# of the edit tools.
# On the other hand, we cannnot blindly override `get`, `post`, etc. either
# because parents might not have implemented the method and it would result
# in 500 errors when incorrect HTTP requests are generated on the end points.
#   def dispatch(self, request, *args, **kwargs):
#       response = self.conditional_forward(request)
#       if response:
#           return response
#       # If we get here, the request was forwarded and we got an exception
#       # or the request must be handled locally.
#       return super(SessionProxyMixin, self).dispatch(request, *args, **kwargs)

    def options(self, request, *args, **kwargs):
        # With CORS the browser strips the Authentication header yet
        # it expects a 200 OK response.
        request.matched_rule, request.matched_params = find_rule(
            request, self.app)
        if request.matched_rule and request.matched_rule.is_forward:
            try:
                return self.fetch_remote_page()
            except RequestException as err:
                return self.forward_error(err)
        return self.forward_to_parent(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        response = self.conditional_forward(request)
        if response:
            return response
        return self.forward_to_parent(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        response = self.conditional_forward(request)
        if response:
            return response
        return self.forward_to_parent(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        response = self.conditional_forward(request)
        if response:
            return response
        return self.forward_to_parent(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        response = self.conditional_forward(request)
        if response:
            return response
        return self.forward_to_parent(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        response = self.conditional_forward(request)
        if response:
            return response
        return self.forward_to_parent(request, *args, **kwargs)

    def forward_to_parent(self, request, *args, **kwargs):
        if request.method.lower() in self.http_method_names:
            handler = getattr(super(SessionProxyMixin, self),
                request.method.lower(), self.http_method_not_allowed)
        else:
            handler = self.http_method_not_allowed
        return handler(request, *args, **kwargs)

    def forward_error(self, err):
        context = self.get_context_data()
        context.update({'err': str(err)})
        return TemplateResponse(
            request=self.request,
            template='rules/forward_error.html',
            context=context,
            content_type='text/html',
            status=503)

    def conditional_forward(self, request):
        response, forward = self.check_permissions(request)
        if response:
            return response
        if forward:
            try:
                return self.fetch_remote_page()
            except RequestException as err:
                return self.forward_error(err)
        return None

    def fetch_remote_page(self):
        """
        Forward the request to the remote site after adjusting session
        information and request headers.

        Respond with the remote site response after adjusting session
        information and response headers.
        """
        remoteurl = '%s%s' % (self.app.entry_point, self.request.path)
        requests_args = self.translate_request_args(self.request)
        if LOGGER.getEffectiveLevel() == logging.DEBUG:
            LOGGER.debug("\"%s %s (Fwd to %s)\" with session %s,"\
                " updated headers: %s",
                self.request.method, self.request.path, self.app.entry_point,
                self.session, requests_args)
        else:
            LOGGER.info("\"%s %s (Fwd to %s)\"", self.request.method,
                self.request.path, self.app.entry_point, extra={
                    'event': 'http_forward', 'fwd_to': self.app.entry_point,
                    'request': self.request})
        response = requests.request(
            self.request.method, remoteurl, **requests_args)
        return self.translate_response(response)

    def translate_request_args(self, request):
        #pylint:disable=too-many-statements
        requests_args = {'allow_redirects': False, 'headers': {}}
        cookies = SimpleCookie()
        try:
            for key, value in six.iteritems(request.COOKIES):
                cookies[key] = value
            if (self.app.session_backend and
                self.app.session_backend != self.app.JWT_SESSION_BACKEND):
                cookies[SESSION_COOKIE_NAME] = self.session_cookie_string
            else:
                # Cookies, as opposed to Authorization header have multiple
                # purposes, so we keep the SESSION_COOKIE_NAME (if exists)
                # regardless of the backend used to transport the proxy session.
                pass
        except http_cookies.CookieError as err:
            # Some is messing up with the 'Cookie' header. This sometimes
            # happen with bots trying to set 'Max-Age' or other reserved words.
            raise DisallowedCookieName(str(err))

        #pylint: disable=maybe-no-member
        # Something changed in `SimpleCookie.output` that creates an invalid
        # cookie string starting with a spacel or there are more strident
        # checks in the requests module (2.11.1) that prevents passing
        # a cookie string starting with a space.
        cookie_string = cookies.output(header='', sep=';').strip()

        # Retrieve the HTTP headers from a WSGI environment dictionary.  See
        # https://docs.djangoapp.com/en/dev/ref/request-response/\
        #    #django.http.HttpRequest.META
        headers = {}
        for key, value in six.iteritems(request.META):
            key_upper = key.upper()
            if key_upper.startswith('HTTP_'):
                key_upper = key_upper[5:].replace('_', '-')
                if key_upper == 'AUTHORIZATION':
                    # We donot want to inadvertently forward the credentials
                    # to connect to the proxy when the session backend is
                    # using cookies.
                    pass
                if key_upper == 'COOKIE':
                    headers[key_upper] = cookie_string
                else:
                    # Some servers don't like when you send the requesting host
                    # through but we do anyway. That's how the nginx reverse
                    # proxy is configured as well.
                    headers[key_upper] = value
            elif key_upper in ('CONTENT_TYPE', 'CONTENT_LENGTH'):
                headers[key.replace('_', '-')] = value

        site = RequestSite(request)
        if 'HOST' not in headers:
            headers.update({'HOST': site.domain})
        if 'X-FORWARDED-FOR' not in headers:
            headers.update({'X-FORWARDED-FOR': site.domain})
        if 'X-REAL-IP' not in headers:
            headers.update({'X-REAL-IP': request.META.get('REMOTE_ADDR', None)})
        if 'COOKIE' not in headers:
            headers.update({'COOKIE': cookie_string})

        if self.app.session_backend and \
            self.app.session_backend == self.app.JWT_SESSION_BACKEND:
            jwt_token = self.session_jwt_string
            headers.update({'AUTHORIZATION': 'Bearer %s' % jwt_token})

        if request.META.get(
                'CONTENT_TYPE', '').startswith('multipart/form-data'):
            if request.FILES:
                requests_args['files'] = request.FILES
            data = {}
            for key, val in six.iteritems(request.POST):
                data.update({key:val})
            requests_args['data'] = data
        else:
            requests_args['data'] = request.body

        params = request.GET.copy()

        # If there's a content-length header from Django, it's probably
        # in all-caps and requests might not notice it, so just remove it.
        for key in list(headers.keys()):
            if key.lower() == 'content-length':
                del headers[key]
            elif key.lower() == 'content-type' and request.META.get(
                'CONTENT_TYPE', '').startswith('multipart/form-data'):
                del headers[key]

        requests_args['headers'] = headers
        requests_args['params'] = params
        return requests_args

    @staticmethod
    def translate_response(response):
        proxy_response = HttpResponse(
            response.content, status=response.status_code)
        if 'set-cookie' in response.headers:
            # Here we have to decode the Set-Cookie ourselves because
            # requests will pack the set-cookie headers under the same key,
            # comma separated, which comma SimpleCookie.load() will append
            # to the path in the Morsel class (ie. Path=/,).
            # This of course results in the browser not sending the cookie
            # back to us later on.
            #pylint: disable=protected-access
            if six.PY2:
                set_cookie_lines \
                    = response.raw._original_response.msg.getallmatchingheaders(
                        'Set-Cookie')
            else:
                # We implement our own search here because
                # ``getallmatchingheaders`` is broken in Python3
                # (see https://bugs.python.org/issue5053)
                set_cookie_lines = []
                for line, data in six.iteritems(
                        response.raw._original_response.msg):
                    if line.lower() == 'set-cookie':
                        set_cookie_lines.append(line + ': ' + data)

            set_cookies_cont = ''
            set_cookies = []
            for line in set_cookie_lines:
                # The parsing is complicated by the fact that
                # ``getallmatchingheaders`` will return continuation lines
                # as an entry in the list.
                if line.startswith('Set-Cookie'):
                    if set_cookies_cont:
                        set_cookies += [set_cookies_cont]
                    set_cookies_cont = line[11:].strip()
                else:
                    set_cookies_cont += line.strip()
            if set_cookies_cont:
                set_cookies += [set_cookies_cont]

            intercepted_cookies = SimpleCookie()
            for cookie_text in set_cookies:
                intercepted_cookies.load(cookie_text)
            excluded_cookies = set([
                'sessionid', # XXX hardcoded
            ])
            for key in excluded_cookies:
                if key in intercepted_cookies:
                    del intercepted_cookies[key]
            #pylint: disable=maybe-no-member
            proxy_response.cookies.update(intercepted_cookies)

        excluded_headers = set([
            'set-cookie', # Previously parsed.
            # Hop-by-hop headers
            # ------------------
            # Certain response headers should NOT be just tunneled through.
            # For more info, see:
            # http://www.w3.org/Protocols/rfc2616/rfc2616-sec13.html#sec13.5.1
            'connection', 'keep-alive', 'proxy-authenticate',
            'proxy-authorization', 'te', 'trailers', 'transfer-encoding',
            'upgrade',

            # Although content-encoding is not listed among the hop-by-hop
            # headers, it can cause trouble as well.  Just let the server set
            # the value as it should be.
            'content-encoding',

            # Since the remote server may or may not have sent the content
            # in the same encoding as Django will, let Django worry about
            # what the length should be.
            'content-length',
        ])
        for key, value in six.iteritems(response.headers):
            if key.lower() in excluded_headers:
                continue
            proxy_response[key] = value
        return proxy_response


class SessionProxyView(SessionProxyMixin, AppMixin, TemplateView):

    pass


class AppDashboardView(AppMixin, UpdateView):
    """
    Update a ``App``'s fields associated to the proxy dashboard
    (i.e. entry point and encryption key).
    """

    model = get_app_model()
    fields = ('entry_point',)
    template_name = 'rules/app_dashboard.html'

    def get_object(self, queryset=None):
        return self.app

    def get_context_data(self, **kwargs):
        #pylint:disable=too-many-locals
        context = super(AppDashboardView, self).get_context_data(**kwargs)
        rules = []
        for idx, rule in enumerate(settings.RULE_OPERATORS):
            short_name, _, defaults = rule
            parms = defaults.copy()
            look = re.search(r'%\((\S+)\)s', short_name)
            if look:
                cls_path = look.group(1)
                cls = get_model(cls_path)
                cls_name = cls_path.split('.')[-1].lower()
                try:
                    queryset = cls.objects.filter(
                        organization=self.app.account, is_active=True)
                except FieldError:
                    # The following code means we do not support optional
                    # ``organization`` foreign keys (i.e. ``null=True``).
                    try:
                        queryset = cls.objects.filter(
                            organization=self.app.account)
                    except FieldError:
                        queryset = cls.objects.all()
                for obj in queryset:
                    parms.update({cls_name: obj.slug})
                    identifier = '%d/%s' % (idx, json.dumps(parms))
                    parms.update()
                    descr = short_name % {cls_path: obj.title}
                    rules += [(identifier, descr)]
            else:
                rules += [(str(idx), short_name)]
        context.update({
            'site_available_at_url': self.request.build_absolute_uri('/'),
            'organization': self.app.account,
            'rules': rules
        })
        return context


class UserEngagementView(AppMixin, TemplateView):

    template_name = 'rules/engagement.html'
