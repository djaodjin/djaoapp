# Copyright (c) 2018, DjaoDjin inc.
# see LICENSE
from __future__ import unicode_literals

import logging

from django.core.exceptions import NON_FIELD_ERRORS
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth import login as auth_login
from django.http import HttpResponseRedirect
from django.utils.translation import ugettext_lazy as _
from saas import settings as saas_settings
from saas.mixins import ProviderMixin
from saas.models import Organization, Signature, get_broker
from signup.auth import validate_redirect
from signup.mixins import UserMixin
from signup.models import Notification
from signup.views.auth import (
    ActivationView as ActivationBaseView,
    PasswordResetView as PasswordResetBaseView,
    PasswordResetConfirmView as PasswordResetConfirmBaseView,
    SigninView as SigninBaseView,
    SignoutView as SignoutBaseView,
    SignupView as SignupBaseView)
from signup.views.users import (
    UserProfileView as UserProfileBaseView,
    UserNotificationsView as UserNotificationsBaseView)
from saas.views.users import ProductListView as UserAccessiblesBaseView
from rules.mixins import AppMixin

from ..compat import reverse
from ..forms.custom_signup import (ActivationForm, PersonalRegistrationForm,
    SigninForm, TogetherRegistrationForm)
from ..locals import get_current_broker
from ..mixins import RegisterMixin


LOGGER = logging.getLogger(__name__)


# Implementation Note: inherits from ProviderMixin
# in order to include `top_accessibles`.
class UserProfileView(ProviderMixin, UserProfileBaseView):

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
            messages.error(self.request, _("This user does not support updates'\
                ' through POST request."))
            return HttpResponseRedirect(reverse('saas_organization_profile',
                args=(self.attached_organization,)))
        return super(UserProfileView, self).form_valid(form)

    def get(self, request, *args, **kwargs):
        if self.attached_organization:
            return HttpResponseRedirect(reverse('saas_organization_profile',
                args=(self.attached_organization,)))
        return super(UserProfileView, self).get(request, *args, **kwargs)


# Implementation Note: inherits from ProviderMixin
# in order to include `top_accessibles`.
class UserNotificationsView(ProviderMixin, UserNotificationsBaseView):
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

# Implementation Note: inherits from signup.UserMixin
# in order to include profile and notifications sidebar menus.
class UserAccessiblesView(UserMixin, UserAccessiblesBaseView):
    pass
