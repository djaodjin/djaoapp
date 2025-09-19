# Copyright (c) 2023, DjaoDjin inc.
# see LICENSE
from __future__ import unicode_literals

import logging

from saas.api.organizations import (
    OrganizationDetailAPIView as OrganizationDetailBaseAPIView,
    OrganizationListAPIView as OrganizationListBaseAPIView,
    OrganizationPictureAPIView as OrganizationPictureBaseAPIView)
from saas.utils import get_organization_model
from signup.models import Contact

from .serializers import (ProfileDetailSerializer, ProfileSerializer)


LOGGER = logging.getLogger(__name__)

class ProfileDecorateMixin(object):

    def decorate_personal(self, page):
        super(ProfileDecorateMixin, self).decorate_personal(page)
        organization_model = get_organization_model()
        records = [page] if isinstance(page, organization_model) else page
        for organization in records:
            if (hasattr(organization, 'is_personal') and
                organization.is_personal):
                contact = organization.attached_user().contacts.first()
                #pylint:disable=protected-access
                for field in Contact._meta.fields:
                    if not hasattr(organization, field.name):
                        setattr(organization, field.name,
                            getattr(contact, field.name) if contact else "")
        return page


class DjaoAppProfileDetailAPIView(ProfileDecorateMixin,
                                OrganizationDetailBaseAPIView):
    """
    Retrieves a billing profile

    The API is typically used within an HTML
    `contact information page </docs/guides/themes/#dashboard_profile>`_
    as present in the default theme.

    **Tags**: profile, subscriber, profilemodel

    **Examples

    .. code-block:: http

        GET /api/profile/xia HTTP/1.1

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
                    "plan": {
                        "slug": "open-space",
                        "title": "Open Space"
                    },
                    "auto_renew": true
                }
            ]
        }
    """
#    queryset = get_organization_model().objects.all()
    serializer_class = ProfileDetailSerializer

    def delete_records(self, user):
        user.contacts.all().update(user=None)
        user.notifications.all().delete()
        user.credentials.all().delete()

    def put(self, request, *args, **kwargs):
        """
        Updates a billing profile

        **Tags: profile, subscriber, profilemodel

        **Examples

        .. code-block:: http

            PUT /api/profile/xia HTTP/1.1

        .. code-block:: json

            {
              "email": "xia@locahost.localdomain",
              "full_name": "Xia Lee"
            }

        responds

        .. code-block:: json

            {
              "email": "xia@locahost.localdomain",
              "full_name": "Xia Lee",
              "type": "personal"
            }
        """
        #pylint:disable=useless-super-delegation
        return super(DjaoAppProfileDetailAPIView, self).put(
            request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        """
        Deletes a billing profile

        We anonymize the profile instead of purely deleting
        it from the database because we don't want to loose history
        on subscriptions and transactions.

        **Tags: profile, subscriber, profilemodel

        **Examples

        .. code-block:: http

            DELETE /api/profile/xia HTTP/1.1
        """
        #pylint:disable=useless-super-delegation
        return super(DjaoAppProfileDetailAPIView, self).delete(
            request, *args, **kwargs)


class DjaoAppProfileListAPIView(ProfileDecorateMixin,
                                OrganizationListBaseAPIView):
    """
    Lists billing profiles

    Returns a list of {{PAGE_SIZE}} profile and user accounts.

    The queryset can be further refined to match a search filter (``q``)
    and/or a range of dates ([``start_at``, ``ends_at``]),
    and sorted on specific fields (``o``).

    **Tags: profile

    **Examples

    .. code-block:: http

        GET /api/profile?o=created_at&ot=desc HTTP/1.1

    responds

    .. code-block:: json

        {
            "count": 1,
            "next": null,
            "previous": null,
            "results": [{
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
                "type": "personal",
                "picture": ""
            }]
        }
    """
    serializer_class = ProfileSerializer


class DjaoAppProfilePictureAPIView(ProfileDecorateMixin,
                                   OrganizationPictureBaseAPIView):
    """
        Uploads a static asset file

        **Examples

        .. code-block:: http

            POST /api/profile/xia/picture HTTP/1.1

        responds

        .. code-block:: json

            {
              "location": "https://cowork.net/picture.jpg"
            }
    """

    def post(self, request, *args, **kwargs):
        resp = super(DjaoAppProfilePictureAPIView, self).post(
            request, *args, **kwargs)
        location = resp.get('location')
        user = self.organization.attached_user()
        if user:
            Contact.objects.update_or_create(
                slug=self.kwargs.get(self.lookup_url_kwarg),
                defaults={'picture': location, 'user': user})
        return resp
