# Copyright (c) 2018, DjaoDjin inc.
# see LICENSE

from __future__ import unicode_literals

import logging

from django.core.exceptions import NON_FIELD_ERRORS
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db import transaction
from django.contrib.auth import authenticate
from django.contrib.auth import login as auth_login
from django.http import HttpResponseRedirect
from django.template.defaultfilters import slugify
from saas import settings as saas_settings
from saas.mixins import ProviderMixin
from saas.models import Organization, Signature
from signup.auth import validate_redirect
from signup.views.users import (
    ActivationView as ActivationBaseView,
    PasswordResetView as PasswordResetBaseView,
    PasswordResetConfirmView as PasswordResetConfirmBaseView,
    SigninView as SigninBaseView,
    SignoutView as SignoutBaseView,
    SignupView as SignupBaseView,
    UserProfileView as UserProfileBaseView)
from rules.mixins import AppMixin

from ..compat import reverse
from ..locals import get_current_broker
from ..forms.custom_signup import (PersonalRegistrationForm,
    SigninForm, TogetherRegistrationForm)


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

    pass


class PasswordResetView(AuthMixin, AppMixin, PasswordResetBaseView):

    def get_success_url(self):
        # Implementation Note: Because we add a ``AuthMixin``
        # that overrides ``get_success_url``, we need to add this code
        # from the base class back here.
        messages.info(self.request, "Please follow the instructions "\
            "in the email that has just been sent to you to reset"\
            " your password.")
        return super(PasswordResetView, self).get_success_url()


class PasswordResetConfirmView(AuthMixin, AppMixin,
                               PasswordResetConfirmBaseView):

    def get_success_url(self):
        # Implementation Note: Because we add a ``AuthMixin``
        # that overrides ``get_success_url``, we need to add this code
        # from the base class back here.
        messages.info(self.request, "Your password has been reset sucessfully.")
        return super(PasswordResetConfirmView, self).get_success_url()


class SigninView(AuthMixin, AppMixin, SigninBaseView):

    form_class = SigninForm


class SignoutView(SignoutBaseView):

    pass


class SignupView(AuthMixin, AppMixin, SignupBaseView):

    user_model = get_user_model()
    role_extra_fields = (('function', 'Function', False),)
    organization_extra_fields = (
        ('parent_corporation', 'Parent corporation', False),
    )

    def form_invalid(self, form):
        #pylint:disable=protected-access
        organization_selector = 'full_name'
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
        if self.app:
            if self.app.registration == self.app.PERSONAL_REGISTRATION:
                return self.register_personal(**cleaned_data)
            elif self.app.registration == self.app.TOGETHER_REGISTRATION:
                return self.register_together(**cleaned_data)

        user = super(SignupView, self).register(**cleaned_data)
        if user:
            Signature.objects.create_signature(
                saas_settings.TERMS_OF_USE, user)
        return user

    def _register_together(self, username, password, email, user_first_name,
                           user_last_name,
                           organization_full_name, phone, street_address,
                           locality, region, postal_code, country,
                           role_extra=None, organization_slug=None,
                           organization_extra=None):
        #pylint:disable=too-many-arguments,too-many-locals
        if not organization_slug:
            organization_slug = slugify(organization_full_name)
        with transaction.atomic():
            # Create a ``User``
            user = self.user_model.objects.create_user(
                username=username, password=password, email=email,
                first_name=user_first_name, last_name=user_last_name)

            Signature.objects.create_signature(saas_settings.TERMS_OF_USE, user)

            # Create a 'personal' ``Organization`` to associate the user
            # to a billing account.
            account = Organization.objects.create(
                slug=organization_slug,
                full_name=organization_full_name,
                email=email,
                phone=phone,
                street_address=street_address,
                locality=locality,
                region=region,
                postal_code=postal_code,
                country=country,
                extra=organization_extra)
            account.add_manager(user, extra=role_extra)
            LOGGER.info("created organization '%s' with"\
                " full name: '%s', email: '%s', phone: '%s',"\
                " street_address: '%s', locality: '%s', region: '%s',"\
                " postal_code: '%s', country: '%s'.", account.slug,
                account.full_name, account.email, account.phone,
                account.street_address, account.locality, account.region,
                account.postal_code, account.country,
                extra={'event': 'create', 'request': self.request, 'user': user,
                    'type': 'Organization', 'slug': account.slug,
                    'full_name': account.full_name, 'email': account.email,
                    'street_address': account.street_address,
                    'locality': account.locality, 'region': account.region,
                    'postal_code': account.postal_code,
                    'country': account.country})

        # Sign-in the newly registered user
        user = authenticate(username=username, password=password)
        auth_login(self.request, user)
        return user

    def register_personal(self, **cleaned_data):
        """
        Registers both a User and an Organization at the same time
        with the added constraint that username and organization slug
        are identical such that it creates a transparent user billing profile.
        """
        user_first_name, user_last_name = self.first_and_last_names(
            **cleaned_data)
        return self._register_together(
            username=cleaned_data['username'],
            password=cleaned_data['new_password1'],
            user_first_name=user_first_name,
            user_last_name=user_last_name,
            email=cleaned_data['email'],
            organization_slug=cleaned_data['username'],
            organization_full_name="%s %s" % (
                cleaned_data['first_name'], cleaned_data['last_name']),
            phone=cleaned_data['phone'],
            street_address=cleaned_data['street_address'],
            locality=cleaned_data['locality'],
            region=cleaned_data['region'],
            postal_code=cleaned_data['postal_code'],
            country=cleaned_data['country'])


    def register_together(self, **cleaned_data):
        """
        Registers both a User and an Organization at the same time.
        """
        organization_selector = 'full_name'
        user_first_name, user_last_name = self.first_and_last_names(
            **cleaned_data)
        role_extra = {}
        for field in self.role_extra_fields:
            key = field[0]
            if key in cleaned_data:
                role_extra.update({key: cleaned_data[key]})
        organization_extra = {}
        for field in self.organization_extra_fields:
            key = field[0]
            if key in cleaned_data:
                organization_extra.update({key: cleaned_data[key]})
        return self._register_together(
            username=cleaned_data['username'],
            password=cleaned_data['new_password1'],
            user_first_name=user_first_name,
            user_last_name=user_last_name,
            email=cleaned_data['email'],
            organization_full_name=cleaned_data[organization_selector],
            phone=cleaned_data.get('phone', ""),
            street_address=cleaned_data.get('street_address', ""),
            locality=cleaned_data.get('locality', ""),
            region=cleaned_data.get('region', ""),
            postal_code=cleaned_data.get('postal_code', ""),
            country=cleaned_data.get('country', ""),
            role_extra=role_extra,
            organization_extra=organization_extra)


class UserProfileView(AuthMixin, ProviderMixin, UserProfileBaseView):

    # These fields declared in ``UserProfileBaseView`` will be overriden
    # by the ones declared in ``OrganizationMixin``.
    model = get_user_model()
    slug_field = 'username'
    slug_url_kwarg = 'user'

    def get(self, request, *args, **kwargs):
        # XXX attached_manager
        queryset = Organization.objects.filter(
            slug=kwargs.get(self.slug_url_kwarg))
        if queryset.exists():
            return HttpResponseRedirect(
                reverse('saas_organization_profile', args=(queryset.get(),)))
        return super(UserProfileView, self).get(request, *args, **kwargs)
