# Copyright (c) 2019, DjaoDjin inc.
# see LICENSE
from __future__ import unicode_literals

import logging

from django.utils.translation import ugettext_lazy as _
from saas.views.profile import DashboardView as BaseDashboardView
from saas.utils import is_broker, update_context_urls

from ..compat import reverse


LOGGER = logging.getLogger(__name__)


class DashboardView(BaseDashboardView):

    def get_context_data(self, **kwargs):
        context = super(DashboardView, self).get_context_data(**kwargs)
        if is_broker(self.organization):
            update_context_urls(context, {
                'api_todos': reverse('api_todos')
            })
        return context
