# Copyright (c) 2021, DjaoDjin inc.
# see LICENSE
from __future__ import unicode_literals

import logging

from django.contrib import messages
from django.http import HttpResponseRedirect
from django.utils.translation import ugettext_lazy as _
from multitier.thread_locals import get_current_site
from saas.models import Organization
from saas.utils import update_context_urls
from signup.views.users import (
    UserProfileView as UserProfileBaseView,
    UserNotificationsView as UserNotificationsBaseView,
    PasswordChangeView as UserPasswordUpdateBaseView)
from saas.views.users import ProductListView as UserAccessiblesBaseView

from ..compat import reverse
from ..mixins import NotificationsMixin

LOGGER = logging.getLogger(__name__)

class UserMixin(object):
    """
    Sidebar menus related to a user.
    """
    user_url_kwarg = 'user'

    @property
    def attached_organization(self):
        if not hasattr(self, '_attached_organization'):
            try:
                # We use `get` instead of `attached` here because we want
                # to redirect to the profle page regardless if an organization
                # with the lookup slug is found.
                self._attached_organization = Organization.objects.get(
                    slug=self.kwargs.get(self.user_url_kwarg))
            except Organization.DoesNotExist:
                self._attached_organization = None
        return self._attached_organization


    def get_context_data(self, **kwargs):
        context = super(UserMixin, self).get_context_data(**kwargs)
        update_context_urls(context, {
            'profile_base': reverse('saas_profile'),
            'user': {
                'accessibles': reverse(
                    'saas_user_product_list', args=(self.user,)),
                'notifications': reverse(
                    'users_notifications', args=(self.user,)),
                'profile': reverse('users_profile', args=(self.user,)),
            }})
        organization = self.attached_organization
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


class UserProfileView(UserMixin, UserProfileBaseView):

    template_name = 'saas/profile/index.html'

    def form_valid(self, form):
        # There is something fundamentally wrong if we have an `attached_user`
        # and we get here. The `GET` request should have redirected us
        # to the organization profile page.
        if self.attached_organization:
            messages.error(self.request, _("This user does not support updates"\
                " through POST request."))
            return HttpResponseRedirect(reverse('saas_organization_profile',
                args=(self.attached_organization,)))
        return super(UserProfileView, self).form_valid(form)

    def get(self, request, *args, **kwargs):
        if self.attached_organization:
            return HttpResponseRedirect(reverse('saas_organization_profile',
                args=(self.attached_organization,)))
        return super(UserProfileView, self).get(request, *args, **kwargs)


class UserNotificationsView(NotificationsMixin, UserMixin,
                            UserNotificationsBaseView):
    """
    A view where a user can configure their notification settings
    """


class UserAccessiblesView(UserMixin, UserAccessiblesBaseView):

    def get_context_data(self, **kwargs):
        context = super(UserAccessiblesView, self).get_context_data(**kwargs)
        context.update({
            'site': get_current_site()
        })
        return context


class UserPasswordUpdateView(UserMixin, UserPasswordUpdateBaseView):
    pass


class UserPublicKeyUpdateView(UserMixin, UserPasswordUpdateBaseView):
    pass
