# Copyright (c) 2018, DjaoDjin inc.
# see LICENSE
from __future__ import unicode_literals

import logging

from pages.utils import get_default_storage
from rules.utils import get_current_app
from rest_framework import generics
from rest_framework.response import Response
from rest_framework import serializers
from saas.mixins import OrganizationMixin
from signup.backends.sts_credentials import aws_bucket_context


LOGGER = logging.getLogger(__name__)


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
    Get temporary credentials to access S3 directly from the browser.

    **Example

    .. code-block:: http

        POST /api/auth/tokens/realms/cowork/  HTTP/1.1

    .. code-block:: json

        {
          "url": ""
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
