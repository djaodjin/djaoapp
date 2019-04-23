# Copyright (c) 2019, DjaoDjin inc.
# see LICENSE

from __future__ import absolute_import

from multitier.thread_locals import get_current_site
from pages.extras import AccountMixinBase
from rules.extras import AppMixinBase
#from saas.utils import is_broker

from ..compat import reverse


class ExtraMixin(AppMixinBase, AccountMixinBase):

    def get_context_data(self, **kwargs):
        context = super(ExtraMixin, self).get_context_data(**kwargs)
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
