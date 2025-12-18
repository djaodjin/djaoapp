# Copyright (c) 2025, DjaoDjin inc.
# see LICENSE
from __future__ import unicode_literals

import logging

from django.conf import settings
from saas import settings as saas_settings
from saas.models import get_broker
from saas.backends.stripe_processor.views import (
    StripeProcessorRedirectView as BaseStripeProcessorRedirectView)
from saas.views.billing import (
    ProcessorAuthorizeView as BaseProcessorAuthorizeView)
from saas.views.extra import (
    PrintableChargeReceiptView as PrintableChargeReceiptBaseView)
from saas.views.profile import (DashboardView as BaseDashboardView,
    OrganizationProfileView as OrganizationProfileViewBase)
from saas.helpers import update_context_urls
from signup.models import get_user_contact

from ..compat import reverse
from ..forms.profile import PersonalProfileForm
from ..notifications.signals import get_charge_updated_context
from ..notifications.serializers import ChargeNotificationSerializer
from ..thread_locals import dynamic_processor_keys


LOGGER = logging.getLogger(__name__)


class DashboardView(BaseDashboardView):

    def get_context_data(self, **kwargs):
        context = super(DashboardView, self).get_context_data(**kwargs)
        if self.organization.is_broker:
            update_context_urls(context, {
                'recent_activity': reverse('api_recent_activity'),
                'api_todos': reverse('api_todos')
            })
        return context


class ProcessorAuthorizeView(BaseProcessorAuthorizeView):

    def get_context_data(self, **kwargs):
        context = super(ProcessorAuthorizeView, self).get_context_data(**kwargs)
        if settings.ENABLES_PROCESSOR_TEST_KEYS:
            provider = self.organization
            processor_backend = dynamic_processor_keys(provider, testmode=True)
            authorize_url = processor_backend.get_authorize_url(provider)
            if authorize_url:
                update_context_urls(context, {
                    'authorize_processor_test': authorize_url
                })
        return context


class OrganizationProfileView(OrganizationProfileViewBase):

    @property
    def contact(self):
        if not hasattr(self, '_contact'):
            #pylint:disable=attribute-defined-outside-init
            self._contact = get_user_contact(self.object.attached_user())
        return self._contact


    def get_context_data(self, **kwargs):
        context = super(OrganizationProfileView, self).get_context_data(
            **kwargs)
        if self.contact:
            context.update({
                'email_verified_at': self.contact.email_verified_at,
                'phone_verified_at': self.contact.phone_verified_at
            })
        broker = get_broker()
        user = self.request.user
        if user and broker.with_role(saas_settings.MANAGER).filter(
                pk=user.pk).exists():
            # If we have a request user who is a profile manager for the broker,
            # we will display the activity notes for the profile.
            update_context_urls(context, {
                'api_activities': reverse('api_profile_activities', args=(
                    self.object,)),
                'api_candidates': reverse('saas_api_search_users'),
            })
        return context

    def get_form_class(self):
        if self.object.attached_user():
            # There is only one user so we will add the User fields
            # to the form so they can be updated at the same time.
            return PersonalProfileForm
        return super(OrganizationProfileView, self).get_form_class()

    def get_initial(self):
        kwargs = super(OrganizationProfileView, self).get_initial()
        if self.object.attached_user():
            if self.contact:
                kwargs.update({'lang': self.contact.lang})
        return kwargs


class StripeProcessorRedirectView(BaseStripeProcessorRedirectView):

    def get_redirect_url(self, *args, **kwargs):
        url = super(StripeProcessorRedirectView, self).get_redirect_url(
            *args, **kwargs)
        if self.request.path.endswith('/test/'):
            url += "&livemode=0"
        return url


class PrintableChargeReceiptView(PrintableChargeReceiptBaseView):

    def get_context_data(self, **kwargs):
        context = ChargeNotificationSerializer().to_representation(
            get_charge_updated_context(self.get_object()))
        return context
