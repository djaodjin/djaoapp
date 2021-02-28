# Copyright (c) 2020, Djaodjin Inc.
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

"""
Backend to authenticate a User through her username, email address or
phone number

Add the UsernameOrEmailModelBackend to your project
settings.AUTHENTICATION_BACKENDS and use UsernameOrEmailAuthenticationForm
for the authentication_form parameter to your login urlpattern.

settings.py:

AUTHENTICATION_BACKENDS = (
    'signup.backends.auth.EmailOrUsernameModelBackend',
    'django.contrib.auth.backends.ModelBackend'
)

urls.py:

urlpatterns = patterns('',
    url(r'^login/$', 'django.contrib.auth.views.login',
        { 'authentication_form': UsernameOrEmailAuthenticationForm }
        name='login'),
)
"""
from __future__ import unicode_literals

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

from ..models import Contact
from ..validators import validate_phone


class UsernameOrEmailModelBackend(object):
    """
    Backend to authenticate a user through either her username
    or email address.
    """
    #pylint: disable=no-self-use
    model = get_user_model()

    def find_user(self, username):
        try:
            validate_email(username)
            kwargs = {'email__iexact': username}
        except ValidationError:
            kwargs = {'username__iexact': username}
        return self.model.objects.filter(is_active=True).get(**kwargs)

    def authenticate(self, request, username=None, password=None):
        #pylint:disable=unused-argument
        try:
            user = self.find_user(username)
            if user.check_password(password):
                return user
        except self.model.DoesNotExist:
            # Run the default password hasher once to reduce the timing
            # difference between an existing and a non-existing user (#20760).
            self.model().set_password(password)
        return None

    def get_user(self, user_id):
        try:
            return self.model.objects.get(pk=user_id)
        except self.model.DoesNotExist:
            return None


class UsernameOrEmailPhoneModelBackend(object):
    """
    Backend to authenticate a user through either her username,
    email address or phone number.
    """
    #pylint: disable=no-self-use
    model = get_user_model()

    def find_user(self, username):
        user_kwargs = {}
        contact_kwargs = {}
        username = str(username) # We could have a ``PhoneNumber`` here.
        try:
            validate_email(username)
            contact_kwargs = {'email__iexact': username}
            user_kwargs = {'email__iexact': username}
        except ValidationError:
            pass
        if not contact_kwargs:
            try:
                contact_kwargs = {'phone__iexact': validate_phone(username)}
            except ValidationError:
                contact_kwargs = {'user__username__iexact': username}
                user_kwargs = {'username__iexact': username}
        if user_kwargs:
            try:
                return self.model.objects.filter(
                    is_active=True).get(**user_kwargs)
            except self.model.DoesNotExist:
                pass
        try:
            contact = Contact.objects.filter(user__is_active=True,
                **contact_kwargs).select_related('user').get()
            return contact.user
        except Contact.DoesNotExist:
            pass
        raise self.model.DoesNotExist()

    def authenticate(self, request, username=None, password=None):
        #pylint:disable=unused-argument
        try:
            user = self.find_user(username)
            if user.check_password(password):
                return user
        except self.model.DoesNotExist:
            # Run the default password hasher once to reduce the timing
            # difference between an existing and a non-existing user (#20760).
            self.model().set_password(password)
        return None

    def get_user(self, user_id):
        try:
            return self.model.objects.get(pk=user_id)
        except self.model.DoesNotExist:
            return None
