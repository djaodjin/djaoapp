# Copyright (c) 2023, DjaoDjin inc.
# see LICENSE
from __future__ import unicode_literals

import logging

from django.contrib import messages
from django.http import HttpResponseRedirect
from multitier.thread_locals import get_current_site
from saas.models import Organization
from saas.utils import update_context_urls
from saas.views.users import ProductListView as UserAccessiblesBaseView
from signup.views.users import (
    PasswordChangeView as UserPasswordUpdateBaseView,
    UserNotificationsView as UserNotificationsBaseView,
    UserProfileView as UserProfileBaseView,
    UserPublicKeyUpdateView as UserPublicKeyUpdateBaseView)

from ..compat import gettext_lazy as _, reverse
from ..mixins import NotificationsMixin
from ..extras.signup import ExtraMixin

LOGGER = logging.getLogger(__name__)


class UserProfileView(ExtraMixin, UserProfileBaseView):

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


class UserNotificationsView(NotificationsMixin, ExtraMixin,
                            UserNotificationsBaseView):
    """
    A view where a user can configure their notification settings
    """


class UserAccessiblesView(ExtraMixin, UserAccessiblesBaseView):

    def get_context_data(self, **kwargs):
        context = super(UserAccessiblesView, self).get_context_data(**kwargs)
        # We have to add 'site' to the context here because the connected
        # profiles page inherits from ExtraMixin, not OrganizationMixin.
        context.update({
            'site': get_current_site()
        })
        return context


class UserPasswordUpdateView(ExtraMixin, UserPasswordUpdateBaseView):
    pass


class UserPublicKeyUpdateView(ExtraMixin, UserPublicKeyUpdateBaseView):
    pass
