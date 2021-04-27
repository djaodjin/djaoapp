# Copyright (c) 2021, DjaoDjin inc.
# see LICENSE

from __future__ import absolute_import

from django.conf import settings

from multitier.thread_locals import get_current_site
from pages.extras import AccountMixinBase
from rules.extras import AppMixinBase
from rules.utils import get_current_app

from ..compat import reverse

# matches definitions in `saas.backends.stripe_processor.base.StripeBackend`.
STRIPE_CONNECT_LOCAL = 0
STRIPE_CONNECT_FORWARD = 1
STRIPE_CONNECT_REMOTE = 2


class ExtraMixin(AppMixinBase, AccountMixinBase):

    # matches definition in `saas.backends.stripe_processor.base.StripeBackend`.
    @staticmethod
    def _is_platform(provider):
        #pylint:disable=protected-access
        return provider._state.db == 'default' and provider.is_broker

    def get_context_data(self, **kwargs):
        context = super(ExtraMixin, self).get_context_data(**kwargs)

        # Flags used in saas/_body_top_template.html to show how processor
        # handles cards and charges.
        #   if broker not configured
        #      return configure_broker()
        #   if broker in testmode
        #      return configure_broker_livemode()
        #   if provider not connected
        #      return connect_provider()
        #   if provider in testmode
        #      return connect_provider_livemode()
        app = get_current_app()
        # ``app.account`` is guarenteed to be in the same database as ``app``.
        # ``site.account`` is always in the *default* database, which is not
        # the expected database ``Organization`` are typically queried from.

        # XXX Relying on settings instead of saas_settings to cut down
        # on imports. `requires_provider_keys` matches definition
        # in `saas.backends.stripe_processor.base.StripeBackend`.
        broker_pub_key = getattr(settings, 'STRIPE_PUB_KEY', None)
        processor_backend_mode = settings.SAAS.get(
            'PROCESSOR', STRIPE_CONNECT_LOCAL).get(
            'MODE', STRIPE_CONNECT_LOCAL)
        requires_provider_keys = (processor_backend_mode in (
            STRIPE_CONNECT_FORWARD, STRIPE_CONNECT_REMOTE) and
            not self._is_platform(app.account))
        provider_pub_key = app.account.processor_pub_key

        processor_hint = None
        if not broker_pub_key:
            processor_hint = 'configure_broker'
        elif requires_provider_keys and not provider_pub_key:
            processor_hint = 'connect_provider'
        elif not broker_pub_key.startswith('pk_live_'):
            processor_hint = 'configure_broker_livemode'
        elif (requires_provider_keys and
              not provider_pub_key.startswith('pk_live_')):
            processor_hint = 'connect_provider_livemode'
        context.update({'processor_hint': processor_hint})
        self.update_context_urls(context, {'provider': {
            'bank': reverse('saas_update_bank', args=(app.account,))}})

        if not self.organization.is_broker:
            if 'urls' in context:
                if 'pages' in context['urls']:
                    del context['urls']['pages']
                if 'rules' in context['urls']:
                    del context['urls']['rules']
        # XXX might be overkill to always add ``site`` even though
        # it is only used in ``templates/saas/users/roles.html`` at this point.
        context.update({'site': get_current_site()})
        self.update_context_urls(context, {
            'profile_redirect': reverse('accounts_profile'),
        })
        # `ExtraMixin.get_context_data` is called before
        # `OrganizationMixin.get_context_data` had an opportunity to
        # add the organization to the `context`, so we call
        # `OrganizationMixin.organization` here. hmmm.
        attached_user = self.organization.attached_user()
        if attached_user:
            self.update_context_urls(context, {
                'user': {
                    # The following are copy/pasted
                    # from `signup.UserProfileView`
                    # to be used in the personal profile page.
                    'api_generate_keys': reverse(
                        'api_generate_keys', args=(attached_user,)),
                    'api_profile': reverse(
                        'api_user_profile', args=(attached_user,)),
                    'api_password_change': reverse(
                        'api_user_password_change', args=(attached_user,)),
                    'api_contact': reverse(
                        'api_contact', args=(attached_user.username,)), #XXX
                    'api_pubkey': reverse(
                        'api_pubkey', args=(attached_user,)),
                    'password_change': reverse(
                        'password_change', args=(attached_user,)),
                    # For sidebar menu items on personal profiles.
                    'accessibles': reverse(
                        'saas_user_product_list', args=(attached_user,)),
                    'notifications': reverse(
                        'users_notifications', args=(attached_user,)),
                    'profile': reverse('users_profile', args=(attached_user,)),
            }})
            # XXX we can't enable this code until we remove references
            # to `User = get_user_model()` in signup.compat.
            #if has_valid_password(attached_user):
            #    self.update_context_urls(context, {'user': {
            #        'api_activate': reverse(
            #            'api_user_activate', args=(attached_user,)),
            #    }})

        # XXX temporarily until djaodjin-saas v0.5 is released.
        #if not is_broker(self.organization):
        #    self.update_context_urls(context, {
        #        'rules': {'app': None},
        #        'pages': {'theme_base': None},
        #    })
        return context
