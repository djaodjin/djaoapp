# Copyright (c) 2023, DjaoDjin inc.
# see LICENSE

from __future__ import absolute_import

from saas.extras import OrganizationMixinBase

from ..compat import reverse


class ExtraMixin(object):

    def get_organization(self):
        from saas.utils import get_organization_model # to avoid import loops
        from saas.models import get_broker
        if hasattr(self, 'user'):
            # ContactListView
            return get_organization_model().objects.attached(self.user)
        return get_broker()

    def get_context_data(self, **kwargs):
        from saas.utils import update_context_urls # to avoid import loops
        context = super(ExtraMixin, self).get_context_data(**kwargs)

        if not hasattr(self, 'user'):
            # ContactListView
            return context

        self.update_context_urls(context, {
            'user': {
                # The following are copy/pasted
                # from `signup.UserProfileView`
                # to be used in the personal profile page.
                'api_generate_keys': reverse(
                    'api_generate_keys', args=(self.user,)),
                'api_profile': reverse(
                    'api_user_profile', args=(self.user,)),
                'api_password_change': reverse(
                    'api_user_password_change', args=(self.user,)),
                'api_contact': reverse(
                    'api_contact', args=(self.user.username,)), #XXX
                'api_pubkey': reverse(
                    'api_pubkey', args=(self.user,)),
                'password_change': reverse(
                    'password_change', args=(self.user,)),
                'keys_update': reverse(
                    'pubkey_update', args=(self.user,)),
                # For sidebar menu items on personal profiles.
                'accessibles': reverse(
                    'saas_user_product_list', args=(self.user,)),
                'notifications': reverse(
                    'users_notifications', args=(self.user,)),
                'profile': reverse('users_profile', args=(self.user,)),
        }})

        organization = self.get_organization()
        if organization and organization.is_broker:
            update_context_urls(context, {
                'theme_update': reverse('extended_templates_theme_update'),
                'rules': {'app': reverse('rules_update')}
            })

        if organization and not organization.is_broker:
            # A broker does not have subscriptions.

            # Duplicate code from `saas.extras.OrganizationMixinBase` since
            # it does not get inherited in the context of a `UserMixin`.
            update_context_urls(context, {
                'organization': {
                    'billing': reverse(
                        'saas_billing_info', args=(organization,)),
                    'subscriptions': reverse(
                        'saas_subscription_list', args=(organization,)),
                }})

        return context
