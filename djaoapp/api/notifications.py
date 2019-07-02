# Copyright (c) 2018, DjaoDjin inc.
# see LICENSE
from __future__ import unicode_literals

from django.template import TemplateDoesNotExist
from django.utils.translation import ugettext_lazy as _
from extended_templates.backends import get_email_backend
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from rules.mixins import AppMixin
from saas.models import Price, get_broker

from ..compat import reverse
from ..thread_locals import get_current_site, get_current_app


def get_test_email_context():
    broker = get_broker()
    site = get_current_site()
    return {
        # specific to charge_receipt
        'charge': {
            'price': Price(2999, 'usd'),
            'processor_key': "{{charge.processor_key}}",
            'last4': "{{charge.last4}}",
            'exp_date': "{{charge.exp_date}}",
            'created_by': {},
        },
        'email_by': {
            'username': "{{charge.email_by.username}}",
            'email': "{{charge.email_by.email}}",
            'first_name': "{{charge.email_by.first_name}}",
            'printable_name': "{{charge.email_by.printable_name}}"},
        # specific to expires_at
        'plan': {'printable_name': "{{plan.printable_name}}"},
        # specific to organization_updated
        'changes': {},
        # specific to claim_code_generated
        'subscriber': {},
        # specific to card_updated
        'old_card': {
            'last4': "{{old_card.last4}}",
            'exp_date': "{{old_card.exp_date}}"},
        'new_card': {
            'last4': "{{new_card.last4}}",
            'exp_date': "{{new_card.exp_date}}"},
        # specific to weekly_report
        'table': {},
        'date': '',
        # app_created/app_updated
        'instance': {
            'printable_name': "{{instance.printable_name}}"},
        # common across all notifications
        'urls': {
            'cart': site.as_absolute_uri(reverse('saas_cart')),
            'user': {
                'profile': None},
            'organization': {
                'profile': None}
        },
        'user': {
            'username': "{{user.username}}",
            'email': "{{user.email}}",
            'first_name': "{{user.first_name}}",
            'printable_name': "{{user.printable_name}}"},
        'organization': {
            'printable_name': "{{organization.printable_name}}"},
        'site': site, 'app': get_current_app(),
        'provider': broker, 'broker': broker
    }


class NotificationAPIView(AppMixin, APIView):
    # So far this is just a dummy used in `reverse` to get a base url.
    pass


class NotificationDetailAPIView(AppMixin, APIView):

    # Even though ``GET`` will be denied, we still need to provide
    # a ``serializer_class`` because it is called before permission checks.
    http_method_names = ['post']
    serializer_class = None

    def post(self, request, *args, **kwargs):#pylint:disable=unused-argument
        """
        Sends a test notification e-mail

        **Tags: themes

        **Example

        .. code-block:: http

            POST /api/notifications/contact_requested_notice/ HTTP/1.1

        """
        try:
            app = get_current_app()
            get_email_backend(connection=app.get_connection()).send(
                from_email=app.get_from_email(),
                recipients=[self.request.user.email],
                template="notification/%s.eml" % self.kwargs.get(
                    'template', None),
                context=get_test_email_context())
        except TemplateDoesNotExist:
            return Response({"details":
                _("Problem with template. Could not send test email.")},
                status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {"details": _("Test email sent to %(email)s") % {
                'email': request.user.email}})
