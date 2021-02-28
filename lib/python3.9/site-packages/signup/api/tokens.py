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

from django.core.exceptions import PermissionDenied
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from .auth import JWTBase
from ..docs import OpenAPIResponse, swagger_auto_schema
from ..serializers import TokenSerializer, ValidationErrorSerializer
from ..utils import verify_token as verify_token_base


LOGGER = logging.getLogger(__name__)


class JWTVerify(JWTBase):
    """
    Verifies a JSON Web Token

    The authenticated user and the user associated to the token should be
    identical.

    **Tags: auth

    **Example

    .. code-block:: http

        POST /api/auth/tokens/verify/ HTTP/1.1

    .. code-block:: json

        {
            "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2V\
ybmFtZSI6ImRvbm55IiwiZW1haWwiOiJzbWlyb2xvKzRAZGphb2RqaW4uY2\
9tIiwiZnVsbF9uYW1lIjoiRG9ubnkgQ29vcGVyIiwiZXhwIjoxNTI5NjU4N\
zEwfQ.F2y1iwj5NHlImmPfSff6IHLN7sUXpBFmX0qjCbFTe6A"
        }

    responds

    .. code-block:: json

        {
            "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2V\
ybmFtZSI6ImRvbm55IiwiZW1haWwiOiJzbWlyb2xvKzRAZGphb2RqaW4uY2\
9tIiwiZnVsbF9uYW1lIjoiRG9ubnkgQ29vcGVyIiwiZXhwIjoxNTI5NjU4N\
zEwfQ.F2y1iwj5NHlImmPfSff6IHLN7sUXpBFmX0qjCbFTe6A"
        }
    """
    serializer_class = TokenSerializer

    @staticmethod
    def verify_token(token):
        return verify_token_base(token)

    @swagger_auto_schema(responses={
        200: OpenAPIResponse("Token is valid", TokenSerializer),
        400: OpenAPIResponse("Token is invalid", ValidationErrorSerializer)})
    def post(self, request, *args, **kwargs): #pylint:disable=unused-argument
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            token = serializer.validated_data['token']
            if self.request.user == self.verify_token(token):
                return Response({'token': token})
        raise ValidationError("token is invalid")


class JWTRefresh(JWTVerify):
    """
    Refreshes a JSON Web Token

    Refreshes a JSON Web Token by verifying the token and creating
    a new one that expires further in the future.

    The authenticated user and the user associated to the token should be
    identical.

    **Tags: auth

    **Example

    .. code-block:: http

        POST /api/auth/tokens/ HTTP/1.1

    .. code-block:: json

        {
            "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2V\
ybmFtZSI6ImRvbm55IiwiZW1haWwiOiJzbWlyb2xvKzRAZGphb2RqaW4uY2\
9tIiwiZnVsbF9uYW1lIjoiRG9ubnkgQ29vcGVyIiwiZXhwIjoxNTI5NjU4N\
zEwfQ.F2y1iwj5NHlImmPfSff6IHLN7sUXpBFmX0qjCbFTe6A"
        }

    responds

    .. code-block:: json

        {
            "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VybmFt\
ZSI6ImRvbm55IiwiZW1haWwiOiJzbWlyb2xvKzRAZGphb2RqaW4uY29tIiw\
iZnVsbF9uYW1lIjoiRG9ubnkgQ29vcGVyIiwiZXhwIjoxNTI5Njk1NjA1fQ\
.-uuZb8R68jWw1Tc9FJocOWe1KHFklRffXbH0Rg6d_0c"
        }
    """
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            token = serializer.validated_data['token']
            user = super(JWTRefresh, self).verify_token(token)
            if self.request.user == user:
                return self.create_token(user)
        raise PermissionDenied()
