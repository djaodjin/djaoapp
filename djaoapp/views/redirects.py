# Copyright (c) 2019, DjaoDjin inc.
# see LICENSE

"""
Redirect for /billing/cart/
"""

from rules.mixins import AppMixin
from saas.views import OrganizationRedirectView as BaseOrganizationRedirectView


class OrganizationRedirectView(AppMixin, BaseOrganizationRedirectView):

    explicit_create_on_none = True
    implicit_create_on_none = False

    def get_implicit_create_on_none(self):
        if self.app and self.app.get_implicit_create_on_none():
            return True
        return self.implicit_create_on_none
