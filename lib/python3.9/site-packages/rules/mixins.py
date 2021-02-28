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

import logging

from deployutils.apps.django.backends.encrypted_cookies import (
    SessionStore as CookieSessionStore)
from deployutils.apps.django.backends.jwt_session_store import (
    SessionStore as JWTSessionStore)
from deployutils.apps.django.settings import SESSION_COOKIE_NAME
from django.contrib.auth import get_user_model
from django.utils.module_loading import import_string
from rest_framework.generics import get_object_or_404

from . import settings
from .compat import is_authenticated, six
from .models import Engagement
from .utils import datetime_or_now
from .extras import AppMixinBase


LOGGER = logging.getLogger(__name__)


class AppMixin(AppMixinBase, settings.EXTRA_MIXIN):
    pass


class EngagementMixin(object):
    """
    Records ``Engagement`` with a ``App``.
    """
    engagement_trigger = 'default'

    @property
    def last_visited(self):
        if not hasattr(self, '_last_visited'):
            self._last_visited = None
            if is_authenticated(self.request):
                engagement, created = Engagement.objects.get_or_create(
                    slug=self.engagement_trigger, user=self.request.user)
                if created:
                    # Avoid too many INSERT statements
                    engagement.last_visited = datetime_or_now()
                    engagement.save()
                    LOGGER.info("initial '%s' engagement with %s",
                        self.engagement_trigger, self.request.path)
                else:
                    self._last_visited = engagement.last_visited
        return self._last_visited

    def get_context_data(self, **kwargs):
        context = super(EngagementMixin, self).get_context_data(**kwargs)
        context.update({'last_visited': self.last_visited})
        return context


class SessionDataMixin(object):

    @staticmethod
    def serialize_request(request, app, rule):
        if is_authenticated(request):
            #pylint: disable=no-member
            serializer_class = import_string(settings.SESSION_SERIALIZER)
            serializer = serializer_class(request, context={
                'app': app, 'rule': rule})
            return serializer.data
        return {}

    @property
    def session_cookie_string(self):
        """
        Return the encrypted session information
        added to the HTTP Cookie Headers.
        """
        if not hasattr(self, '_session_cookie_string'):
            self._session_cookie_string = self.get_session_cookie_string(
                self.request, self.app, self.rule, self.session)
        return self._session_cookie_string

    def get_session_cookie_string(self, request, app, rule, session):
        # This is the latest time we can populate the session
        # since after that we need it to encrypt the cookie string.
        session.update(self.serialize_request(request, app, rule))
        session_store = CookieSessionStore(app.enc_key)
        session_token = session_store.prepare(session, app.enc_key)
        if not isinstance(session_token, six.string_types):
            # Because we don't want Python3 to prefix our strings with b'.
            session_token = session_token.decode('ascii')
        return session_token

    @property
    def session_jwt_string(self):
        """
        Return the encrypted session information
        encoded as a JWT token.
        """
        if not hasattr(self, '_session_jwt_string'):
            self._session_jwt_string = self.get_session_jwt_string(
                self.request, self.app, self.rule, self.session)
        return self._session_jwt_string

    def get_session_jwt_string(self, request, app, rule, session):
        # This is the latest time we can populate the session
        # since after that we need it to encrypt the cookie string.
        session.update(self.serialize_request(request, app, rule))
        session_store = JWTSessionStore(app.enc_key)
        session_token = session_store.prepare(session, app.enc_key)
        if not isinstance(session_token, six.string_types):
            # Because we don't want Python3 to prefix our strings with b'.
            session_token = session_token.decode('ascii')
        return session_token

    @property
    def forward_session_header(self):
        if not hasattr(self, '_forward_session_header'):
            if self.app.session_backend == self.app.JWT_SESSION_BACKEND:
                self._forward_session_header = "%s: %s" % (
                    SESSION_COOKIE_NAME, self.session_jwt_string)
            else:
                line = "%s: %s" % (SESSION_COOKIE_NAME,
                    self.session_cookie_string)
                self._forward_session_header = '\\\n'.join(
                    [line[i:i+48] for i in range(0, len(line), 48)])
        return self._forward_session_header

    def get_forward_session_header(self, request, app, rule, session):
        if app.session_backend == app.JWT_SESSION_BACKEND:
            forward_session_header = ("Authorization: Bearer %s" %
                self.get_session_jwt_string(request, app, rule, session))
        else:
            line = "Cookie: %s=%s" % (SESSION_COOKIE_NAME,
                self.get_session_cookie_string(request, app, rule, session))
            forward_session_header = '\\\n'.join(
                [line[i:i+48] for i in range(0, len(line), 48)])
        return forward_session_header


class UserMixin(object):

    user_field = 'username'
    user_url_kwarg = 'user'

    @property
    def user(self):
        if not hasattr(self, '_user'):
            slug = self.kwargs.get(self.user_url_kwarg)
            if getattr(self.request.user, self.user_field) == slug:
                # Not only do we avoid one database query, we also
                # make sure the user is the actual wrapper object.
                self._user = self.request.user
            else:
                kwargs = {self.user_field: slug}
                self._user = get_object_or_404(
                    get_user_model().objects.all(), **kwargs)
        return self._user
