# Copyright (c) 2018, DjaoDjin inc.
# see LICENSE
from __future__ import unicode_literals


import logging

from django.contrib.auth import get_user_model
from django.utils.translation import ugettext_lazy as _
from pages.utils import get_default_storage
from rest_framework import serializers
from rest_framework import generics
from rest_framework.response import Response
from rules.mixins import AppMixin
from rules.utils import get_current_app
from saas import settings as saas_settings
from saas.models import Signature
from saas.mixins import OrganizationMixin
from signup.api.auth import JWTRegister as JWTRegisterBase
from signup.backends.sts_credentials import aws_bucket_context
from signup.serializers import CreateUserSerializer


from ..mixins import RegisterMixin


LOGGER = logging.getLogger(__name__)


class RegisterSerializer(CreateUserSerializer):

    organization_name = serializers.CharField(required=False,
        help_text=_("Organization name that owns the billing, registered with"\
            " the user as manager"))
    street_address = serializers.CharField(required=False,
        help_text=_("Street address for the billing profile"))
    locality = serializers.CharField(required=False,
        help_text=_("City/Town for the billing profile"))
    region = serializers.CharField(required=False,
        help_text=_("State/Province/County for the billing profile"))
    postal_code = serializers.CharField(required=False,
        help_text=_("Zip/Postal Code for the billing profile"))
    country = serializers.CharField(required=False,
        help_text=_("Country for the billing profile"))
    phone = serializers.CharField(required=False,
        help_text=_("Phone number for the billing profile"))

    class Meta:
        model = get_user_model()
        fields = ('username', 'password', 'email', 'full_name',
            'organization_name', 'street_address', 'locality',
            'region', 'postal_code', 'country', 'phone')


class DjaoAppJWTRegister(AppMixin, RegisterMixin, JWTRegisterBase):
    """
    Creates a new user and optionally an associated billing
    or organization profile.

    This end point returns a JSON Web Token that can subsequently
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
        full_name = serializer.validated_data.get('full_name', None)
        if 'organization_name' in serializer.data:
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


class CredentialsSerializer(serializers.Serializer):

    location = serializers.CharField()
    access_key = serializers.CharField()
    acl = serializers.CharField()
    policy = serializers.CharField()
    signature = serializers.CharField()
    security_token = serializers.CharField()
    x_amz_credential = serializers.CharField()
    x_amz_date = serializers.CharField()

    def create(self, validated_data):
        raise NotImplementedError()

    def update(self, instance, validated_data):
        raise NotImplementedError()


class CredentialsAPIView(OrganizationMixin, generics.GenericAPIView):
    """
    .. http:get:: /api/auth/realms/:organization/

    Get temporary credentials to access S3 directly from the browser.

    **Example response**:

    .. sourcecode:: http

    {
        "url": "",
    }
    """
    serializer_class = CredentialsSerializer

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
        serializer = CredentialsSerializer(data=context)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data)
