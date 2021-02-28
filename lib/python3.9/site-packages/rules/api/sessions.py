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

import json

from rest_framework.response import Response
from rest_framework.generics import GenericAPIView, RetrieveAPIView

from ..mixins import AppMixin, SessionDataMixin, UserMixin
from ..utils import JSONEncoder
from .serializers import SessionDataSerializer


class GetSessionDataRequest(object):

    def __init__(self, user):
        self.user = user


class GetSessionAPIView(GenericAPIView):
    # So far this is just a dummy used in `reverse` to get a base url.
    pass


class GetSessionDetailAPIView(SessionDataMixin, AppMixin, UserMixin,
                            RetrieveAPIView):
    """
    Retrieves example session

    Returns a session data for a user as it will be passed to the backend
    service.

    **Tags: rbac

    **Examples

    .. code-block:: http

        GET /api/proxy/sessions/xia/ HTTP/1.1

    responds

    .. code-block:: json

        {
          "forward_session": "{username: xia}",
          "forward_session_header": "Authorization: XXX",
          "forward_url": "https://cowork.herokuapp.com/"
        }
    """
    serializer_class = SessionDataSerializer

    def retrieve(self, request, *args, **kwargs):
        rule = None
        session = {}
        forward_session_header = self.get_forward_session_header(
            GetSessionDataRequest(self.user), self.app, rule, session)
        # Order of `forward_session_header =` and `forward_session =`
        # is important because of the call to `serialize_request`.
        forward_session = json.dumps(
            session, indent=2, cls=JSONEncoder)
        serializer = self.get_serializer({
            'forward_session': forward_session,
            'forward_session_header': forward_session_header,
            'forward_url': self.app.entry_point})
        return Response(serializer.data)
