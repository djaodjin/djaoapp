# Copyright (c) 2018, DjaoDjin inc.
# see LICENSE
from __future__ import unicode_literals

import logging

from django.contrib import messages
from django.http import HttpResponseRedirect
from django.utils.translation import ugettext_lazy as _
from multitier.thread_locals import get_current_site
from saas import settings as saas_settings
from saas.mixins import ProviderMixin
from saas.models import Organization, get_broker
from signup.models import Notification
from signup.views.users import (
    UserProfileView as UserProfileBaseView,
    UserNotificationsView as UserNotificationsBaseView,
    PasswordChangeView as UserPasswordUpdateBaseView,
    UserPublicKeyUpdateView as UserPublicKeyUpdateBaseView)
from saas.views.users import ProductListView as UserAccessiblesBaseView
from saas.utils import update_context_urls

from ..compat import reverse


LOGGER = logging.getLogger(__name__)


class UserMixin(object):

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
        return context


class UserProfileView(UserMixin, UserProfileBaseView):

    template_name = 'saas/profile/index.html'

    @property
    def attached_organization(self):
        if not hasattr(self, '_attached_organization'):
            self._attached_organization = Organization.objects.attached(
                self.kwargs.get(self.slug_url_kwarg))
        return self._attached_organization

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


class UserNotificationsView(UserMixin, UserNotificationsBaseView):
    """
    A view where a user can configure their notification settings
    """

    def get_notifications(self):
        if get_broker().with_role(saas_settings.MANAGER).filter(
                pk=self.user.pk).exists():
            return super(UserNotificationsView, self).get_notifications()
        return Notification.objects.filter(slug__in=(
            'charge_updated', 'card_updated', 'order_executed',
            'organization_updated', 'expires_soon'))


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
