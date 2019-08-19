# Copyright (c) 2019, DjaoDjin inc.
# see LICENSE
from __future__ import unicode_literals

import logging

from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from multitier.thread_locals import get_current_site
from saas.backends import load_backend
from saas.views.billing import (
    ProcessorAuthorizeView as BaseProcessorAuthorizeView)
from saas.views.profile import DashboardView as BaseDashboardView
from saas.utils import is_broker, update_context_urls
from saas.backends.stripe_processor.views import (
    StripeProcessorRedirectView as BaseStripeProcessorRedirectView)
from ..compat import reverse


LOGGER = logging.getLogger(__name__)


class DashboardView(BaseDashboardView):

    def get_context_data(self, **kwargs):
        context = super(DashboardView, self).get_context_data(**kwargs)
        if is_broker(self.organization):
            update_context_urls(context, {
                'recent_activity': reverse('api_recent_activity'),
                'api_todos': reverse('api_todos')
            })
        return context


class ProcessorAuthorizeView(BaseProcessorAuthorizeView):

    @property
    def processor_backend(self):
        if not hasattr(self, '_processor_backend'):
            self._processor_backend = load_backend(
                settings.SAAS.get('PROCESSOR', {
                    'BACKEND': 'saas.backends.stripe_processor.StripeBackend'
                }).get(
                    'BACKEND', 'saas.backends.stripe_processor.StripeBackend'))
        return self._processor_backend

    def connect_auth(self, auth_code):
        site = get_current_site()
        try:
            livemode = int(self.request.GET.get('livemode', 1))
        except ValueError:
            livemode = 1
        if livemode:
            site.remove_tags(['testing'])
        else:
            site.add_tags(['testing'])
            self.processor_backend.pub_key = settings.STRIPE_TEST_PUB_KEY
            self.processor_backend.priv_key = settings.STRIPE_TEST_PRIV_KEY
            self.processor_backend.client_id = settings.STRIPE_TEST_CLIENT_ID
        site.save()
        self.processor_backend.connect_auth(self.object, auth_code)

    def get_context_data(self, **kwargs):
        context = super(ProcessorAuthorizeView, self).get_context_data(**kwargs)
        provider = self.organization

        kwargs = {}
        if (hasattr(settings, 'STRIPE_CONNECT_CALLBACK_URL') and
            settings.STRIPE_CONNECT_CALLBACK_URL):
            kwargs = {
                'redirect_uri': settings.STRIPE_CONNECT_CALLBACK_URL,
            }
        authorize_url = self.processor_backend.get_authorize_url(
            provider, **kwargs)
        if authorize_url:
            update_context_urls(context, {
                'authorize_processor': authorize_url
            })
        if (hasattr(settings, 'STRIPE_TEST_CONNECT_CALLBACK_URL') and
            settings.STRIPE_TEST_CONNECT_CALLBACK_URL):
            authorize_url = self.processor_backend.get_authorize_url(
                provider, client_id=settings.STRIPE_TEST_CLIENT_ID,
                redirect_uri=settings.STRIPE_TEST_CONNECT_CALLBACK_URL)
            if authorize_url:
                update_context_urls(context, {
                    'authorize_processor_test': authorize_url
                })
        return context


class StripeProcessorRedirectView(BaseStripeProcessorRedirectView):

    def get_redirect_url(self, *args, **kwargs):
        url = super(StripeProcessorRedirectView, self).get_redirect_url(
            *args, **kwargs)
        if self.request.path.endswith('/test/'):
            url += "&livemode=0"
        return url
