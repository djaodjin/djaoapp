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

from django.conf import settings as django_settings
from django.db import DEFAULT_DB_ALIAS

from . import settings
from .compat import get_app_model_class, six
from .thread_locals import get_current_site


class SiteRouter(object):
    """
    A router to control all database operations on Django models in a set
    of ``apps`` and SQL tables in a set of ``tables``.
    """
    #pylint: disable=protected-access

    apps = settings.ROUTER_APPS
    tables = settings.ROUTER_TABLES

    @staticmethod
    def provider_db():
        if hasattr(django_settings, 'MULTITIER_NAME'):
            # ``manage.py loaddata`` will call db_for_write for relation
            # tables. Since we don't have a ``request`` then, we rely
            # on an environment variable.
            return django_settings.MULTITIER_NAME
        current_site = get_current_site()
        if current_site:
            return current_site.db_name
        return DEFAULT_DB_ALIAS

    def includes(self, model):
        if isinstance(model, six.string_types):
            return model in self.apps
        return (model._meta.app_label in self.apps
                or model._meta.db_table in self.tables)


    def db_for_read(self, model, **hints): #pylint: disable=unused-argument
        """
        Attempts to read ``apps`` models go to the current provider.
        """
        result = None
        if self.includes(model):
            result = self.provider_db()
        return result

    def db_for_write(self, model, **hints): #pylint: disable=unused-argument
        """
        Attempts to write ``apps`` models to the current provider.
        """
        result = None
        if self.includes(model):
            result = self.provider_db()
        return result

    def allow_relation(self, obj1, obj2, **hints):
        #pylint: disable=unused-argument
        """
        Allow relations if a model in the ``apps`` is involved.
        """
        if obj1._meta.app_label in self.apps or \
                obj2._meta.app_label in self.apps:
            return True
        return None

    # XXX Note here running tests with Django <1.7 will call
    #     allow_syncdb instead.
    def allow_migrate(self, database, app_label, model_name=None, **hints):
        """
        Make sure the apps only appears in the current provider
        database.
        """
        result = True
        model = hints.get('model')
        if model is None:
            if model_name is not None:
                model = get_app_model_class(app_label, model_name)
            else:
                # Django 1.7 prototype is allow_migrate(self, db, model)
                model = app_label
        if database != DEFAULT_DB_ALIAS:
            result = self.includes(model)
        return result
