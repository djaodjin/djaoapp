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
Session Store for encrypted cookies.
"""

from __future__ import absolute_import

import logging, json

from django.contrib.auth import (BACKEND_SESSION_KEY, HASH_SESSION_KEY,
    SESSION_KEY, authenticate)

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
        Returns *session_dict* as a base64 encrypted json string.

        The full encrypted text is special crafted to be compatible
        with openssl. It can be decrypted with:

          $ echo _full_encypted_ | openssl aes-256-cbc -d -a -k _passphrase_ -p
          salt=...
          key=...
          iv=...
          _json_formatted_
        """
        if passphrase is None:
            passphrase = settings.DJAODJIN_SECRET_KEY
        encrypted = crypt.encrypt(
            json.dumps(session_data, cls=crypt.JSONEncoder),
            passphrase=passphrase,
            debug_stmt="encrypted_cookies.SessionStore.prepare")
        # b64encode will return `bytes` (Py3) but Django 2.0 is expecting
        # a `str` to add to the cookie header, otherwise it wraps those
        # `bytes` into a b'***' and adds that to the cookie.
        # Note that Django 1.11 will add those `bytes` to the cookie "as-is".
        if not isinstance(encrypted, six.string_types):
            as_text = encrypted.decode('ascii')
        else:
            as_text = encrypted
        return as_text

    def load(self):
        """
        We load the data from the key itself instead of fetching from
        some external data store. Opposite of _get_session_key(),
        raises BadSignature if signature fails.

          $ echo '_json_formatted_' | openssl aes-256-cbc -a -k _passphrase_ -p
          salt=...
          key=...
          iv=...
          _full_encrypted_
        """
        session_data = {}
        try:
            session_text = crypt.decrypt(self._session_key,
                passphrase=settings.DJAODJIN_SECRET_KEY,
                debug_stmt="encrypted_cookies.SessionStore.load")
            session_data = json.loads(session_text)
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
        except (IndexError, TypeError, ValueError) as err:
            # Incorrect padding in b64decode, incorrect block size in AES,
            # incorrect PKCS#5 padding or malformed json will end-up here.
            LOGGER.debug("error: while loading session, %s", err)
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
