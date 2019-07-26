# Copyright (c) 2019, DjaoDjin inc.
# see LICENSE
from __future__ import unicode_literals

import logging
from operator import itemgetter

from django.contrib.auth import get_user_model
from django.utils.translation import ugettext_lazy as _
from rest_framework.generics import ListAPIView
from rest_framework.response import Response

from saas.models import Charge
from saas.managers.metrics import day_periods
from saas.utils import get_role_model
from signup.api.users import UserDetailAPIView as UserProfileBaseAPIView

from .serializers import ActivitySerializer

LOGGER = logging.getLogger(__name__)


class UserProfileAPIView(UserProfileBaseAPIView):
    """
    Retrieves a login profile

    **Tags: profile

    **Example

    .. code-block:: http

        GET /api/users/donny HTTP/1.1

    responds

    .. code-block:: json

        {
          "username": "donny",
          "email": "donny.smith@locahost.localdomain",
          "full_name": "Donny Smith"
        }
    """
    def perform_destroy(self, instance):
        # We will archive the user record to keep audit foreign keys
        # in place but we delete the roles on organizations
        # for that user to make sure access rights for the archive profile
        # are fully gone.
        if instance.user:
            get_role_model().objects.filter(user=instance.user).delete()
        super(UserProfileAPIView, self).perform_destroy(instance)


class RecentActivityAPIView(ListAPIView):
    """
    Retrieves recently active users

    **Tags: metrics

    **Example

    .. code-block:: http

        GET /api/proxy/recent/ HTTP/1.1

    responds

    .. code-block:: json

        {
          "count": 1,
          "next": null,
          "previous": null,
          "results": [
            {
              "printable_name": "Alice Cooper",
              "descr": "recently logged in",
              "created_at": "2019-07-15T20:40:29.509572Z",
              "slug": "alice"
            }
          ]
        }
    """
    serializer_class = ActivitySerializer

    def get_queryset(self):
        start_at = day_periods()[0]
        users = get_user_model().objects.filter(
            last_login__gt=start_at).order_by('-last_login')[:5]
        charges = Charge.objects.filter(
            created_at__gt=start_at).order_by('-created_at')[:5]
        data = {}
        for user in users:
            data[user.username] = {'printable_name': user.get_full_name(),
                'descr': _('recently logged in'), 'slug': user.username,
                'created_at': user.last_login}
        for charge in charges:
            if charge.state == charge.DONE:
                descr = _('charge paid')
            elif charge.state == charge.FAILED:
                descr = _('charge failed')
            else:
                continue
            data[charge.customer.slug] = {'printable_name':
                charge.customer.printable_name, 'descr': descr,
                'created_at': charge.created_at,
                # TODO 404 for some of the slugs
                'slug': charge.customer.slug}
        data = sorted(data.values(), key=itemgetter('printable_name'))
        return data
