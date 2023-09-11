# Copyright (c) 2023, DjaoDjin inc.
# see LICENSE
from __future__ import unicode_literals

import json

from django.template import TemplateDoesNotExist
from rest_framework import status
from rest_framework.response import Response
from rest_framework.generics import GenericAPIView
from rules.mixins import AppMixin
from rules.utils import get_current_app
from saas.docs import swagger_auto_schema, no_body, OpenAPIResponse
from saas.models import get_broker
from signup.serializers_overrides import UserDetailSerializer

from ..api.serializers import ProfileSerializer
from ..compat import gettext_lazy as _
from ..notifications import send_notification
from ..views.docs import get_notification_schema
from .serializers import DetailSerializer


def get_test_notification_context(notification_slug, originated_by=None):
    schema = get_notification_schema(notification_slug)
    examples = schema.get('examples', [])
    if examples:
        # XXX We do some strange things to display the notification docs
        example = examples[0].get('requestBody', examples[0].get('resp', {}))
    else:
        example = {}
    if 'broker' in example:
        broker = get_broker()
        example.update({
            'broker': ProfileSerializer().to_representation(broker)})
    if originated_by and 'originated_by' in example:
        example.update({
            'originated_by': UserDetailSerializer().to_representation(
                originated_by)})
    return example


class NotificationAPIView(AppMixin, GenericAPIView):
    # So far this is just a dummy used in `reverse` to get a base url.
    pass


class NotificationDetailAPIView(AppMixin, GenericAPIView):

    # Even though ``GET`` will be denied, we still need to provide
    # a ``serializer_class`` because it is called before permission checks.
    http_method_names = ['post']
    serializer_class = DetailSerializer

    @swagger_auto_schema(request_body=no_body, responses={
        200: OpenAPIResponse("", DetailSerializer)})
    def post(self, request, *args, **kwargs):#pylint:disable=unused-argument
        """
        Sends a test notification e-mail

        **Tags: themes, broker, notificationmodel

        **Example

        .. code-block:: http

            POST /api/notifications/user_contact HTTP/1.1

        responds

        .. code-block:: json

            {
                "detail": "Test email sent to xia@example.com"
            }
        """
        try:
            notification_slug = self.kwargs.get('template')
            context = json.loads(self.request.data) if self.request.data else {}
            context.update(get_test_notification_context(notification_slug,
                    originated_by=self.request.user))
            recipients = []
            if self.request.user.email:
                recipients = [self.request.user.email]
            send_notification(notification_slug, context=context,
                recipients=recipients)
        except TemplateDoesNotExist:
            return Response({'detail':
                _("Problem with template. Could not send test email.")},
                status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {'detail': _("Test email sent to %(email)s") % {
                'email': request.user.email}})
