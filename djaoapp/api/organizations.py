# Copyright (c) 2019, DjaoDjin inc.
# see LICENSE
from __future__ import unicode_literals

import logging

from saas.api.organizations import (
    OrganizationDetailAPIView as OrganizationDetailBaseAPIView,
    OrganizationListAPIView as OrganizationListBaseAPIView)
from saas.api.serializers import OrganizationCreateSerializer
from saas.docs import swagger_auto_schema

from .serializers import (OrganizationSerializer, ProfileSerializer)


LOGGER = logging.getLogger(__name__)


class OrganizationDetailAPIView(OrganizationDetailBaseAPIView):
    """
    Retrieves a billing profile

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
            "phone": "555-555-5555",
            "street_address": "185 Berry St #550",
            "locality": "San Francisco",
            "region": "CA",
            "postal_code": "",
            "country": "US",
            "default_timezone": "Europe/Kiev",
            "is_provider": false,
            "is_bulk_buyer": false,
            "type": "",
            "picture": "",
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
    serializer_class = ProfileSerializer

    def put(self, request, *args, **kwargs):
        """
        Updates a billing profile

        **Tags: profile

        **Examples

        .. code-block:: http

            PUT /api/profile/xia/ HTTP/1.1

        responds

        .. code-block:: json

            {
              "email": "xia@locahost.localdomain",
              "full_name": "Xia Lee",
              "type": "personal"
            }
        """
        return super(OrganizationDetailAPIView, self).put(
            request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        """
        Deletes a billing profile

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
    Lists billing profiles

    Queries a page (``PAGE_SIZE`` records) of organization and user profiles.

    The queryset can be filtered for at least one field to match a search
    term (``q``).

    The queryset can be ordered by a field by adding an HTTP query parameter
    ``o=`` followed by the field name. A sequence of fields can be used
    to create a complete ordering by adding a sequence of ``o`` HTTP query
    parameters. To reverse the natural order of a field, prefix the field
    name by a minus (-) sign.

    **Tags: profile

    **Examples

    .. code-block:: http

        GET /api/profile/?o=created_at&ot=desc HTTP/1.1

    responds

    .. code-block:: json

        {
            "count": 1,
            "next": null,
            "previous": null,
            "results": [{
                "slug": "xia",
                "full_name": "Xia Lee",
                "email": "xia@localhost.localdomain",
                "created_at": "2016-01-14T23:16:55Z",
                "printable_name": "Xia Lee"
            }]
        }
    """
#    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
#    search_fields = ('full_name',)
#    ordering_fields = ('full_name',)
#    ordering = ('full_name',)
    serializer_class = OrganizationSerializer

    @swagger_auto_schema(request_body=OrganizationCreateSerializer)
    def post(self, request, *args, **kwargs):
        """
        Creates a billing profile

        **Tags: profile

        **Examples

        .. code-block:: http

            POST /api/profile/ HTTP/1.1

        .. code-block:: json

            {
              "email": "xia@locahost.localdomain",
              "full_name": "Xia Lee"
            }
        """
        return super(OrganizationListAPIView, self).post(
            request, *args, **kwargs)
