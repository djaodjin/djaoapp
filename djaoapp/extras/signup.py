# Copyright (c) 2023, DjaoDjin inc.
# see LICENSE

from __future__ import absolute_import

from extended_templates.extras import AccountMixinBase
from rules.extras import AppMixinBase
from saas.extras import OrganizationMixinBase

from ..compat import reverse


class ExtraMixin(AppMixinBase, AccountMixinBase, OrganizationMixinBase):

    def get_organization(self):
        from saas.models import get_broker # to avoid import loops
        return get_broker()

    def get_context_data(self, **kwargs):
        context = super(ExtraMixin, self).get_context_data(**kwargs)
        return context
