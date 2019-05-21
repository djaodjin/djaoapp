# Copyright (c) 2019, DjaoDjin inc.
# see LICENSE
from __future__ import unicode_literals

import logging

from django.contrib.auth import get_user_model
from django.utils.translation import ugettext_lazy as _
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from saas.utils import get_role_model
from saas.models import Charge
from signup.api.users import UserDetailAPIView as UserProfileBaseAPIView

from .serializers import ActivitySerializer

LOGGER = logging.getLogger(__name__)


class UserProfileAPIView(UserProfileBaseAPIView):
    """
    Retrieves, updates or deletes the profile information of a user.

    **Tags: profile

    **Example

    .. code-block:: http

        GET /api/users/donny HTTP/1.1

    responds

    .. code-block:: json

        {
         "username": "donny",
         "email": "donny.smith@example.com"
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


class RecentActivityAPIView(GenericAPIView):
    serializer_class = ActivitySerializer

    def get(self, request, *args, **kwargs):
        users = get_user_model().objects.order_by('-last_login')[:5]
        charges = Charge.objects.order_by('-created_at')[:5]
        data = []
        for user in users:
            data.append({'printable_name': user.get_full_name(),
                'descr': _('recently logged in'),
                'created_at': user.last_login})
        for charge in charges:
            if charge.state == charge.DONE:
                descr = _('charge paid')
            elif charge.state == charge.FAILED:
                descr = _('charge failed')
            else:
                continue
            data.append({'printable_name': '%s: %s' % (charge.customer,
                charge.description), 'descr': descr,
                'created_at': user.last_login})
        return Response({'results': self.get_serializer(data, many=True).data})
