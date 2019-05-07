# Copyright (c) 2019, DjaoDjin inc.
# see LICENSE

from django.utils.translation import ugettext_lazy as _
from multitier.mixins import build_absolute_uri
from multitier.thread_locals import get_current_site
from saas.models import get_broker
from pages.views.themes import (
    ThemePackagesView as  ThemePackageBaseView,
    ThemePackageDownloadView as ThemePackageDownloadBaseView)

from ..compat import reverse


class ThemePackageView(ThemePackageBaseView):

    def get_context_data(self, **kwargs):
        context = super(ThemePackageView, self).get_context_data(**kwargs)
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
                    'descr': _("This notification is sent to the user invited"\
" through a groupBuy.")
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
                    'descr': _("This notification is sent to profile managers"\
" of a domain when a user submits an inquiry on the contact-us page.")
                },
                'user_registered': {
                    'title': _("User registered"),
                    'descr': _("This notification is sent to profile managers"\
" of a domain when a user has registered.")
                },
                'role_requested': {
                    'title': _("Role requested"),
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
        context.update({'site_available_at_url': build_absolute_uri(
            self.request, site=get_current_site().db_object)})
        return context


class ThemePackageDownloadView(ThemePackageDownloadBaseView):

    @property
    def theme(self):
        if not hasattr(self, '_theme'):
            self._theme = self.app.slug
        return self._theme
