# Copyright (c) 2020, DjaoDjin inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED
# TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
# OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
# OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
# ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""
Mockup login view used in testing.
"""
from __future__ import unicode_literals

from importlib import import_module

from django.conf import settings as django_settings
from django.contrib.auth import (REDIRECT_FIELD_NAME, login as auth_login,
    get_user_model)
from django import forms
from django.http.request import split_domain_port, validate_host
from django.views.generic.base import TemplateResponseMixin
from django.views.generic.edit import FormMixin, ProcessFormView

from ..import settings
from ..compat import urlparse, urlunparse
from .forms import SignupForm


class RedirectFormMixin(FormMixin):
    success_url = django_settings.LOGIN_REDIRECT_URL

    @staticmethod
    def validate_redirect_url(next_url):
        """
        Returns the next_url path if next_url matches allowed hosts.
        """
        if not next_url:
            return None
        parts = urlparse(next_url)
        if parts.netloc:
            domain, _ = split_domain_port(parts.netloc)
            allowed_hosts = (['*'] if django_settings.DEBUG
                else django_settings.ALLOWED_HOSTS)
            if not (domain and validate_host(domain, allowed_hosts)):
                return None
        return urlunparse(("", "", parts.path,
            parts.params, parts.query, parts.fragment))

    def get_success_url(self):
        next_url = self.validate_redirect_url(
            self.request.GET.get(REDIRECT_FIELD_NAME, None))
        if not next_url:
            next_url = super(RedirectFormMixin, self).get_success_url()
        return next_url

    def get_context_data(self, **kwargs):
        context = super(RedirectFormMixin, self).get_context_data(**kwargs)
        next_url = self.validate_redirect_url(
            self.request.GET.get(REDIRECT_FIELD_NAME, None))
        if next_url:
            context.update({REDIRECT_FIELD_NAME: next_url})
        return context


class AuthenticationForm(forms.Form):
    """
    Base class for authenticating users. Extend this to get a form that accepts
    username/password logins.
    """
    username = forms.CharField(max_length=254)
    password = forms.CharField(label="Password", widget=forms.PasswordInput)


class SigninView(TemplateResponseMixin, RedirectFormMixin, ProcessFormView):
    """
    Check credentials and sign in the authenticated user.
    """

    form_class = AuthenticationForm
    template_name = 'accounts/login.html'

    def form_valid(self, form):
        engine = import_module(django_settings.SESSION_ENGINE)
        session_store = engine.SessionStore()
        #pylint:disable=protected-access
        session_store._session_key = session_store.prepare(
            settings.MOCKUP_SESSIONS[form.cleaned_data['username']],
            settings.DJAODJIN_SECRET_KEY)
        session_store.modified = True
        self.request.session = session_store
        return super(SigninView, self).form_valid(form)


class SignupView(TemplateResponseMixin, RedirectFormMixin, ProcessFormView):
    """
    A frictionless registration backend With a full name and email
    address, the user is immediately signed up and logged in.
    """

    form_class = SignupForm
    template_name = 'accounts/register.html'

    def form_valid(self, form):
        self.register(**form.cleaned_data)
        return super(SignupView, self).form_valid(form)

    def register(self, **cleaned_data):
        #pylint: disable=maybe-no-member
        email = cleaned_data['email']
        first_name = cleaned_data.get('first_name', None)
        last_name = cleaned_data.get('last_name', None)
        if not first_name:
            # If the form does not contain a first_name/last_name pair,
            # we assume a full_name was passed instead.
            full_name = cleaned_data['full_name']
            name_parts = full_name.split(' ')
            if name_parts:
                first_name = name_parts[0]
                last_name = ' '.join(name_parts[1:])
            else:
                first_name = full_name
                last_name = ''
        username = cleaned_data.get('username', None)
        password = cleaned_data.get('password', None)
        user = get_user_model().objects.create_user(
            username=username, password=password,
            email=email, first_name=first_name, last_name=last_name)

        # Bypassing authentication here, the user just registered.
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        auth_login(self.request, user)
        return user
