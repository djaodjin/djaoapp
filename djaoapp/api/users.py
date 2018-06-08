# Copyright (c) 2018, DjaoDjin inc.
# see LICENSE

import logging

from django.core.files.storage import get_storage_class
from pages.mixins import get_bucket_name, get_media_prefix
from rules.utils import get_current_app
from rest_framework import generics
from rest_framework.response import Response
from rest_framework import serializers
from saas.mixins import OrganizationMixin
from signup.backends.sts_credentials import aws_bucket_context


LOGGER = logging.getLogger(__name__)


class CredentialsSerializer(serializers.Serializer):

    location = serializers.CharField()
    media_prefix = serializers.CharField(allow_blank=True)
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
        context = {}
        app = get_current_app()
        try:
            # The following statement will raise an Exception
            # when we are dealing with a ``FileSystemStorage``.
            _ = get_storage_class().bucket_name
            bucket_name = get_bucket_name(app)
            media_prefix = get_media_prefix(app)
            aws_region = context.get('aws_region', None)
            context.update(aws_bucket_context(request, bucket_name,
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
            context.update({'media_prefix': media_prefix})
        except AttributeError:
            LOGGER.debug("doesn't look like we have a S3Storage.")

        serializer = CredentialsSerializer(data=context)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data)
