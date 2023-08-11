# Copyright (c) 2023, DjaoDjin inc.
# see LICENSE
from __future__ import unicode_literals

import logging

from django.contrib import messages
from django.http import HttpResponseRedirect
from saas.views.users import ProductListView as UserAccessiblesBaseView
from signup.views.users import (
    PasswordChangeView as UserPasswordUpdateBaseView,
    UserNotificationsView as UserNotificationsBaseView,
    UserProfileView as UserProfileBaseView,
    UserPublicKeyUpdateView as UserPublicKeyUpdateBaseView)

from ..compat import gettext_lazy as _, reverse
from ..mixins import NotificationsMixin

LOGGER = logging.getLogger(__name__)


class UserProfileView(UserProfileBaseView):

    template_name = 'saas/profile/index.html'

    def form_valid(self, form):
        # There is something fundamentally wrong if we have an `attached_user`
        # and we get here. The `GET` request should have redirected us
        # to the organization profile page.
        attached_organization = self.get_organization()
        if attached_organization:
            messages.error(self.request, _("This user does not support updates"\
                " through POST request."))
            return HttpResponseRedirect(reverse('saas_organization_profile',
                args=(attached_organization,)))
        return super(UserProfileView, self).form_valid(form)

    def get(self, request, *args, **kwargs):
        attached_organization = self.get_organization()
        if attached_organization:
            return HttpResponseRedirect(reverse('saas_organization_profile',
                args=(attached_organization,)))
        return super(UserProfileView, self).get(request, *args, **kwargs)


class UserNotificationsView(NotificationsMixin, UserNotificationsBaseView):
    """
    A view where a user can configure their notification settings
    """


class UserAccessiblesView(UserAccessiblesBaseView):
    pass


class UserPasswordUpdateView(UserPasswordUpdateBaseView):
    pass


class UserPublicKeyUpdateView(UserPublicKeyUpdateBaseView):
    pass
