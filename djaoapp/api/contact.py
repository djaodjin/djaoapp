# Copyright (c) 2023, DjaoDjin inc.
# see LICENSE
from __future__ import unicode_literals

import logging, socket
from smtplib import SMTPException
import googlemaps

from deployutils.apps.django.compat import is_authenticated
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.conf import settings
from rest_framework import status
from rest_framework.settings import api_settings
from rest_framework.filters import SearchFilter
from rest_framework.generics import GenericAPIView, ListAPIView, RetrieveAPIView
from rest_framework.response import Response
from saas.api.serializers import ValidationErrorSerializer
from saas.docs import extend_schema, OpenApiResponse
from saas.mixins import ProviderMixin
from saas.models import Organization
from saas.pagination import TypeaheadPagination
from saas.utils import full_name_natural_split

from ..compat import gettext_lazy as _, six
from ..signals import user_contact
from .serializers import (ContactUsSerializer, PlacesSuggestionSerializer,
    PlacesDetailSerializer)


LOGGER = logging.getLogger(__name__)


class ContactUsAPIView(ProviderMixin, GenericAPIView):
    """
    Sends a contact-us message

    Emails a free form contact-us message from a customer to the provider

    The API is typically used within an HTML
    `contact page </docs/guides/themes/#workflow_contact>`_
    as present in the default theme.

    **Tags: visitor

    **Example

    .. code-block:: http

        POST /api/contact HTTP/1.1

    .. code-block:: json

        {
          "email": "joe+1@example.com",
          "full_name": "Joe Card1",
          "message": "Can I request a demo?"
        }

    responds

    .. code-block:: json

        {
            "detail": "Your request has been sent. We will reply within\
24 hours. Thank you."
        }
    """
    serializer_class = ContactUsSerializer

    @extend_schema(responses={
        200: OpenApiResponse(ValidationErrorSerializer)})
    def post(self, request, *args, **kwargs):
        #pylint:disable=too-many-locals,unused-argument
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if is_authenticated(self.request):
            user = self.request.user
        else:
            user_model = get_user_model()
            email = serializer.validated_data.get('email', None)
            try:
                user = user_model.objects.get(email=email)
            except user_model.DoesNotExist:
                #pylint:disable=unused-variable
                first_name, mid, last_name = full_name_natural_split(
                    serializer.validated_data.get('full_name', None))
                user = user_model(
                    email=email, first_name=first_name, last_name=last_name)
        message = serializer.validated_data.get('message', '')
        provider = serializer.validated_data.get('provider', self.provider)
        items = []
        for key, value in six.iteritems(serializer.data):
            if value and not (key in serializer.validated_data or
                key in ('captcha', 'g-recaptcha-response',
                    'csrfmiddlewaretoken')):
                items += [(key, value)]
        if message:
            items += [("Message", message)]
        if not user.email:
            return Response({'detail':
    _("Thank you for the feedback. Please feel free to leave your contact"\
" information next time so we can serve you better.")})
        if provider:
            provider = get_object_or_404(Organization, slug=provider)
        else:
            provider = self.provider
        try:
            user_contact.send(
                sender=__name__, provider=provider,
                user=user, reason=items, request=self.request)
            return Response({'detail':
_("Your request has been sent. We will reply within 24 hours. Thank you.")})
        except (SMTPException, socket.error) as err:
            LOGGER.exception("%s on page %s",
                err, self.request.get_raw_uri())
            return Response({'detail':
_("Sorry, there was an issue sending your request for information"\
" to '%(full_name)s &lt;%(email)s&gt;'.") % {
    'full_name': provider.full_name, 'email': provider.email}})


class PlacesSuggestionsAPIView(ListAPIView):
    """
    Lists street address candidates

    The API is typically used within a profile page.

    **Tags**: profile

    **Examples

    .. code-block:: http

        GET /api/accounts/places?q=123 HTTP/1.1

    responds

    .. code-block:: json

       {
            "count": 5,
            "results": [
                {
                "description": "123 William Street, New York, NY, USA",
                "place_id": "ChIJIaGbBBhawokRUmbgNsUmr-s"
                },
                {
                "description": "1230 6th Avenue, New York, NY, USA",
                "place_id": "ChIJC8abO_9YwokRlbzMgC8_XWE"
                },
                {
                "description": "1233 York Avenue, New York, NY, USA",
                "place_id": "ChIJ1_GF_cJYwokR8u455JHGkBA"
                },
                {
                "description": "123 Melrose Street, Brooklyn, NY, USA",
                "place_id": "ChIJZbhuygdcwokR_5NT5POb8Z8"
                },
                {
                "description": "1239 Broadway, New York, NY, USA",
                "place_id": "ChIJMebitahZwokRa9MwUrkbedc"
                }
            ]
        }
    """
    schema = None
    serializer_class = PlacesSuggestionSerializer
    pagination_class = TypeaheadPagination
    filter_backends = (SearchFilter, )

    def get_queryset(self):
        gmaps = googlemaps.Client(key=settings.GOOGLE_API_KEY)
        query = self.request.query_params.get(api_settings.SEARCH_PARAM)

        if query and len(query) > 2:
            results = gmaps.places_autocomplete(query, types='address')
        else:
            results = []

        return results


class PlacesDetailAPIView(RetrieveAPIView):
    """
    Retrieves a street address candidate

    The API is typically used in conjunction with
    typeahead query API within a profile page.

    **Tags**: profile

    **Examples

    .. code-block:: http

        GET /api/accounts/places/ChIJIaGbBBhawokRUmbgNsUmr-s HTTP/1.1

    responds

    .. code-block:: json

    {
        "street_number": "123",
        "route": "William Street",
        "postal_code": "10038",
        "sublocality": "Manhattan",
        "locality": "New York",
        "state": "New York",
        "state_code": "NY",
        "country": "United States",
        "country_code": "US"
    }
    """
    schema = None
    serializer_class = PlacesDetailSerializer

    @extend_schema(responses={
        200: OpenApiResponse(PlacesDetailSerializer)})
    def get(self, request, *args, **kwargs):
        gmaps = googlemaps.Client(key=settings.GOOGLE_API_KEY)
        place_id = kwargs.get('place_id')
        if place_id:
            try:
                result = gmaps.place(place_id)
                if result['status'] == 'OK':
                    serializer = self.get_serializer(result['result'])
                    return Response(serializer.data)
            except:
                pass

        return Response(status=status.HTTP_404_NOT_FOUND)
