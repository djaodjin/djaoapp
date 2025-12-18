# Copyright (c) 2023, DjaoDjin inc.
# see LICENSE

from __future__ import absolute_import

from extended_templates.extras import AccountMixinBase
from rules.extras import AppMixinBase
from rules.utils import get_current_app
from signup.helpers import has_invalid_password, update_context_urls

from ..compat import reverse


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

        processor_backend = app.account.processor_backend
        broker_pub_key = processor_backend.pub_key
        requires_provider_keys = (
            processor_backend.requires_provider_keys() and
            not self._is_platform(app.account))
        provider_pub_key = app.account.processor_pub_key

        processor_hint = None
        if not processor_backend.is_configured():
            processor_hint = 'configure_broker'
        elif requires_provider_keys and not provider_pub_key:
            processor_hint = 'connect_provider'
            update_context_urls(context, {'provider': {
                'bank': reverse('saas_update_bank', args=(app.account,))}})
        elif not broker_pub_key.startswith('pk_live_'):
            processor_hint = 'configure_broker_livemode'
        elif (requires_provider_keys and
              not provider_pub_key.startswith('pk_live_')):
            processor_hint = 'connect_provider_livemode'
            update_context_urls(context, {'provider': {
                'bank': reverse('saas_update_bank', args=(app.account,))}})
        context.update({'processor_hint': processor_hint})

        if not self.organization.is_broker:
            if 'urls' in context:
                if 'theme_update' in context['urls']:
                    del context['urls']['theme_update']
                if 'rules' in context['urls']:
                    del context['urls']['rules']
        update_context_urls(context, {
            'api_places_suggestions': reverse('api_places_suggestions'),
            'profile_redirect': reverse('accounts_profile'),
            'trust_compliance': reverse('trust_compliance', args=(
                self.organization,))
        })

        # `ExtraMixin.get_context_data` is called before
        # `OrganizationMixin.get_context_data` had an opportunity to
        # add the organization to the `context`, so we call
        # `OrganizationMixin.organization` here. hmmm.
        user = self.organization.attached_user()
        if user:
            # The following are copy/pasted
            # from `signup.UserProfileView`
            # to be used in the personal profile page.
            setattr(user, 'full_name', user.get_full_name())
            primary_contact = user.contacts.filter(
                email__iexact=user.email).order_by('created_at').first()
            if primary_contact:
                context.update({
                    'email_verified_at': primary_contact.email_verified_at,
                    'phone_verified_at': primary_contact.phone_verified_at
                })
            if primary_contact and primary_contact.picture:
                setattr(user, 'picture', primary_contact.picture)
            else:
                picture_candidate = user.contacts.filter(
                    picture__isnull=False).order_by('created_at').first()
                if picture_candidate:
                    setattr(user, 'picture', picture_candidate.picture)

            update_context_urls(context, {
                # The following are copy/pasted
                # from `signup.UserProfileView`
                # to be used in the personal profile page.
                'api_recover': reverse('api_recover'),
                'user': {
                    'api_generate_keys': reverse(
                        'api_generate_keys', args=(user,)),
                    'api_profile': reverse(
                        'api_user_profile', args=(user,)),
                    'api_password_change': reverse(
                        'api_user_password_change', args=(user,)),
                    'api_otp_change': reverse(
                        'api_user_otp_change', args=(user,)),
                    'api_profile_picture': reverse(
                        'saas_api_organization_picture', args=(
                        self.organization,)),
                    'api_contact': reverse(
                        'api_contact', args=(user.username,)), #XXX
                    'api_pubkey': reverse(
                        'api_pubkey', args=(user,)),
                    'password_change': reverse(
                        'password_change', args=(user,)),
                    'keys_update': reverse(
                        'pubkey_update', args=(user,)),

                    # For sidebar menu items on personal profiles.
                    'accessibles': reverse(
                        'saas_user_product_list', args=(user,)),
                    'notifications': reverse(
                        'users_notifications', args=(user,)),
                    'profile': reverse('users_profile', args=(user,)),
            }})
            # The following are copy/pasted
            # from `signup.UserProfileView`
            # to be used in the personal profile page.
            if has_invalid_password(user):
                update_context_urls(context, {'user': {
                    'api_activate': reverse(
                        'api_user_activate', args=(user,)),
                }})

            from signup.models import OTPGenerator
            context.update({
                'otp_enabled': OTPGenerator.objects.filter(
                    user=user).exists()})

        return context


    def update_attached_user(self, user, validated_data):
        from signup.models import get_user_contact
        contact = get_user_contact(user)
        if contact:
            contact.slug = validated_data.get('slug', contact.slug)
            full_name = validated_data.get('full_name')
            if full_name:
                contact.full_name = full_name
            contact.email = validated_data.get('email', contact.email)
            contact.phone = validated_data.get('phone', contact.phone)
            contact.lang = validated_data.get('lang', contact.lang)
            contact.save()
        return user
