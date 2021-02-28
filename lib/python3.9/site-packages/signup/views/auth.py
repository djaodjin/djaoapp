# Copyright (c) 2021, Djaodjin Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
# OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
# OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
# ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""Extra Views that might prove useful to register users."""
from __future__ import unicode_literals

import logging

from django.contrib import messages
from django.contrib.auth import (login as auth_login, logout as auth_logout,
    REDIRECT_FIELD_NAME, authenticate, get_user_model)
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.utils.encoding import force_bytes
from django.utils.http import (urlencode, urlsafe_base64_decode,
    urlsafe_base64_encode)
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.cache import add_never_cache_headers
from django.views.generic.base import TemplateResponseMixin, View
from django.views.generic.edit import FormMixin, ProcessFormView, UpdateView
from rest_framework import serializers
from rest_framework.settings import api_settings

from .. import settings, signals
from ..auth import validate_redirect
from ..compat import reverse, is_authenticated, six
from ..decorators import check_has_credentials
from ..forms import (ActivationForm, MFACodeForm, FrictionlessSignupForm,
    PasswordResetForm, PasswordResetConfirmForm,
    UserActivateForm, AuthenticationForm)
from ..helpers import full_name_natural_split
from ..mixins import ActivateMixin, UrlsMixin
from ..models import Contact
from ..utils import (fill_form_errors, get_disabled_authentication,
    get_disabled_registration, get_login_throttle, get_password_reset_throttle,
    has_invalid_password)
from ..validators import as_email_or_phone


LOGGER = logging.getLogger(__name__)


def _login(request, user):
    """
    Attaches a session cookie to the request and
    generates an login event in the audit logs.
    """
    auth_login(request, user)
    LOGGER.info("%s signed in.", user,
        extra={'event': 'login', 'request': request})


class RedirectFormMixin(FormMixin):
    success_url = settings.LOGIN_REDIRECT_URL

    def get_success_url(self):
        next_url = validate_redirect(self.request)
        if not next_url:
            next_url = super(RedirectFormMixin, self).get_success_url()
        return next_url

    def get_context_data(self, **kwargs):
        context = super(RedirectFormMixin, self).get_context_data(**kwargs)
        next_url = validate_redirect(self.request)
        if next_url:
            context.update({REDIRECT_FIELD_NAME: next_url})
        return context


class AuthTemplateResponseMixin(UrlsMixin, TemplateResponseMixin):
    """
    Returns a *disabled* page regardless when get_disabled_authentication
    is True.
    """

    def get_context_data(self, **kwargs):
        context = super(AuthTemplateResponseMixin, self).get_context_data(
            **kwargs)
        # URLs for user
        disabled_registration = get_disabled_registration(self.request)
        self.update_context_urls(context, {
            'api': {
                'login': reverse('api_login'),
                'recover': reverse('api_recover'),
                'register': (reverse('api_register')
                    if not disabled_registration else None),
            },
            'user': {
                'login': reverse('login'),
                'password_reset': reverse('password_reset'),
                'register': (reverse('registration_register')
                    if not disabled_registration else None),
        }})
        return context

    def dispatch(self, request, *args, **kwargs):
        if request.method.lower() in self.http_method_names:
            if get_disabled_authentication(request):
                context = {'disabled_authentication': True}
                response_kwargs = {}
                response_kwargs.setdefault('content_type', self.content_type)
                return TemplateResponse(
                    request=request, template='accounts/disabled.html',
                    context=context, **response_kwargs)
        return super(AuthTemplateResponseMixin, self).dispatch(
            request, *args, **kwargs)


class RedirectFormView(RedirectFormMixin, ProcessFormView):
    """
    Redirects on form valid.
    """


class PasswordResetBaseView(RedirectFormMixin, ProcessFormView):
    """
    Enter email address or phone number to reset password.
    """
    model = get_user_model()
    form_class = PasswordResetForm
    token_generator = default_token_generator

    def check_user_throttles(self, request, user):
        throttle = get_password_reset_throttle()
        if throttle:
            throttle(request, self, user)

    def form_valid(self, form):
        username = form.cleaned_data.get('email', None)
        email, phone = as_email_or_phone(username)
        try:
            user = self.model.objects.find_user(username)

            # Rate-limit based on the user.
            self.check_user_throttles(self.request, user)

            next_url = validate_redirect(self.request)
            if check_has_credentials(self.request, user, next_url=next_url):
                # Make sure that a reset password email is sent to a user
                # that actually has an activated account.
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                if not isinstance(uid, six.string_types):
                    # See Django2.2 release notes
                    uid = uid.decode()
                token = self.token_generator.make_token(user)
                back_url = self.request.build_absolute_uri(
                    reverse('password_reset_confirm', args=(uid, token)))
                if next_url:
                    back_url += '?%s=%s' % (REDIRECT_FIELD_NAME, next_url)
                signals.user_reset_password.send(
                    sender=__name__, user=user, request=self.request,
                    back_url=back_url, expiration_days=settings.KEY_EXPIRATION)
                if phone:
                    messages.info(self.request,
                    _("Please follow the instructions in the phone message"\
                    " that has just been sent to you to reset"\
                    " your password."))
                elif email:
                    messages.info(self.request,
                    _("Please follow the instructions"\
                    " in the email that has just been sent to you to reset"\
                    " your password."))
            else:
                if phone:
                    messages.info(self.request,
                        _("You should now secure and activate"\
                          " your account following the instructions"\
                          " we just phoned you. Thank you."))
                elif email:
                    messages.info(self.request,
                        _("You should now secure and activate"\
                          " your account following the instructions"\
                          " we just emailed you. Thank you."))
            return super(PasswordResetBaseView, self).form_valid(form)
        except self.model.DoesNotExist:
            # We don't want to give a clue about registered users, yet
            # it already possible to do a straight register to get the same.
            if phone:
                messages.error(self.request, _("We cannot find an account"\
                    " for this phone number. Please verify the spelling."))
            else:
                messages.error(self.request, _("We cannot find an account"\
                    " for this e-mail address. Please verify the spelling."))
        return super(PasswordResetBaseView, self).form_invalid(form)


class PasswordResetConfirmBaseView(RedirectFormMixin, ProcessFormView):
    """
    Clicked on the link sent in the reset e-mail.
    """
    model = get_user_model()
    form_class = PasswordResetConfirmForm
    token_generator = default_token_generator
    post_reset_login = True

    def form_valid(self, form):
        if self.post_reset_login:
            user = self.object
            user_with_backend = authenticate(self.request,
                username=user.username,
                password=form.cleaned_data['new_password'])
            _login(self.request, user_with_backend)
        return super(PasswordResetConfirmBaseView, self).form_valid(form)

    def get_context_data(self, **kwargs):
        context = super(PasswordResetConfirmBaseView,
                        self).get_context_data(**kwargs)
        user = self.object
        if user is not None and self.token_generator.check_token(
                                    user, self.kwargs.get('token')):
            context.update({'validlink': True})
        return context

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests, instantiating a form instance with the passed
        POST variables and then checked for validity.
        """
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        user = self.object
        if user is not None and self.token_generator.check_token(
                                    user, self.kwargs.get('token')):
            if form.is_valid():
                form.save()
                LOGGER.info("%s reset her/his password.", user,
                    extra={'event': 'resetpassword', 'request': request})
                return self.form_valid(form)
        return self.form_invalid(form)

    def get_success_url(self):
        messages.info(self.request,
            _("Your password has been reset sucessfully."))
        return super(PasswordResetConfirmBaseView, self).get_success_url()

    def get_form_kwargs(self):
        """
        Returns the keyword arguments for instantiating the form.
        """
        kwargs = super(PasswordResetConfirmBaseView, self).get_form_kwargs()
        try:
            uid = urlsafe_base64_decode(self.kwargs.get('uidb64'))
            if not isinstance(uid, six.string_types):
                # See Django2.2 release notes
                uid = uid.decode()
            self.object = self.model.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, self.model.DoesNotExist):
            self.object = None
        kwargs.update({'instance': self.object})
        return kwargs


class SignupBaseView(RedirectFormMixin, ProcessFormView):
    """
    A frictionless registration backend With a full name and email
    address, the user is immediately signed up and logged in.
    """
    model = get_user_model()
    form_class = FrictionlessSignupForm
    fail_url = ('registration_register', (), {})
    backend_path = 'signup.backends.auth.UsernameOrEmailPhoneModelBackend'

    @staticmethod
    def first_and_last_names(**cleaned_data):
        first_name = cleaned_data.get('first_name', None)
        last_name = cleaned_data.get('last_name', None)
        if not first_name:
            # If the form does not contain a first_name/last_name pair,
            # we assume a full_name was passed instead.
            full_name = cleaned_data.get(
                'user_full_name', cleaned_data.get('full_name', None))
            first_name, _, last_name = full_name_natural_split(full_name)
        return first_name, last_name

    def dispatch(self, request, *args, **kwargs):
        if request.method.lower() in self.http_method_names:
            if get_disabled_registration(request):
                context = {'disabled_registration': True}
                response_kwargs = {}
                response_kwargs.setdefault('content_type', self.content_type)
                return TemplateResponse(request=request,
                    template='accounts/disabled.html',
                    context=context, **response_kwargs)
        return super(SignupBaseView, self).dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        try:
            cleaned_data = {}
            for field_name in six.iterkeys(form.data):
                cleaned_data.update({
                    field_name: form.cleaned_data.get(
                        field_name, form.data[field_name])})
            new_user = self.register(**cleaned_data)
        except serializers.ValidationError as err:
            fill_form_errors(form, err)
            return self.form_invalid(form)
        if new_user:
            success_url = self.get_success_url()
        else:
            success_url = self.request.META['PATH_INFO']
        return HttpResponseRedirect(success_url)

    def get_initial(self):
        initial = super(SignupBaseView, self).get_initial()
        for key, value in six.iteritems(self.request.GET):
            initial.update({key: value})
        return initial

    def register_user(self, **cleaned_data):
        email = cleaned_data.get('email', None)
        if email:
            try:
                user = self.model.objects.find_user(email)
                if check_has_credentials(self.request, user,
                                     next_url=self.get_success_url()):
                    raise serializers.ValidationError(
                        {'email':
                         _("A user with that e-mail address already exists."),
                         api_settings.NON_FIELD_ERRORS_KEY:
                         mark_safe(_(
                             "This email address has already been registered!"\
    " Please <a href=\"%s\">login</a> with your credentials. Thank you.")
                            % reverse('login'))})
                raise serializers.ValidationError(
                    {'email':
                     _("A user with that e-mail address already exists."),
                     api_settings.NON_FIELD_ERRORS_KEY:
                     mark_safe(_(
                         "This email address has already been registered!"\
    " You should now secure and activate your account following "\
    " the instructions we just emailed you. Thank you."))})
            except self.model.DoesNotExist:
                # OK to continue. We will have raised an exception in all other
                # cases.
                pass

        phone = cleaned_data.get('phone', None)
        if phone:
            try:
                user = self.model.objects.find_user(phone)
                if check_has_credentials(self.request, user,
                                     next_url=self.get_success_url()):
                    raise serializers.ValidationError(
                        {'phone':
                         _("A user with that phone number already exists."),
                         api_settings.NON_FIELD_ERRORS_KEY:
                         mark_safe(_(
                             "This phone number has already been registered!"\
    " Please <a href=\"%s\">login</a> with your credentials. Thank you.")
                            % reverse('login'))})
                raise serializers.ValidationError(
                    {'phone':
                     _("A user with that phone number already exists."),
                     api_settings.NON_FIELD_ERRORS_KEY:
                     mark_safe(_(
                         "This phone number has already been registered!"\
    " You should now secure and activate your account following "\
    " the instructions we just messaged you. Thank you."))})
            except self.model.DoesNotExist:
                # OK to continue. We will have raised an exception in all other
                # cases.
                pass

        first_name, last_name = self.first_and_last_names(**cleaned_data)
        username = cleaned_data.get('username', None)
        password = cleaned_data.get('new_password',
            cleaned_data.get('password', None))
        user = self.model.objects.create_user(username,
            email=email, password=password, phone=phone,
            first_name=first_name, last_name=last_name)
        # Bypassing authentication here, we are doing frictionless registration
        # the first time around.
        user.backend = self.backend_path
        return user

    def register(self, **cleaned_data):
        user = self.register_user(**cleaned_data)
        _login(self.request, user)
        return user


class ActivationBaseView(RedirectFormMixin, ActivateMixin, UpdateView):
    """
    The user is now on the activation url that was sent in an email.
    It is time to complete the registration and activate the account.

    View that checks the hash in a password activation link and presents a
    form for entering a new password. We can activate the account for real
    once we know the email is valid and a password has been set.
    """
    form_class = ActivationForm
    http_method_names = ['get', 'post']

    @property
    def contact(self):
        if not hasattr(self, '_contact'):
            self._contact = Contact.objects.get_token(
                self.kwargs.get(self.key_url_kwarg))
        return self._contact

    def get_context_data(self, **kwargs):
        context = super(ActivationBaseView, self).get_context_data(**kwargs)
        if self.contact and self.contact.extra:
            # XXX might be best as a separate field.
            context.update({'reason': self.contact.extra})
        return context

    def get_form_class(self):
        if self.object and not has_invalid_password(self.object):
            return UserActivateForm
        return super(ActivationBaseView, self).get_form_class()

    def get_initial(self):
        if self.object:
            return {
                'email': self.object.email,
                'full_name': self.object.get_full_name(),
                'username': self.object.username}
        return {}

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        if is_authenticated(request):
            if request.user != self.object:
                auth_logout(request)
        # We put the code inline instead of using method_decorator() otherwise
        # kwargs is interpreted as parameters in sensitive_post_parameters.
        request.sensitive_post_parameters = '__ALL__'
        response = super(ActivationBaseView, self).dispatch(
            request, *args, **kwargs)
        add_never_cache_headers(response)
        return response

    def form_valid(self, form):
        user = self.activate_user(**form.cleaned_data)
        if user.last_login:
            messages.info(
                self.request, _("Thank you. Your account is now active."))

        # Okay, security check complete. Log the user in.
        password = form.cleaned_data.get(
            'password', form.cleaned_data.get('new_password'))
        user_with_backend = authenticate(
            self.request, username=user.username, password=password)
        _login(self.request, user_with_backend)
        if self.request.session.test_cookie_worked():
            self.request.session.delete_test_cookie()
        return HttpResponseRedirect(self.get_success_url())

    def get(self, request, *args, **kwargs):
        # We return a custom 404 page such that a user has a chance
        # to see an explanation of why clicking an expired link
        # in an e-mail leads to a 404.
        status_code = 200
        next_url = validate_redirect(self.request)
        if not self.object:
            status_code = 404
            messages.error(request, _("Activation failed. You may have"\
                " already activated your account previously. In that case,"\
                " just login. Thank you."))
            if next_url:
                return HttpResponseRedirect(next_url)
        elif is_authenticated(request) and self.request.user == self.object:
            user = self.activate_user()
            if user.last_login:
                messages.info(self.request,
                    _("Thank you for verifying your e-mail address."))
            return HttpResponseRedirect(self.get_success_url())
        return self.render_to_response(self.get_context_data(**kwargs),
            status=status_code)

    def get_object(self, queryset=None):  #pylint:disable=unused-argument
        token = self.contact
        return token.user if token else None


class SigninBaseView(RedirectFormMixin, ProcessFormView):
    """
    Check credentials and sign in the authenticated user.
    """
    model = get_user_model()
    form_class = AuthenticationForm
    password_form_class = AuthenticationForm

    def check_user_throttles(self, request, user):
        throttle = get_login_throttle()
        if throttle:
            throttle(request, self, user)

    def get_form_class(self):
        username = self.request.POST.get('username')
        if username:
            contact = Contact.objects.filter(user__username=username).first()
            if contact and contact.mfa_backend and contact.mfa_priv_key:
                return MFACodeForm
        password = self.request.POST.get('password')
        if password and not 'password' in self.form_class.base_fields:
            return self.password_form_class
        return self.form_class

    def get_form_kwargs(self):
        kwargs = super(SigninBaseView, self).get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def get_password_form(self):
        form_class = self.form_class
        if not 'password' in self.form_class.base_fields:
            form_class = self.password_form_class
        form = form_class(**self.get_form_kwargs())
        return form

    def get_mfa_form(self):
        form = MFACodeForm(**self.get_form_kwargs())
        # We must pass the username and password back to the browser
        # as hidden fields, but prevent calls to `form.non_field_errors()`
        # in the templates to inadvertently trigger a call
        # to `MFACodeForm.clean()`.
        form._errors = {} #pylint:disable=protected-access
        return form

    def form_valid(self, form):
        username = form.cleaned_data.get('username')
        try:
            user = self.model.objects.find_user(username)
        except self.model.DoesNotExist:
            form.add_error('username', _("username or password is incorrect."))
            return self.form_invalid(form)

        self.check_user_throttles(self.request, user)

        password = form.cleaned_data.get('password')
        if not password:
            form = self.get_password_form()
            form.is_valid()
            return self.form_invalid(form)

        user_with_backend = authenticate(self.request,
            username=username, password=password)

        contact = Contact.objects.filter(user=user_with_backend).first()
        if contact and contact.mfa_backend:
            if not contact.mfa_priv_key:
                form = self.get_mfa_form()
                contact.create_mfa_token()
                context = self.get_context_data(form=form)
                return self.render_to_response(context)
            # `get_form_class` will have returned `MFACodeForm`
            # if `mfa_priv_key` is not yet set, which in turn
            # will not make it this far is the code is incorrect.
            contact.clear_mfa_token()
        _login(self.request, user_with_backend)
        return super(SigninBaseView, self).form_valid(form)

    def form_invalid(self, form):
        username = form.cleaned_data.get('username')
        # It is possible username should be interpreted as an e-mail address
        # and yet be entered incorrectly, in which case the `username` key
        # won't be present in the `cleaned_data`.
        if username:
            try:
                user = self.model.objects.find_user(username)
                if not check_has_credentials(self.request, user):
                    form.add_error(None, _(
                        "This email address has already been registered!"\
                        " You should now secure and activate your account"\
                        " following the instructions we just emailed you."\
                        " Thank you."))
                else:
                    contact = Contact.objects.filter(user=user).first()
                    if contact and contact.mfa_backend:
                        if contact.mfa_nb_attempts >= settings.MFA_MAX_ATTEMPTS:
                            contact.clear_mfa_token()
                            form = self.get_form()
                            form.add_error(None, _("You have exceeded the"\
                                " number of attempts to enter the MFA code."\
                                " Please start again."))
                        else:
                            contact.mfa_nb_attempts += 1
                            contact.save()
            except self.model.DoesNotExist:
                # Django takes extra steps to make sure an attacker finds
                # it difficult to distinguish between a non-existant user
                # and an incorrect password on login.
                # This is only useful when registration is disabled otherwise
                # an attacker could simply use the register end-point instead.
                if not get_disabled_registration(self.request):
                    # If we have attempted to login a user that is not yet
                    # registered, automatically redirect to the registration
                    # page and pre-populate the form fields.
                    try:
                        validate_email(username)
                        query_params = {'email': username}
                        messages.error(self.request, _("This email is not yet"\
                            " registered. Would you like to do so?"))
                    except ValidationError:
                        query_params = {'username': username}
                        messages.error(self.request, _(
                            "This username is not yet"\
                            " registered. Would you like to do so?"))
                    next_url = validate_redirect(self.request)
                    if next_url:
                        query_params.update({REDIRECT_FIELD_NAME: next_url})
                    redirect_to = reverse('registration_register')
                    if query_params:
                        redirect_to += '?%s' % urlencode(query_params)
                    return HttpResponseRedirect(redirect_to)
        return super(SigninBaseView, self).form_invalid(form)


class SignoutBaseView(RedirectFormMixin, View):
    """
    Log out the authenticated user.
    """

    def get(self, request, *args, **kwargs): #pylint:disable=unused-argument
        LOGGER.info("%s signed out.", self.request.user,
            extra={'event': 'logout', 'request': request})
        auth_logout(request)
        next_url = self.get_success_url()
        response = HttpResponseRedirect(next_url)
        if settings.LOGOUT_CLEAR_COOKIES:
            for cookie in settings.LOGOUT_CLEAR_COOKIES:
                response.delete_cookie(cookie)
        return response


# Actual views to instantiate start here:

class ActivationView(AuthTemplateResponseMixin, ActivationBaseView):

    template_name = 'accounts/activate/verification_key.html'


class PasswordResetView(AuthTemplateResponseMixin, PasswordResetBaseView):

    template_name = 'accounts/recover.html'


class PasswordResetConfirmView(AuthTemplateResponseMixin,
                               PasswordResetConfirmBaseView):

    template_name = 'accounts/reset.html'


class SigninView(AuthTemplateResponseMixin, SigninBaseView):

    template_name = 'accounts/login.html'


class SignoutView(AuthTemplateResponseMixin, SignoutBaseView):

    template_name = 'accounts/logout.html'


class SignupView(AuthTemplateResponseMixin, SignupBaseView):

    template_name = 'accounts/register.html'
