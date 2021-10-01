# Copyright (c) 2021, DjaoDjin inc.
# see LICENSE
from __future__ import unicode_literals


import logging

from django.utils.translation import ugettext_lazy as _
from pages.utils import get_default_storage
from rest_framework import serializers
from rest_framework import generics
from rest_framework.response import Response
from rules.mixins import AppMixin
from rules.utils import get_current_app
from saas.models import Agreement
from saas.mixins import OrganizationMixin
from signup.api.auth import JWTRegister as JWTRegisterBase
from signup.backends.sts_credentials import aws_bucket_context

from ..mixins import RegisterMixin
from .serializers import RegisterSerializer


LOGGER = logging.getLogger(__name__)


class DjaoAppJWTRegister(AppMixin, RegisterMixin, JWTRegisterBase):
    """
    Registers a user

    Creates a new user and returns a JSON Web Token that can subsequently
    be used to authenticate the new user in HTTP requests.

    The API is typically used within an HTML
    `register page </docs/themes/#workflow_register>`_
    as present in the default theme.

    **Tags: auth, visitor, usermodel

    **Example

    .. code-block:: http

        POST /api/auth/register/ HTTP/1.1

    .. code-block:: json

        {
          "username": "joe1",
          "password": "yoyo",
          "email": "joe+1@example.com",
          "full_name": "Joe Card1"
        }

    responds

    .. code-block:: json

        {
            "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VybmFtZSI6\
ImpvZTEiLCJlbWFpbCI6ImpvZSsxQGRqYW9kamluLmNvbSIsImZ1bGxfbmFtZ\
SI6IkpvZSAgQ2FyZDEiLCJleHAiOjE1Mjk2NTUyMjR9.GFxjU5AvcCQbVylF1P\
JwcBUUMECj8AKxsHtRHUSypco"
        }
    """
    serializer_class = RegisterSerializer

    def get_serializer_class(self):
        serializer_class = super(
            DjaoAppJWTRegister, self).get_serializer_class()
        for agreement in Agreement.objects.all():
            #pylint:disable=protected-access
            serializer_class._declared_fields[agreement.slug] = \
                serializers.CharField(required=False, help_text=agreement.title)
            serializer_class.Meta.fields += (agreement.slug,)
        return serializer_class

    def register(self, serializer):
        #pylint: disable=maybe-no-member,too-many-boolean-expressions
        registration = serializer.validated_data.get('type',
            self.app.IMPLICIT_REGISTRATION)
        full_name = serializer.validated_data.get('full_name', None)
        if 'organization_name' in serializer.validated_data:
            # We have a registration of a user and organization together.
            registration = self.app.TOGETHER_REGISTRATION
            organization_name = serializer.validated_data.get(
                'organization_name', None)
            if full_name and full_name == organization_name:
                # No we have a personal registration after all
                registration = self.app.PERSONAL_REGISTRATION
        elif (serializer.validated_data.get('street_address', None) or
            serializer.validated_data.get('locality', None) or
            serializer.validated_data.get('region', None) or
            serializer.validated_data.get('postal_code', None) or
            serializer.validated_data.get('country', None)):
            # We have enough information for a billing profile
            registration = self.app.PERSONAL_REGISTRATION

        if registration == self.app.PERSONAL_REGISTRATION:
            user = self.register_personal(**serializer.validated_data)
        elif registration == self.app.TOGETHER_REGISTRATION:
            user = self.register_together(**serializer.validated_data)
        else:
            user = self.register_user(**serializer.validated_data)
        return user


class AuthRealmsSerializer(serializers.Serializer):

    location = serializers.CharField(
        help_text=_("URL to upload files"))
    access_key = serializers.CharField(
        help_text=_("Access key"))
    acl = serializers.CharField(
        help_text=_("ACL (i.e. private or public-read)"))
    policy = serializers.CharField(
        help_text=_("Policy"))
    signature = serializers.CharField(
        help_text=_("Signature"))
    security_token = serializers.CharField(
        help_text=_("Security token"))
    x_amz_credential = serializers.CharField(
        help_text=_("AMZ Credential"))
    x_amz_date = serializers.CharField(
        help_text=_("AMZ Date"))

    def create(self, validated_data):
        raise NotImplementedError()

    def update(self, instance, validated_data):
        raise NotImplementedError()


class CredentialsAPIView(OrganizationMixin, generics.RetrieveAPIView):
    """
    Retrieves temporary credentials

    Gets temporary credentials to access S3 directly from the browser.

    **Examples

    .. code-block:: http

        GET  /api/auth/tokens/realms/cowork/ HTTP/1.1

    responds

    .. code-block:: json

        {
          "location":"https://cowork.s3-us-east-1.amazonaws.com/",
          "access_key":"*********",
          "acl":"public-read",
          "policy":"*********",
          "signature":"*********",
          "security_token":"*********",
          "x_amz_credential":"*********/20190808/us-east-1/s3/aws4_request",
          "x_amz_date":"20190808T000000Z"
        }
    """
    serializer_class = AuthRealmsSerializer

    def get(self, request, *args, **kwargs):
        #pylint:disable=unused-argument,no-self-use
        context = {}
        app = get_current_app()
        try:
            storage = get_default_storage(request, account=app.account)
            # The following statement will raise an Exception
            # when we are dealing with a ``FileSystemStorage``.
            location = "s3://%s/%s" % (storage.bucket_name, storage.location)
            aws_region = context.get('aws_region', None)
            context.update(aws_bucket_context(request, location,
                aws_upload_role=app.role_name,
                aws_external_id=app.external_id,
                aws_region=aws_region,
                acls=['private', 'public-read']))
            if request.query_params.get('public', False):
                context.update({
                    'policy': context['public_read_aws_policy'],
                    'signature': context['public_read_aws_policy_signature'],
                })
            else:
                context.update({
                    'policy': context['private_aws_policy'],
                    'signature': context['private_aws_policy_signature'],
                })
        except AttributeError:
            LOGGER.debug("doesn't look like we have a S3Storage.")
        serializer = self.get_serializer(data=context)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data)
