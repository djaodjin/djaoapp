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

from __future__ import absolute_import

import logging, random

from django.contrib.auth.backends import RemoteUserBackend
from django.contrib.auth import get_user_model
from django.db.utils import DatabaseError

from ..compat import check_signature, six
from ....helpers import full_name_natural_split

# Beware that if you are using `deployutils.apps.django.logging.RequestFilter`
# to add `%(username)s` to log entries, there will be a recursive loop through
# django.contrib.auth calls coming here.
LOGGER = logging.getLogger(__name__)

UserModel = get_user_model() #pylint:disable=invalid-name


class ProxyUserBackend(RemoteUserBackend):

    users = {}

    def user_can_authenticate(self, user):
        """
        Reject users with is_active=False. Custom user models that don't have
        that attribute are allowed.
        """
        is_active = getattr(user, 'is_active', None)
        return is_active or is_active is None

    def authenticate(self, request, remote_user=None):
        #pylint:disable=arguments-differ
        # Django <=1.8 and >=1.9 have different signatures.
        """
        The ``username`` passed here is considered trusted.  This
        method simply returns the ``User`` object with the given username.

        In order to support older Django versions
        (before commit 4b9330ccc04575f9e5126529ec355a450d12e77c), if username
        is None, we will assume request is the ``remote_user`` parameter.
        """
        if not remote_user:
            remote_user = request
        if not remote_user:
            return None

        user = None
        username = self.clean_username(remote_user)
        try:
            #pylint:disable=protected-access
            if self.create_unknown_user:
                defaults = {}
                if isinstance(request, dict):
                    session_data = request
                    if 'full_name' in session_data:
                        first_name, _, last_name = full_name_natural_split(
                            session_data['full_name'])
                        defaults.update({
                            'first_name': first_name,
                            'last_name': last_name
                        })
                    for key in ('email', 'first_name', 'last_name'):
                        if key in session_data:
                            defaults.update({key: session_data[key]})
                user, created = UserModel._default_manager.get_or_create(**{
                    UserModel.USERNAME_FIELD: username,
                    'defaults': defaults,
                })
                if created:
                    LOGGER.debug("created user '%s' in database.", username)
                    args = (request, user)
                    try:
                        check_signature(self.configure_user, *args)
                    except TypeError:
                        args = (user,)
                    user = self.configure_user(*args)
            else:
                try:
                    user = UserModel._default_manager.get_by_natural_key(
                        username)
                except UserModel.DoesNotExist:
                    pass
        except DatabaseError as err:
            LOGGER.debug("User table missing from database? (err:%s)", err)
            # We don't have a auth_user table, so let's build a hash in memory.
            for user in six.itervalues(self.users):
                LOGGER.debug("match %s with User(id=%d, username=%s)",
                    username, user.id, user.username)
                if user.username == username:
                    LOGGER.debug("found %d %s", user.id, user.username)
                    return user
            # Not found in memory dict
            user = UserModel(
                id=random.randint(1, (1 << 32) - 1), username=username)
            LOGGER.debug("add User(id=%d, username=%s) to cache.",
                user.id, user.username)
            self.users[user.id] = user
        return user if self.user_can_authenticate(user) else None

    def get_user(self, user_id):
        try:
            #pylint:disable=protected-access
            user = UserModel._default_manager.get(pk=user_id)
        except UserModel.DoesNotExist:
            return None
        except DatabaseError:
            user = self.users.get(user_id, None)
        return user if self.user_can_authenticate(user) else None
