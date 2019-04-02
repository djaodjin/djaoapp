# Copyright (c) 2019, DjaoDjin inc.
# see LICENSE
from __future__ import unicode_literals

import logging

from saas.utils import get_role_model
from signup.api.contacts import ContactDetailAPIView as UserProfileBaseAPIView

LOGGER = logging.getLogger(__name__)


class UserProfileAPIView(UserProfileBaseAPIView):
    """
    Retrieves, updates or deletes the profile information of a user.

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
        get_role_model().objects.filter(user=instance).delete()
        super(UserProfileAPIView, self).perform_destroy(instance)
