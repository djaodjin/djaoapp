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

"""
Session Store for JWT tokens.
"""

from __future__ import absolute_import

import logging

from django.contrib.auth import (BACKEND_SESSION_KEY, HASH_SESSION_KEY,
    SESSION_KEY, authenticate)
from jwt import encode, decode

from .... import crypt
from .. import settings
from ..compat import six
from .session_base import SessionStore as SessionBase


LOGGER = logging.getLogger(__name__)


class SessionStore(SessionBase):

    def __init__(self, session_key=None):
        super(SessionStore, self).__init__(session_key=session_key)
        self._session_key_data = {}

    @property
    def data(self):
        return self._session

    @property
    def session_key_data(self):
        return self._session_key_data

    @staticmethod
    def prepare(session_data={}, #pylint: disable=dangerous-default-value
                passphrase=None):
        """
        Returns *session_dict* as a base64 encoded json string.

        """
        if passphrase is None:
            passphrase = settings.DJAODJIN_SECRET_KEY
        encoded = encode(session_data, passphrase,
            json_encoder=crypt.JSONEncoder)
        # b64encode will return `bytes` (Py3) but Django 2.0 is expecting
        # a `str` to add to the cookie header, otherwise it wraps those
        # `bytes` into a b'***' and adds that to the cookie.
        # Note that Django 1.11 will add those `bytes` to the cookie "as-is".
        if not isinstance(encoded, six.string_types):
            as_text = encoded.decode('ascii')
        else:
            as_text = encoded
        return as_text

    def load(self):
        """
        We load the data from the key itself instead of fetching from
        some external data store. Opposite of _get_session_key(),
        raises BadSignature if signature fails.

        """
        session_data = {}
        try:
            session_data = decode(self._session_key,
                settings.DJAODJIN_SECRET_KEY)
            self._session_key_data.update(session_data)
            LOGGER.debug("session data (from proxy): %s", session_data)
            # We have been able to decode the session data, let's
            # create Users and session keys expected by Django
            # contrib.auth backend.
            if 'username' in session_data:
                user = authenticate(
                    request=session_data, remote_user=session_data['username'])
                if not user:
                    raise ValueError("Cannot authenticate user.")
                session_data[SESSION_KEY] = user.id
                session_data[BACKEND_SESSION_KEY] = user.backend
                session_data[HASH_SESSION_KEY] = user.get_session_auth_hash()
                if self._local:
                    session_data_local = self._local.load()
                    LOGGER.debug("session data (local): %s", session_data_local)
                    session_data.update(session_data_local)
        except Exception as err: #pylint:disable=broad-except
            LOGGER.debug("error: %s - while loading session_key %s"\
                " with secret %s", err, self._session_key,
                settings.DJAODJIN_SECRET_KEY)
            return {}
        return session_data

    def _get_session_key(self):
        """
        Most session backends don't need to override this method, but we do,
        because instead of generating a random string, we want to actually
        generate a secure url-safe Base64-encoded string of data as our
        session key.
        """
        session_cache = getattr(self, '_session_cache', {})
        return self.prepare(session_cache)
