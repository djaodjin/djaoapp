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

import datetime, logging

from flask import current_app as app, request, jsonify
import jwt

from ...helpers import as_timestamp, datetime_or_now


LOGGER = logging.getLogger(__name__)
JWT_ALGORITHM = 'HS256'

def api():
    return jsonify({'version': "1.0"})


def api_login():
    content = request.json
    username = content.get('username')
    exp = as_timestamp(datetime_or_now() + datetime.timedelta(days=1))
    payload = app.config['MOCKUP_SESSIONS'].get(username)
    payload.update({'exp': exp})
    token = jwt.encode(payload,
        app.config['DJAODJIN_SECRET_KEY'], JWT_ALGORITHM).decode('utf-8')
    return jsonify({'token': token})


def api_tokens():
    content = request.json
    token = content.get('token')
    payload = jwt.decode(
        token,
        app.config['DJAODJIN_SECRET_KEY'],
        True, # verify
        options={'verify_exp': True},
        algorithms=[JWT_ALGORITHM])
    username = payload.get('username', None)
    exp = as_timestamp(datetime_or_now() + datetime.timedelta(days=1))
    payload = app.config['MOCKUP_SESSIONS'].get(username)
    payload.update({'exp': exp})
    token = jwt.encode(payload,
        app.config['DJAODJIN_SECRET_KEY'], JWT_ALGORITHM).decode('utf-8')
    return jsonify({'token': token})
