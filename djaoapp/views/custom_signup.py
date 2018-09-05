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
from rules.mixins import AppMixin

from ..compat import reverse
from ..forms.custom_signup import (ActivationForm, PersonalRegistrationForm,
    SigninForm, TogetherRegistrationForm)
from ..locals import get_current_broker
from ..mixins import RegisterMixin


LOGGER = logging.getLogger(__name__)


class AuthMixin(object):

    def form_invalid(self, form):
        # We move all non_field_errors into messages to make it easier
        # to write templates (i.e. a single for loop on messages).
        # pylint: disable=protected-access
        for error in form.non_field_errors():
            messages.error(self.request, error)
        if NON_FIELD_ERRORS in form._errors:
            del form._errors[NON_FIELD_ERRORS]
        return super(AuthMixin, self).form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super(AuthMixin, self).get_context_data(**kwargs)
        # URLs for user
        if not self.request.user.is_authenticated():
            user_urls = {
               'login_github': reverse('social:begin', args=('github',)),
               'login_google': reverse('social:begin', args=('google-oauth2',)),
               'login_twitter': reverse('social:begin', args=('twitter',)),
            }
            if 'urls' in context:
                if 'user' in context['urls']:
                    context['urls']['user'].update(user_urls)
                else:
                    context['urls'].update({'user': user_urls})
            else:
                context.update({'urls': {'user': user_urls}})
        urls_default = {
            'pricing': reverse('saas_cart_plan_list'),
        }
        if 'urls' in context:
            context['urls'].update(urls_default)
        else:
            context.update({'urls': urls_default})
        return context

    def get_success_url(self):
        next_url = validate_redirect(self.request)
        if not next_url:
            next_url = reverse('product_default_start')
        return next_url


class ActivationView(AuthMixin, AppMixin, ActivationBaseView):

    form_class = ActivationForm

    def get_initial(self):
        kwargs = super(ActivationView, self).get_initial()
        kwargs.update({'legal_agreement_url': reverse('legal_agreement',
            args=('terms-of-use',))})
        return kwargs


class PasswordResetView(AuthMixin, AppMixin, PasswordResetBaseView):

    def get_success_url(self):
        # Implementation Note: Because we add a ``AuthMixin``
        # that overrides ``get_success_url``, we need to add this code
        # from the base class back here.
        return super(PasswordResetView, self).get_success_url()


class PasswordResetConfirmView(AuthMixin, AppMixin,
                               PasswordResetConfirmBaseView):

    def get_success_url(self):
        # Implementation Note: Because we add a ``AuthMixin``
        # that overrides ``get_success_url``, we need to add this code
        # from the base class back here.
        messages.info(self.request,
            _("Your password has been reset sucessfully."))
        return super(PasswordResetConfirmView, self).get_success_url()


class SigninView(AuthMixin, AppMixin, SigninBaseView):

    form_class = SigninForm


class SignoutView(SignoutBaseView):

    pass


class SignupView(AuthMixin, AppMixin, RegisterMixin, SignupBaseView):

    user_model = get_user_model()
    role_extra_fields = (('role_function', 'Function', False),)
    organization_extra_fields = (
        ('organization_parent_corporation', 'Parent corporation', False),
    )

    def form_invalid(self, form):
        #pylint:disable=protected-access
        organization_selector = 'organization_name'
        if len(form._errors) == 1 and organization_selector in form._errors:
            for err in form._errors[organization_selector]:
                if err.startswith(
                        "Your organization might already be registered."):
                    user_model = get_user_model()
                    user = user_model(email=form.cleaned_data['email'])
                    # Use ``form.data`` because Django will have removed
                    # the `organization_selector` key from ``form.cleaned_data``
                    # at this point.
                    organization_name = form.data.get(
                        organization_selector, None)
                    self.already_present_candidate = \
                        Organization.objects.find_candidates(
                            organization_name, user=user).first()
        return super(SignupView, self).form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super(SignupView, self).get_context_data(**kwargs)
        if hasattr(self, 'already_present_candidate'):
            context.update({
                'already_present_candidate': self.already_present_candidate})
        return context

    def get_initial(self):
        kwargs = super(SignupView, self).get_initial()
        if self.app:
            if self.app.registration in [self.app.PERSONAL_REGISTRATION,
                                         self.app.TOGETHER_REGISTRATION]:
                broker = get_current_broker()
                kwargs.update({'country': broker.country,
                               'region': broker.region})
                if self.app.registration == self.app.TOGETHER_REGISTRATION:
                    kwargs.update({'extra_fields': (self.role_extra_fields
                        + self.organization_extra_fields)})
        return kwargs

    def get_form_class(self):
        if self.app:
            if self.app.registration == self.app.PERSONAL_REGISTRATION:
                return PersonalRegistrationForm
            elif self.app.registration == self.app.TOGETHER_REGISTRATION:
                return TogetherRegistrationForm
        return super(SignupView, self).get_form_class()

    def register(self, **cleaned_data):
        #pylint:disable=too-many-boolean-expressions
        registration = self.app.USER_REGISTRATION
        full_name = cleaned_data.get('full_name', None)
        organization_name = cleaned_data.get('organization_name', None)
        if organization_name:
            # We have a registration of a user and organization together.
            registration = self.app.TOGETHER_REGISTRATION
            if full_name and full_name == organization_name:
                # No we have a personal registration after all
                registration = self.app.PERSONAL_REGISTRATION
        elif (cleaned_data.get('street_address', None) or
            cleaned_data.get('locality', None) or
            cleaned_data.get('region', None) or
            cleaned_data.get('postal_code', None) or
            cleaned_data.get('country', None) or
            cleaned_data.get('phone', None)):
            # We have enough information for a billing profile
            registration = self.app.PERSONAL_REGISTRATION

        if registration == self.app.PERSONAL_REGISTRATION:
            user = self.register_personal(**cleaned_data)
        elif registration == self.app.TOGETHER_REGISTRATION:
            user = self.register_together(**cleaned_data)
        else:
            user = self.register_user(**cleaned_data)
            if user:
                Signature.objects.create_signature(
                    saas_settings.TERMS_OF_USE, user)

        auth_login(self.request, user)
        return user


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
