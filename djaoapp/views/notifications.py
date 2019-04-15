# Copyright (c) 2019, DjaoDjin inc.
# see LICENSE

from django.views.generic import TemplateView
from django.utils.translation import ugettext_lazy as _
from rules.mixins import AppMixin
from saas.models import get_broker

from ..api.notifications import get_test_email_context
from ..compat import reverse


class NotificationInnerFrameView(AppMixin, TemplateView):

    template_name = 'notification/detail.html'

    def get_template_names(self):
        template_name = self.kwargs.get('template', None)
        if template_name.endswith('_role_grant_created'):
            return ["notification/%s.eml" % template_name,
                "notification/role_grant_created.eml"]
        return ["notification/%s.eml" % template_name]

    def get_context_data(self, **kwargs):
        context = super(NotificationInnerFrameView, self).get_context_data(
            **kwargs)
        context.update(get_test_email_context())
        return context


class NotificationDetailView(AppMixin, TemplateView):

    template_name = 'notification/detail.html'

    def get_context_data(self, **kwargs):
        context = super(NotificationDetailView, self).get_context_data(**kwargs)
        context.update({
            'iframe_url': reverse('notification_inner_frame',
                args=(self.kwargs.get('template'),))})
        return context


class NotificationListView(AppMixin, TemplateView):

    template_name = 'notification/index.html'

    def get_object(self, queryset=None): #pylint:disable=unused-argument
        return self.app

    def get_context_data(self, **kwargs):
        context = super(NotificationListView, self).get_context_data(**kwargs)
        broker = get_broker()
        context.update({
            'notifications': {
                'card_updated': {
                    'title': _("Card updated"),
                    'descr': _("This notification is sent when a credit card"\
" on file is updated.")
                },
                'charge_receipt': {
                    'title': _("Charge receipt"),
                    'descr': _("This notification is sent when a charge is"\
" created on a credit card. It is also sent when the charge is refunded.")
                },
                'claim_code_generated': {
                    'title': _("Claim code"),
                    'descr': _("")
                },
                'expires_soon': {
                    'title': _("Expires soon"),
                    'descr': _("This notification is sent when a subscription"\
" is about to expire.")
                },
                'order_executed': {
                    'title': _("Order confirmation"),
                    'descr': _("This notification is sent when an order has"\
" been confirmed but a charge has been successfuly processed yet.")
                },
                'organization_updated': {
                    'title': _("Profile updated"),
                    'descr': _("This notification is sent when a profile"\
" is updated.")
                },
                'password_reset': {
                    'title': _("Password reset"),
                    'descr': _("This notification is sent to a user that has"\
" requested to reset their password through a \"forgot password?\" link.")
                },
                'user_activated': {
                    'title': _("User activated"),
                    'descr': _("This notification is sent to profile managers"\
" of a domain when a user has activated his/her account.")
                },
                'user_contact': {
                    'title': _("User contact"),
                    'descr': _("")
                },
                'user_registered': {
                    'title': _("User registered"),
                    'descr': _("This notification is sent to profile managers"\
" of a domain when a user has registered.")
                },
                'user_relation_requested': {
                    'title': _("User relation requested"),
                    'descr': _("This notification is sent to profile managers"\
" of an organization when a user has requested a role on that organization.")
                },
                'verification': {
                    'title': _("Verification"),
                    'descr': _("This notification is sent to verify an e-mail"\
" address of a user.")
                },
                'sales_report': {
                    'title': _("Weekly sales report"),
                    'descr': _("This notification is sent to profile managers."\
" It contains the weekly sales results.")
                },
            },
            'role_descriptions': broker.get_role_descriptions()
        })
        self.update_context_urls(context, {
            'send_test_email': reverse('api_notification_base')
        })
        return context
