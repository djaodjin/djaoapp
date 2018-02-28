# Copyright (c) 2018, DjaoDjin inc.
# see LICENSE

from __future__ import absolute_import

from django.core.urlresolvers import reverse
from multitier.thread_locals import get_current_site
from pages.extras import AccountMixinBase
from rules.extras import AppMixinBase


class ExtraMixin(AppMixinBase, AccountMixinBase):

    def get_context_data(self, **kwargs):
        context = super(ExtraMixin, self).get_context_data(**kwargs)
        # XXX might be overkill to always add ``site`` even though
        # it is only necessary in ``bank.html`` for Stripe callback.
        context.update({'site': get_current_site()})
        urls = {
            'user': {'profile_redirect': reverse('accounts_profile')},
            'notifications': reverse('notification_base')}
        self.update_context_urls(context, urls)
        return context
