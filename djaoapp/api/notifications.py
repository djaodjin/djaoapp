# Copyright (c) 2025, DjaoDjin inc.
# see LICENSE
from __future__ import unicode_literals

import json

from django.template import TemplateDoesNotExist
from rest_framework import status
from rest_framework.response import Response
from rest_framework.generics import GenericAPIView
from rules.mixins import AppMixin
from saas.docs import extend_schema, OpenApiResponse
from saas.mixins import _as_html_description
from saas.models import get_broker
from signup.serializers_overrides import UserDetailSerializer

from ..api.serializers import ProfileSerializer
from ..compat import gettext_lazy as _
from ..notifications import send_notification
from ..api_docs.schemas import get_notification_schema
from .serializers import DetailSerializer


def get_test_notification_context(notification_slug,
                                  originated_by=None, request=None):
    schema = get_notification_schema(notification_slug,
        api_base_url=(request.build_absolute_uri('/') if request else ""))
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
    # The `TransactionSerializer` does this, but we are having a dict
    # created out of a docstring example here.
    if 'charge_items' in example:
        for charge_item in example.get('charge_items'):
            invoiced = charge_item.get('invoiced')
            descr = invoiced.get('description')
            invoiced.update({
                'description': _as_html_description(descr, request=request)
            })
    if 'invoiced_items' in example:
        for invoiced in example.get('invoiced_items'):
            descr = invoiced.get('description')
            invoiced.update({
                'description': _as_html_description(descr, request=request)
            })
    return example


class NotificationAPIView(AppMixin, GenericAPIView):
    # So far this is just a dummy used in `reverse` to get a base url.
    pass


class NotificationDetailAPIView(AppMixin, GenericAPIView):

    # Even though ``GET`` will be denied, we still need to provide
    # a ``serializer_class`` because it is called before permission checks.
    http_method_names = ['post']
    serializer_class = DetailSerializer

    @extend_schema(request=None, responses={
        200: OpenApiResponse(DetailSerializer)})
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
                    originated_by=self.request.user, request=request))
            recipients = []
            if self.request.user.email:
                recipients = [self.request.user.email]
            send_notification(notification_slug, context=context,
                request=self.request, recipients=recipients)
        except TemplateDoesNotExist:
            return Response({'detail':
                _("Problem with template. Could not send test email.")},
                status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {'detail': _("Test email sent to %(email)s") % {
                'email': request.user.email}})
