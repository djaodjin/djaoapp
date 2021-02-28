# Copyright (c) 2019, Djaodjin Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
# OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
# OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
# ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from django.utils.translation import ugettext_lazy as _
from rest_framework import exceptions
from rest_framework.authentication import (BasicAuthentication,
    TokenAuthentication)

from .models import Credentials
from .utils import verify_token


class APIKeyAuthentication(BasicAuthentication):

    model = Credentials

    def authenticate_credentials(self, userid, password, request=None):
        #pylint:disable=unused-argument
        pub_key = userid[0:self.model.API_PUB_KEY_LENGTH]
        priv_key = userid[self.model.API_PUB_KEY_LENGTH:]
        try:
            token = self.model.objects.select_related('user').get(
                api_pub_key=pub_key)
        except self.model.DoesNotExist:
            raise exceptions.AuthenticationFailed(_('Invalid token'))

        if not token.check_priv_key(priv_key):
            raise exceptions.AuthenticationFailed(_('Invalid token'))

        is_active = getattr(token.user, 'is_active', None)
        if not (is_active or is_active is None):
            raise exceptions.AuthenticationFailed(
                _('User inactive or deleted.'))

        return (token.user, token)



class JWTAuthentication(TokenAuthentication):

    keyword = 'Bearer'

    def authenticate_credentials(self, key):
        user = None
        try:
            user = verify_token(key)
        except exceptions.ValidationError:
            raise exceptions.AuthenticationFailed(_('Invalid token'))

        return (user, key)
