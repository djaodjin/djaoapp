# Copyright (c) 2019, DjaoDjin inc.
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

import json, logging, os

from flask.sessions import SessionInterface as FlaskSessionInterface
from flask.sessions import SessionMixin
from jwt import InvalidSignatureError, decode
from werkzeug.datastructures import CallbackDict

from ... import crypt


LOGGER = logging.getLogger(__name__)
JWT_ALGORITHM = 'HS256'


class PermissionDenied(Exception):

    status_code = 403


class DjaoDjinSession(CallbackDict, SessionMixin):
    """
    Stores the decrypted session data passed by the subscription firewall.
    """

    def __init__(self, initial=None, session_key=None):
        def on_update(self):
            self.modified = True
        CallbackDict.__init__(self, initial, on_update)
        self.session_key = session_key
        self.modified = False


class DjaoDjinSessionInterface(FlaskSessionInterface):
    """
    Uses the session information passed by the DjaoDjin subscription firewall.

    The session will be decrypted using *secret_key*.

    *allowed_no_session* lists the paths which are allowed to procede
    when no session data can be found in the http request.
    """
    JWT_HEADER_NAME = 'AUTHORIZATION'
    JWT_SCHEME = 'bearer'

    session_class = DjaoDjinSession

    def __init__(self, secret_key=None, allowed_no_session=None):
        self.secret_key = secret_key
        self.allowed_no_session = (allowed_no_session
            if allowed_no_session is not None else [])

    def open_session(self, app, request):
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
        session_key = None

        jwt_header = request.headers.get(self.JWT_HEADER_NAME)
        if jwt_header:
            jwt_values = jwt_header.split(' ')
            if len(jwt_values) > 1 and \
                jwt_values[0].lower() == self.JWT_SCHEME:
                session_key = jwt_values[1]
                try:
                    session_data = decode(
                        session_key, self.secret_key, JWT_ALGORITHM)
                except (InvalidSignatureError, TypeError, ValueError) as _:
                    pass

        if not session_key:
            session_key = request.cookies.get(app.session_cookie_name)
            try:
                session_data = json.loads(crypt.decrypt(
                    session_key, passphrase=self.secret_key))
            except (IndexError, TypeError, ValueError) as _:
                # Incorrect padding in b64decode, incorrect block size in AES,
                # incorrect PKCS#5 padding or malformed json will end-up here.
                pass

        if not session_key:
            found = False
            for path in self.allowed_no_session:
                if request.path.startswith(str(path)):
                    found = True
                    break
            if not found:
                app.logger.debug("%s not found in %s", request.path,
                    [str(url) for url in self.allowed_no_session])
                raise PermissionDenied("No DjaoDjin session key")

        LOGGER.debug("decoded session data: %s", session_data)
        return self.session_class(initial=session_data, session_key=session_key)

    @staticmethod
    def save_session(app, session, response):
        #pylint:disable=unused-argument
        if session and session.modified:
            if 'csrf_token' in session:
                # XXX What is the csrf_token doing in the session?
                pass
            else:
                app.logger.debug("modified session: %s", session)
                raise RuntimeError(
                    "Session is read-only. trying to update to %s" % session)


class Session(object):
    """
    This class is used to decode a Session passed by the DjaoDjin subscription
    firewall to one or more Flask applications.

    There are two usage modes.  One is initialize the instance with a very
    specific Flask application::

        app = Flask(__name__)
        Session(app)

    The second possibility is to create the object once and configure the
    application later::

        session = Session()
        def create_app():
            app = Flask(__name__)
            session.init_app(app)
            return app
    """

    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        app.session_interface = self._get_interface(app)

    @staticmethod
    def _get_interface(app):
        config = app.config.copy()
        config.setdefault('DJAODJIN_SECRET_KEY',
            os.getenv('DJAODJIN_SECRET_KEY', ""))
        config.setdefault('ALLOWED_NO_SESSION',
            ['/api', '/api/auth/'])
        return DjaoDjinSessionInterface(
            secret_key=config['DJAODJIN_SECRET_KEY'],
            allowed_no_session=config['ALLOWED_NO_SESSION'])
