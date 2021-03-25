# Copyright (c) 2020, DjaoDjin inc.
# see LICENSE

"""
Redirect for /billing/cart/
"""

from django.contrib.auth import REDIRECT_FIELD_NAME
from rules.mixins import AppMixin
from saas.views import OrganizationRedirectView as BaseOrganizationRedirectView
from saas.views.profile import (
    OrganizationCreateView as BaseOrganizationCreateView)
from signup.decorators import check_email_verified as check_email_verified_base


class OrganizationCreateView(AppMixin, BaseOrganizationCreateView):

    implicit_create_on_none = False

    def get_implicit_create_on_none(self):
        if self.app and self.app.get_implicit_create_on_none():
            return True
        return self.implicit_create_on_none


class OrganizationRedirectView(AppMixin, BaseOrganizationRedirectView):

    explicit_create_on_none = True
    implicit_create_on_none = False

    def check_email_verified(self, request, user,
                             redirect_field_name=REDIRECT_FIELD_NAME,
                             next_url=None):
        return check_email_verified_base(request, user,
            redirect_field_name=redirect_field_name, next_url=next_url)

    def get_implicit_create_on_none(self):
        if self.app and self.app.get_implicit_create_on_none():
            return True
        return self.implicit_create_on_none
