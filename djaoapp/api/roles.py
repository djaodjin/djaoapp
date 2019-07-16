# Copyright (c) 2019, DjaoDjin inc.
# see LICENSE
from __future__ import unicode_literals

import logging

from saas.api.roles import RoleByDescrListAPIView as RoleListBaseAPIView
from saas.utils import get_role_model

from .serializers import RoleSerializer


LOGGER = logging.getLogger(__name__)


class RoleListAPIView(RoleListBaseAPIView):
    """
    Lists roles of a specific type

    Lists the specified role assignments for an organization.

    **Tags: rbac

    **Examples

    .. code-block:: http

        GET /api/profile/cowork/roles/manager/ HTTP/1.1

    responds

    .. code-block:: json

        {
            "count": 1,
            "next": null,
            "previous": null,
            "results": [
                {
                    "created_at": "2018-01-01T00:00:00Z",
                    "role_description": {
                        "name": "Manager",
                        "slug": "manager",
                        "organization": {
                            "slug": "cowork",
                            "full_name": "ABC Corp.",
                            "printable_name": "ABC Corp.",
                            "created_at": "2018-01-01T00:00:00Z",
                            "email": "support@localhost.localdomain"
                        }
                    },
                    "user": {
                        "slug": "alice",
                        "email": "alice@localhost.localdomain",
                        "full_name": "Alice Doe",
                        "created_at": "2018-01-01T00:00:00Z"
                    },
                    "request_key": "1",
                    "grant_key": null
                }
            ]
        }
    """
    serializer_class = RoleSerializer
    queryset = get_role_model().objects.all().select_related('user__contact')
