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

from random import choice

from rest_framework.response import Response
from rest_framework.generics import GenericAPIView, RetrieveUpdateAPIView

from ..docs import no_body, swagger_auto_schema
from ..mixins import AppMixin
from ..utils import get_app_model
from .serializers import AppSerializer, AppKeySerializer

#pylint: disable=no-init


class GenerateKeyAPIView(AppMixin, GenericAPIView):
    """
    Generate a new key to communicate between proxy and backend service.
    """
    http_method_names = ['post']
    model = get_app_model()
    serializer_class = AppKeySerializer

    @swagger_auto_schema(request_body=no_body)
    def post(self, request, *args, **kwargs):
        """
        Rotates session encoding key

        Rotates the key used to encode the session information forwarded
        to the application entry point.

        **Tags: rbac

        **Examples

        .. code-block:: http

            POST /api/proxy/key/ HTTP/1.1

        responds

        .. code-block:: json

            {
              "enc_key": "********"
            }
        """
        #pylint:disable=unused-argument
        self.app.enc_key = "".join([
                choice("abcdefghijklmnopqrstuvwxyz0123456789!@#$%^*-_=+")
                for idx in range(16)]) #pylint: disable=unused-variable
        self.app.save()
        return Response(self.get_serializer().to_representation(self.app))


class AppUpdateAPIView(AppMixin, RetrieveUpdateAPIView):
    """
    Returns the URL endpoint to which requests passing the access rules
    are forwarded to, and the format in which the session information
    is encoded.

    When running tests, you can retrieve the actual session information
    for a specific user through the `/proxy/sessions/{user}/` API call.

    **Tags: rbac

    **Examples

    .. code-block:: http

        GET /api/proxy/ HTTP/1.1

    responds

    .. code-block:: json

        {
          "slug": "cowork",
          "entry_point": "https://cowork.herokuapp.com/",
          "session_backend": 1
        }
    """
    model = get_app_model()
    serializer_class = AppSerializer

    def get_object(self):
        return self.app

    def put(self, request, *args, **kwargs):
        """
        Updates forward end-point

        Updates the URL endpoint to which requests passing the access rules
        are forwarded to and/or the format in which the session information
        is encoded.

        **Tags: rbac

        **Examples

        .. code-block:: http

            PUT /api/proxy/ HTTP/1.1

        .. code-block:: json

            {
              "entry_point": "https://cowork.herokuapp.com/",
              "session_backend": 1
            }

        responds

        .. code-block:: json

            {
              "slug": "cowork",
              "entry_point": "https://cowork.herokuapp.com/",
              "session_backend": 1
            }
        """
        #pylint:disable=useless-super-delegation
        return super(AppUpdateAPIView, self).put(request, *args, **kwargs)
