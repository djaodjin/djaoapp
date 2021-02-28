# Copyright (c) 2018, DjaoDjin inc.
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

from django.contrib.auth import (BACKEND_SESSION_KEY, HASH_SESSION_KEY,
    SESSION_KEY)
from django.contrib.sessions.backends.signed_cookies import SessionStore \
    as SessionBase
from django.contrib.sessions.models import Session

from .. import settings
from ..compat import import_string


class SessionStore(SessionBase):

    def __init__(self, session_key=None):
        super(SessionStore, self).__init__(session_key=session_key)
        self._local = None
        if settings.BACKEND_SESSION_STORE:
            local_cls = import_string(settings.BACKEND_SESSION_STORE)
            self._local = local_cls()

    @property
    def session_key_content(self):
        return self._session_key

    def __getitem__(self, key):
        return self._session[key]

    def __setitem__(self, key, value):
        self._session[key] = value
        if self._local:
            self._local[key] = value
        self.modified = True

    def __delitem__(self, key):
        del self._session[key]
        if self._local:
            del self._local[key]
        self.modified = True

    @property
    def local_data(self):
        if self._local:
            #pylint:disable=protected-access
            return self._local._session
        return {}

    def load(self):
        local_session_data = {}
        if self._local:
            local_session_data = self._local.load()
        return local_session_data

    def save(self, must_create=False):
        if self._local:
            self._local[SESSION_KEY] = self._session.get(SESSION_KEY, None)
            self._local[BACKEND_SESSION_KEY] = self._session.get(
                BACKEND_SESSION_KEY, None)
            self._local[HASH_SESSION_KEY] = self._session.get(
                HASH_SESSION_KEY, None)
            # db backend session_key max_length = 40
            #pylint:disable=protected-access
            max_length = Session._meta.get_field('session_key').max_length
            session_key = self.session_key[:max_length]
            self._local._session_key = session_key
            self._local.save(must_create=not self._local.exists(session_key))
