# Copyright (c) 2018, DjaoDjin inc.
# see LICENSE
from __future__ import unicode_literals


import logging

from django.contrib.auth import get_user_model
from rest_framework import serializers
from rules.mixins import AppMixin
from saas import settings as saas_settings
from saas.models import Signature
from signup.api.auth import JWTRegister as JWTRegisterBase
from signup.serializers import CreateUserSerializer

from ..mixins import RegisterMixin


LOGGER = logging.getLogger(__name__)


class RegisterSerializer(CreateUserSerializer):

    organization_name = serializers.CharField(required=False)
    street_address = serializers.CharField(required=False)
    locality = serializers.CharField(required=False)
    region = serializers.CharField(required=False)
    postal_code = serializers.CharField(required=False)
    country = serializers.CharField(required=False)
    phone = serializers.CharField(required=False)

    class Meta:
        model = get_user_model()
        fields = ('username', 'password', 'email', 'full_name',
            'organization_name', 'street_address', 'locality',
            'region', 'postal_code', 'country', 'phone')


class JWTRegister(AppMixin, RegisterMixin, JWTRegisterBase):
    """
    Creates a new user and returns a JSON Web Token that can subsequently
    be used to authenticate the new user in HTTP requests.

    **Example

    .. code-block:: http

        POST /api/auth/register/ HTTP/1.1
        {
          "username": "joe1",
          "password": "yoyo",
          "email": "joe+1@example.com",
          "full_name": "Joe Card1"
        }

    responds

    .. code-block:: http

        {
            "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VybmFtZSI6\
ImpvZTEiLCJlbWFpbCI6ImpvZSsxQGRqYW9kamluLmNvbSIsImZ1bGxfbmFtZ\
SI6IkpvZSAgQ2FyZDEiLCJleHAiOjE1Mjk2NTUyMjR9.GFxjU5AvcCQbVylF1P\
JwcBUUMECj8AKxsHtRHUSypco"
        }
    """
    serializer_class = RegisterSerializer

    def register(self, serializer):
        #pylint: disable=maybe-no-member,too-many-boolean-expressions
        registration = self.app.IMPLICIT_REGISTRATION
        full_name = serializer.validated_data.get(
            'full_name', None)
        organization_name = serializer.validated_data.get(
            'organization_name', None)
        if organization_name:
            # We have a registration of a user and organization together.
            registration = self.app.TOGETHER_REGISTRATION
            if full_name and full_name == organization_name:
                # No we have a personal registration after all
                registration = self.app.PERSONAL_REGISTRATION
        elif (serializer.validated_data.get('street_address', None) or
            serializer.validated_data.get('locality', None) or
            serializer.validated_data.get('region', None) or
            serializer.validated_data.get('postal_code', None) or
            serializer.validated_data.get('country', None) or
            serializer.validated_data.get('phone', None)):
            # We have enough information for a billing profile
            registration = self.app.PERSONAL_REGISTRATION

        if registration == self.app.PERSONAL_REGISTRATION:
            user = self.register_personal(**serializer.validated_data)
        elif registration == self.app.TOGETHER_REGISTRATION:
            user = self.register_together(**serializer.validated_data)
        else:
            user = self.register_user(**serializer.validated_data)
        if user:
            Signature.objects.create_signature(saas_settings.TERMS_OF_USE, user)
        return user
