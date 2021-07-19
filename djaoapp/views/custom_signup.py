# Copyright (c) 2021, DjaoDjin inc.
# see LICENSE
from __future__ import unicode_literals

import logging

from deployutils.apps.django.compat import is_authenticated
from django.core.exceptions import NON_FIELD_ERRORS
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth import login as auth_login
from django.utils.translation import ugettext_lazy as _
from saas import settings as saas_settings
from saas.models import Agreement, Organization, Signature
from signup.auth import validate_redirect
from signup.views.auth import (
    ActivationView as ActivationBaseView,
    PasswordResetView as PasswordResetBaseView,
    PasswordResetConfirmView as PasswordResetConfirmBaseView,
    SigninView as SigninBaseView,
    SignoutView as SignoutBaseView,
    SignupView as SignupBaseView)
from rules.mixins import AppMixin

from ..compat import reverse, six
from ..forms.custom_signup import ActivationForm, SigninForm, SignupForm
from ..thread_locals import get_current_broker
from ..mixins import RegisterMixin


LOGGER = logging.getLogger(__name__)


class AuthMixin(object):

    def get_context_data(self, **kwargs):
        context = super(AuthMixin, self).get_context_data(**kwargs)
        # URLs for user
        if not is_authenticated(self.request):
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

    def activate_user(self, **cleaned_data):
        user = super(ActivationView, self).activate_user(**cleaned_data)
        if user:
            Signature.objects.create_signature(saas_settings.TERMS_OF_USE, user)
        return user

    def get_initial(self):
        kwargs = super(ActivationView, self).get_initial()
        kwargs.update({'legal_agreement_url': reverse('legal_agreement',
            args=('terms-of-use',))})
        return kwargs



class PasswordResetView(AuthMixin, AppMixin, PasswordResetBaseView):

    def get_success_url(self):
        #pylint:disable=useless-super-delegation
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

    form_class = SignupForm
    user_model = get_user_model()

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

        found_non_field_errors = False
        for field_name in six.iterkeys(form._errors):
            if field_name == NON_FIELD_ERRORS:
                found_non_field_errors = True
                break
        if not found_non_field_errors:
            form.add_error(None, _("There were invalid fields while"\
                " registering. See below."))
        return super(SignupView, self).form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super(SignupView, self).get_context_data(**kwargs)
        if hasattr(self, 'already_present_candidate'):
            context.update({
                'already_present_candidate': self.already_present_candidate})
        return context

    def get_initial(self):
        kwargs = super(SignupView, self).get_initial()
        broker = get_current_broker()
        kwargs.update({
            'country': broker.country,
            'region': broker.region
        })
        kwargs.update({
            'extra_fields': [(agreement.slug, agreement.title, False)
                for agreement in Agreement.objects.all()]
        })
        return kwargs

    def get_form_kwargs(self):
        kwargs = super(SignupView, self).get_form_kwargs()
        if self.app and self.app.registration == self.app.PERSONAL_REGISTRATION:
            kwargs.update({'force_required': True})
        return kwargs

    def get_template_names(self):
        candidates = []
        register_path = self.kwargs.get('path', None)
        if not register_path and self.app:
            if self.app.registration == self.app.PERSONAL_REGISTRATION:
                register_path = 'personal'
            elif self.app.registration == self.app.TOGETHER_REGISTRATION:
                register_path = 'organization'
        if register_path:
            candidates = ['accounts/register/%s.html' % register_path]
        return candidates + list(super(SignupView, self).get_template_names())

    def register(self, **cleaned_data):
        #pylint:disable=too-many-boolean-expressions
        registration = self.app.USER_REGISTRATION
        full_name = cleaned_data.get('full_name', None)
        if 'organization_name' in cleaned_data:
            # We have a registration of a user and organization together.
            registration = self.app.TOGETHER_REGISTRATION
            organization_name = cleaned_data.get('organization_name', None)
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
            user = self.register_user(
                next_url=self.get_success_url(), **cleaned_data)
        if user:
            auth_login(self.request, user)
        return user
