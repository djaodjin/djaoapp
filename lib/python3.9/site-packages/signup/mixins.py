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

import logging

from django.http import Http404
from django.contrib.auth import get_user_model
from rest_framework.generics import get_object_or_404

from . import signals
from .compat import is_authenticated, reverse, six
from .models import Contact


LOGGER = logging.getLogger(__name__)


class UrlsMixin(object):

    @staticmethod
    def update_context_urls(context, urls):
        if 'urls' in context:
            for key, val in six.iteritems(urls):
                if key in context['urls']:
                    if isinstance(val, dict):
                        context['urls'][key].update(val)
                    else:
                        # Because organization_create url is added in this mixin
                        # and in ``OrganizationRedirectView``.
                        context['urls'][key] = val
                else:
                    context['urls'].update({key: val})
        else:
            context.update({'urls': urls})
        return context


class ActivateMixin(object):

    key_url_kwarg = 'verification_key'

    def activate_user(self, **cleaned_data):
        verification_key = self.kwargs.get(self.key_url_kwarg)
        full_name = cleaned_data.get('full_name', None)
        if not full_name:
            first_name = cleaned_data.get('first_name', "")
            last_name = cleaned_data.get('last_name', "")
            full_name = (first_name + ' ' + last_name).strip()
        # If we don't save the ``User`` model here,
        # we won't be able to authenticate later.
        user, previously_inactive = Contact.objects.activate_user(
            verification_key,
            username=cleaned_data.get('username'),
            password=cleaned_data.get('new_password'),
            full_name=full_name)
        if user:
            if not user.last_login:
                # XXX copy/paste from models.ActivatedUserManager.create_user
                LOGGER.info("'%s %s <%s>' registered with username '%s'",
                    user.first_name, user.last_name, user.email, user,
                    extra={'event': 'register', 'user': user})
                signals.user_registered.send(sender=__name__, user=user)
            elif previously_inactive:
                LOGGER.info("'%s %s <%s>' activated with username '%s'",
                    user.first_name, user.last_name, user.email, user,
                    extra={'event': 'activate', 'user': user})
                signals.user_activated.send(sender=__name__, user=user,
                    verification_key=self.kwargs.get(self.key_url_kwarg),
                    request=self.request)
        return user


class ContactMixin(UrlsMixin):

    lookup_field = 'slug'
    lookup_url_kwarg = 'user'
    user_queryset = get_user_model().objects.filter(is_active=True)

    @property
    def contact(self):
        if not hasattr(self, '_contact'):
            kwargs = {self.lookup_field: self.kwargs.get(self.lookup_url_kwarg)}
            self._contact = get_object_or_404(Contact.objects.all(), **kwargs)
        return self._contact

    @staticmethod
    def as_contact(user):
        return Contact(slug=user.username, email=user.email,
            full_name=user.get_full_name(), nick_name=user.first_name,
            created_at=user.date_joined, user=user)

    def get_object(self):
        try:
            obj = super(ContactMixin, self).get_object()
        except Http404:
            # We might still have a `User` model that matches.
            lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
            filter_kwargs = {'username': self.kwargs[lookup_url_kwarg]}
            user = get_object_or_404(self.user_queryset, **filter_kwargs)
            obj = self.as_contact(user)
        return obj


class UserMixin(UrlsMixin):

    user_field = 'username'
    user_url_kwarg = 'user'
    user_queryset = get_user_model().objects.filter(is_active=True)

    @property
    def user(self):
        if not hasattr(self, '_user'):
            slug = self.kwargs.get(self.user_url_kwarg)
            if getattr(self.request.user, self.user_field) == slug:
                # Not only do we avoid one database query, we also
                # make sure the user is the actual wrapper object.
                self._user = self.request.user
            else:
                kwargs = {self.user_field: slug}
                self._user = get_object_or_404(self.user_queryset, **kwargs)
        return self._user

    def get_context_data(self, **kwargs):
        context = super(UserMixin, self).get_context_data(**kwargs)
        # URLs for user
        if is_authenticated(self.request):
            self.update_context_urls(context, {'user': {
                'notifications': reverse(
                    'users_notifications', args=(self.user,)),
                'profile': reverse('users_profile', args=(self.user,)),
                'profile_redirect': reverse('accounts_profile')
            }})
        return context
