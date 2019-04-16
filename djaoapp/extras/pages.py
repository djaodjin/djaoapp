# Copyright (c) 2019, DjaoDjin inc.
# see LICENSE

from __future__ import absolute_import

from django.http import Http404
from rules.extras import AppMixinBase
from saas.extras import OrganizationMixinBase
from saas.utils import get_organization_model

from ..compat import reverse


class ExtraMixin(OrganizationMixinBase, AppMixinBase):

    def get_organization(self):
        try:
            organization = super(ExtraMixin, self).get_organization()
        except Http404:
            # AccountModel is a rules.App because we need the bucket.
            if isinstance(self.account, get_organization_model()):
                organization = self.account
            else:
                organization = self.account.account
        return organization

    def get_context_data(self, **kwargs):
        context = super(ExtraMixin, self).get_context_data(**kwargs)
        self.update_context_urls(context, {
            'profile_redirect': reverse('accounts_profile'),
            'notifications': reverse('notification_base')
        })
        return context
