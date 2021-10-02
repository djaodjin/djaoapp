# Copyright (c) 2021, DjaoDjin inc.
# see LICENSE
from __future__ import unicode_literals

import logging
from operator import itemgetter

from django.contrib.auth import get_user_model
from django.utils.translation import ugettext_lazy as _
from rest_framework.generics import ListAPIView

from saas.models import Charge
from saas.metrics.base import day_periods
from saas.utils import get_role_model
from signup.api.users import (UserDetailAPIView as UserDetailBaseAPIView,
    UserNotificationsAPIView as UserNotificationsBaseAPIView)

from ..mixins import NotificationsMixin
from .serializers import RecentActivitySerializer

LOGGER = logging.getLogger(__name__)


class DjaoAppUserDetailAPIView(UserDetailBaseAPIView):
    """
    Retrieves a login profile

    **Tags: profile, user, usermodel

    **Example

    .. code-block:: http

        GET /api/users/donny/ HTTP/1.1

    responds

    .. code-block:: json

        {
          "slug": "donny",
          "username": "donny",
          "created_at": "2018-01-01T00:00:00Z",
          "printable_name": "Donny",
          "full_name": "Donny Smith",
          "email": "donny.smith@locahost.localdomain"
        }
    """
    def perform_destroy(self, instance):
        # We will archive the user record to keep audit foreign keys
        # in place but we delete the roles on organizations
        # for that user to make sure access rights for the archive profile
        # are fully gone.
        if instance:
            get_role_model().objects.filter(user=instance).delete()
        super(DjaoAppUserDetailAPIView, self).perform_destroy(instance)


class DjaoAppUserNotificationsAPIView(NotificationsMixin,
                                      UserNotificationsBaseAPIView):
    """
    Lists a user notifications preferences

    **Tags: profile, user, usermodel

    **Example

    .. code-block:: http

        GET /api/users/donny/notifications/ HTTP/1.1

    responds

    .. code-block:: json

        {
          "notifications": ["user_registered_notice"]
        }
    """

    def put(self, request, *args, **kwargs):
        """
        Changes a user notifications preferences

        **Tags: profile, user, usermodel

        **Example

        .. code-block:: http

            POST /api/users/donny/notifications/ HTTP/1.1

        .. code-block:: json

            {
              "notifications": ["user_registered_notice"]
            }

        responds

        .. code-block:: json

            {
              "notifications": ["user_registered_notice"]
            }
        """
        return self.update(request, *args, **kwargs)


class RecentActivityAPIView(ListAPIView):
    """
    Retrieves recently active users

    The API is typically used within an HTML
    `dashboard page </docs/themes/#dashboard_metrics_dashboard>`_
    as present in the default theme.

    **Tags: metrics, broker, appmodel

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
    serializer_class = RecentActivitySerializer

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
                'created_at': user.last_login, 'type': "user"}
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
