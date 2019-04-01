# Copyright (c) 2019, DjaoDjin inc.
# see LICENSE
from __future__ import unicode_literals

import logging

from rest_framework import filters
from saas.api.organizations import (
    OrganizationDetailAPIView as OrganizationDetailBaseAPIView,
    OrganizationListAPIView as OrganizationListBaseAPIView)
# XXX Temporary import of OrganizationSerializer until a new version
#     of djaodjin-saas is published.
from saas.api.serializers import (
    OrganizationSerializer as CreateOrganizationSerializer)
from saas.docs import swagger_auto_schema
from saas.utils import get_organization_model

from .serializers import (OrganizationSerializer,
    OrganizationWithSubscriptionsSerializer)


LOGGER = logging.getLogger(__name__)


class OrganizationDetailAPIView(OrganizationDetailBaseAPIView):
    """
    Retrieves profile information on an ``Organization``.

    **Tags: profile

    **Examples

    .. code-block:: http

        GET /api/profile/xia/ HTTP/1.1

    responds

    .. code-block:: json

        {
            "created_at": "2018-01-01T00:00:00Z",
            "email": "xia@locahost.localdomain",
            "full_name": "Xia Lee",
            "printable_name": "Xia Lee",
            "slug": "xia",
            "subscriptions": [
                {
                    "created_at": "2018-01-01T00:00:00Z",
                    "ends_at": "2019-01-01T00:00:00Z",
                    "plan": "open-space",
                    "auto_renew": true
                }
            ]
        }
    """
#    queryset = get_organization_model().objects.all()
    serializer_class = OrganizationWithSubscriptionsSerializer

    def put(self, request, *args, **kwargs):
        """
        Updates profile information for an ``Organization``

        **Tags: profile

        **Examples

        .. code-block:: http

            PUT /api/profile/xia/ HTTP/1.1

        .. code-block:: json

            {
              "email": "xia@locahost.localdomain",
              "full_name": "Xia Lee"
            }
        """
        return super(OrganizationDetailAPIView, self).put(
            request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        """
        Deletes an `Organization``.

        We anonymize the organization instead of purely deleting
        it from the database because we don't want to loose history
        on subscriptions and transactions.

        **Tags: profile

        **Examples

        .. code-block:: http

            DELETE /api/profile/xia/ HTTP/1.1
        """
        return super(OrganizationDetailAPIView, self).delete(
            request, *args, **kwargs)


class OrganizationListAPIView(OrganizationListBaseAPIView):
    """
    Queries all ``Organization``.

    **Tags: profile

    **Examples

    .. code-block:: http

        GET /api/profile/?o=created_at&ot=desc HTTP/1.1

    .. code-block:: http

        {
            "count": 1,
            "next": null,
            "previous": null,
            "results": [{
                "slug": "xia",
                "full_name": "Xia Lee",
                "printable_name": "Xia Lee",
                "created_at": "2016-01-14T23:16:55Z"
            }]
        }
    """
#    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
#    search_fields = ('full_name',)
#    ordering_fields = ('full_name',)
#    ordering = ('full_name',)
    serializer_class = OrganizationSerializer

    @swagger_auto_schema(request_body=CreateOrganizationSerializer)
    def post(self, request, *args, **kwargs):
        """
        Creates an``Organization``

        **Tags: profile

        **Examples

        .. code-block:: http

            POST /api/profile/xia/ HTTP/1.1

        .. code-block:: json

            {
              "email": "xia@locahost.localdomain",
              "full_name": "Xia Lee"
            }
        """
        return super(OrganizationListAPIView, self).post(
            request, *args, **kwargs)
