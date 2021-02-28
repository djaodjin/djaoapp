# Copyright (c) 2020, DjaoDjin inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED
# TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
# OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
# OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
# ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import hashlib, logging, os, re

from django.contrib.auth import logout as auth_logout
from django.db import transaction, IntegrityError
from django.core.exceptions import PermissionDenied
from django.contrib.auth import update_session_auth_hash, get_user_model
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _
from rest_framework import parsers, status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import (CreateAPIView, ListCreateAPIView,
    RetrieveUpdateDestroyAPIView, GenericAPIView, UpdateAPIView)
from rest_framework.response import Response
from rest_framework.settings import api_settings


from .. import filters, settings
from ..compat import urlparse, urlunparse
from ..decorators import check_has_credentials
from ..docs import OpenAPIResponse, no_body, swagger_auto_schema
from ..helpers import full_name_natural_split
from ..mixins import ContactMixin
from ..models import Contact
from ..serializers import (ContactSerializer, ContactDetailSerializer,
    PasswordChangeSerializer, NotificationsSerializer, UploadBlobSerializer,
    ValidationErrorSerializer)
from ..utils import generate_random_code, get_picture_storage, handle_uniq_error


LOGGER = logging.getLogger(__name__)


def get_order_func(fields):
    """
    Builds a lambda function that can be used to order two records
    based on a sequence of fields.

    When a field name is preceeded by '-', the order is reversed.
    """
    if len(fields) == 1:
        if fields[0].startswith('-'):
            field_name = fields[0][1:]
            return lambda left, right: (
                getattr(left, field_name) > getattr(right, field_name))
        field_name = fields[0]
        return lambda left, right: (
            getattr(left, field_name) < getattr(right, field_name))
    if fields[0].startswith('-'):
        field_name = fields[0][1:]
        return lambda left, right: (
            getattr(left, field_name) > getattr(right, field_name) or
            get_order_func(fields[1:])(left, right))
    field_name = fields[0]
    return lambda left, right: (
        getattr(left, field_name) < getattr(right, field_name) or
        get_order_func(fields[1:])(left, right))


class UserActivateAPIView(ContactMixin, GenericAPIView):
    """
    Re-sends an activation link

    Re-sends an activation e-mail if the user is not already activated.

    The template for the e-mail sent to the user can be found in
    notification/verification.eml.

    **Tags: auth

    **Example

    .. code-block:: http

        POST /api/users/donny/activate/ HTTP/1.1

    responds

    .. code-block:: json

        {
            "slug": "xia",
            "email": "xia@locahost.localdomain",
            "full_name": "Xia Lee",
            "nick_name": "Xia",
            "created_at": "2018-01-01T00:00:00Z"
        }
    """
    serializer_class = ContactSerializer
    queryset = Contact.objects.all().select_related('user')

    @swagger_auto_schema(request_body=no_body, responses={
        201: OpenAPIResponse("success", ContactSerializer),
        400: OpenAPIResponse("parameters error", ValidationErrorSerializer)})
    def post(self, request, *args, **kwargs):#pylint:disable=unused-argument
        instance = self.get_object()
        if check_has_credentials(request, instance.user):
            raise ValidationError({'detail': _("User is already active")})
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class UserDetailAPIView(ContactMixin, RetrieveUpdateDestroyAPIView):
    """
    Retrieves a login profile

    Retrieves details on one single user profile with slug ``{user}``.

    **Tags: profile

    **Examples

    .. code-block:: http

        GET /api/users/xia HTTP/1.1

    responds

    .. code-block:: json

        {
            "slug": "xia",
            "email": "xia@locahost.localdomain",
            "full_name": "Xia Lee",
            "nick_name": "Xia",
            "created_at": "2018-01-01T00:00:00Z",
            "activities": [{
              "created_at": "2018-01-01T00:00:00Z",
              "created_by": "alice",
              "text": "Phone call",
              "account": null
            },{
              "created_at": "2018-01-02T00:00:00Z",
              "created_by": "alice",
              "text": "Follow up e-mail",
              "account": "cowork"
            }]
        }
    """
    serializer_class = ContactDetailSerializer
    queryset = Contact.objects.all().select_related('user')

    def put(self, request, *args, **kwargs):
        """
        Updates a login profile

        **Tags: profile

        **Examples

        .. code-block:: http

            PUT /api/users/xia/ HTTP/1.1

        .. code-block:: json

            {
              "email": "xia@locahost.localdomain",
              "full_name": "Xia Lee",
              "nick_name": "Xia"
            }

        responds

        .. code-block:: json

            {
              "email": "xia@locahost.localdomain",
              "full_name": "Xia Lee",
              "nick_name": "Xia"
            }
        """
        return self.update(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        """
        Updates a login profile

        **Tags: profile

        **Examples

        .. code-block:: http

            PATCH /api/users/xia/ HTTP/1.1

        .. code-block:: json

            {
              "email": "xia@locahost.localdomain",
              "full_name": "Xia Lee",
              "nick_name": "Xia"
            }

        responds

        .. code-block:: json

            {
              "email": "xia@locahost.localdomain",
              "full_name": "Xia Lee",
              "nick_name": "Xia"
            }
        """
        return self.partial_update(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        """
        Deletes a login profile

        **Tags: profile

        **Examples

        .. code-block:: http

            DELETE /api/users/xia/ HTTP/1.1
        """
        return self.destroy(request, *args, **kwargs)

    def perform_destroy(self, instance):
        if instance.user:
            pkid = instance.user.pk
            email = instance.user.email
            username = instance.user.username
        else:
            email = instance.email
            pkid = instance.pk if instance.pk else generate_random_code()
            username = instance.slug if instance.slug else ("%d" % pkid)

        # We mark the user as inactive and scramble personal information
        # such that we don't remove audit records (ex: billing transactions)
        # from the database.
        slug = '_archive_%d' % pkid
        LOGGER.info("%s deleted user profile for '%s <%s>' (%s).",
            self.request.user, username, email, slug, extra={'event': 'delete',
                'request': self.request, 'username': username, 'email': email,
                'pk': pkid})

        look = re.match(r'.*(@\S+)', settings.DEFAULT_FROM_EMAIL)
        if look:
            email = '%s%s' % (slug, look.group(1))

        with transaction.atomic():
            if instance.pk:
                instance.slug = slug
                instance.email = email
            user = instance.user
            if user:
                requires_logout = (self.request.user == user)
                user.username = slug
                user.email = email
                user.password = '!'
                user.is_active = False
                user.save()
                if requires_logout:
                    auth_logout(self.request)

    def perform_update(self, serializer):
        with transaction.atomic():
            user = serializer.instance.user
            try:
                if user:
                    if serializer.validated_data.get('email'):
                        user.email = serializer.validated_data.get('email')
                    if serializer.validated_data.get('slug'):
                        user.username = serializer.validated_data.get('slug')
                    if serializer.validated_data.get('full_name'):
                        first_name, mid_name, last_name = \
                            full_name_natural_split(
                                serializer.validated_data.get('full_name'),
                                middle_initials=False)
                        user.first_name = first_name
                        if mid_name:
                            user.first_name = (
                                first_name + " " + mid_name).strip()
                        user.last_name = last_name
                    user.save()
                serializer.save()
            except IntegrityError as err:
                handle_uniq_error(err)


class UserListCreateAPIView(ListCreateAPIView):
    """
    Lists user profiles

    Queries a page (``PAGE_SIZE`` records) of organization and user profiles.

    The queryset can be filtered for at least one field to match a search
    term (``q``).

    The queryset can be ordered by a field by adding an HTTP query parameter
    ``o=`` followed by the field name. A sequence of fields can be used
    to create a complete ordering by adding a sequence of ``o`` HTTP query
    parameters. To reverse the natural order of a field, prefix the field
    name by a minus (-) sign.

    **Tags: profile

    **Example

    .. code-block:: http

        GET /api/users/?q=xia HTTP/1.1

    responds

    .. code-block:: json

        {
            "count": 1,
            "next": null,
            "previous": null,
            "results": [{
              "slug": "xia",
              "email": "xia@locahost.localdomain",
              "full_name": "Xia Lee",
              "nick_name": "Xia",
              "created_at": "2018-01-01T00:00:00Z",
              "activities": [{
                "created_at": "2018-01-01T00:00:00Z",
                "created_by": "alice",
                "text": "Phone call",
                "account": null
              },{
                "created_at": "2018-01-02T00:00:00Z",
                "created_by": "alice",
                "text": "Follow up e-mail",
                "account": "cowork"
              }]
            }]
        }
    """
    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
    search_fields = (
        'email',
        # fields in User model:
        'username',
    )
    ordering_fields = (
        'full_name',
        'created_at',
        'date_joined')

    ordering = ('full_name',)
    alternate_ordering = ('first_name', 'last_name')
    serializer_class = ContactSerializer
    queryset = Contact.objects.all().select_related('user')
    user_queryset = get_user_model().objects.filter(is_active=True)

    def get_serializer_class(self):
        if self.request.method.lower() == 'post':
            return ContactDetailSerializer
        return super(UserListCreateAPIView, self).get_serializer_class()

    @swagger_auto_schema(request_body=ContactDetailSerializer, responses={
        201: OpenAPIResponse("success", ContactDetailSerializer),
        400: OpenAPIResponse("parameters error", ValidationErrorSerializer)})
    def post(self, request, *args, **kwargs):
        """
        Creates a user profile

        **Tags: profile

        **Examples

        .. code-block:: http

            POST /api/users/ HTTP/1.1

        .. code-block:: json

            {
              "email": "xia@locahost.localdomain",
              "full_name": "Xia Lee",
              "nick_name": "Xia"
            }

        responds

        .. code-block:: json

            {
              "email": "xia@locahost.localdomain",
              "full_name": "Xia Lee",
              "nick_name": "Xia"
            }
        """
        return self.create(request, *args, **kwargs)

    @staticmethod
    def as_contact(user):
        return Contact(slug=user.username, email=user.email,
            full_name=user.get_full_name(), nick_name=user.first_name,
            created_at=user.date_joined, user=user)

    def get_users_queryset(self):
        return self.user_queryset.filter(contacts__isnull=True)

    def list(self, request, *args, **kwargs):
        #pylint:disable=too-many-locals,too-many-statements
        contacts_queryset = self.filter_queryset(self.get_queryset())
        contacts_page = self.paginate_queryset(contacts_queryset)
        # XXX When we use a `rest_framework.PageNumberPagination`,
        # it will hold a reference to the page created by a `DjangoPaginator`.
        # The `LimitOffsetPagination` paginator holds its own count.
        if hasattr(self.paginator, 'page'):
            contacts_count = self.paginator.page.paginator.count
        else:
            contacts_count = self.paginator.count

        users_queryset = self.filter_queryset(self.get_users_queryset())
        users_page = self.paginate_queryset(users_queryset)
        # Since we run a second `paginate_queryset`, the paginator.count
        # is not the number of users.
        if hasattr(self.paginator, 'page'):
            self.paginator.page.paginator.count += contacts_count
        else:
            self.paginator.count += contacts_count

        order_func = get_order_func(filters.OrderingFilter().get_ordering(
            self.request, contacts_queryset, self))

        # XXX merge `users_page` into page.
        page = []
        user = None
        contact = None
        users_iterator = iter(users_page)
        contacts_iterator = iter(contacts_page)
        try:
            contact = next(contacts_iterator)
        except StopIteration:
            pass
        try:
            user = self.as_contact(next(users_iterator))
        except StopIteration:
            pass
        try:
            while contact and user:
                if order_func(contact, user):
                    page += [contact]
                    contact = None
                    contact = next(contacts_iterator)
                elif order_func(user, contact):
                    page += [user]
                    user = None
                    user = self.as_contact(next(users_iterator))
                else:
                    page += [contact]
                    contact = None
                    contact = next(contacts_iterator)
                    page += [user]
                    user = None
                    user = self.as_contact(next(users_iterator))
        except StopIteration:
            pass
        try:
            while contact:
                page += [contact]
                contact = next(contacts_iterator)
        except StopIteration:
            pass
        try:
            while user:
                page += [user]
                user = self.as_contact(next(users_iterator))
        except StopIteration:
            pass

        # XXX It could be faster to stop previous loops early but it is not
        # clear. The extra check at each iteration might in fact be slower.
        page = page[:api_settings.PAGE_SIZE]

        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    def perform_create(self, serializer):
        user_model = self.user_queryset.model
        with transaction.atomic():
            try:
                user = user_model.objects.get(
                    email=serializer.validated_data.get('email'))
            except user_model.DoesNotExist:
                user = None
            serializer.save(user=user)


class PasswordChangeAPIView(GenericAPIView):
    """
    Changes a user password
    """
    lookup_field = 'username'
    lookup_url_kwarg = 'user'
    serializer_class = PasswordChangeSerializer
    queryset = get_user_model().objects.filter(is_active=True)

    @swagger_auto_schema(responses={
        200: OpenAPIResponse("success", ValidationErrorSerializer)})
    def put(self, request, *args, **kwargs):
        """
        Changes a user password

        **Tags: auth

        **Example

        .. code-block:: http

            PUT /api/users/donny/password/ HTTP/1.1

        .. code-block:: json

            {
              "password": "yeye",
              "new_password": "yoyo"
            }

        responds

        .. code-block:: json

            {
              "detail": "Password updated successfully."
            }
        """
        #pylint:disable=unused-argument
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)

        password = serializer.validated_data['password']
        new_password = serializer.validated_data.get('new_password')
        if not self.request.user.check_password(password):
            raise PermissionDenied(_("Incorrect credentials"))
        if new_password:
            serializer.instance.set_password(new_password)
            serializer.instance.save()
            # Updating the password logs out all other sessions for the user
            # except the current one if
            # django.contrib.auth.middleware.SessionAuthenticationMiddleware
            # is enabled.
            update_session_auth_hash(self.request, serializer.instance)

        return Response({'detail': _("Password updated successfully.")})


class UserNotificationsAPIView(UpdateAPIView):
    """
    Changes a user notifications preferences

    **Tags: profile

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
    lookup_field = 'username'
    lookup_url_kwarg = 'user'
    serializer_class = NotificationsSerializer
    queryset = get_user_model().objects.filter(is_active=True)


class UserPictureAPIView(ContactMixin, CreateAPIView):
    """
        Uploads a picture for the user profile

        **Examples

        .. code-block:: http

            POST /api/users/xia/picture/ HTTP/1.1

        responds

        .. code-block:: json

            {
              "location": "https://cowork.net/picture.jpg"
            }
    """
    parser_classes = (parsers.FormParser, parsers.MultiPartParser)
    serializer_class = UploadBlobSerializer

    def post(self, request, *args, **kwargs):
        #pylint:disable=unused-argument
        uploaded_file = request.data.get('file')
        if not uploaded_file:
            return Response({'detail': "no location or file specified."},
                status=status.HTTP_400_BAD_REQUEST)

        # tentatively extract file extension.
        parts = os.path.splitext(
            force_text(uploaded_file.name.replace('\\', '/')))
        ext = parts[-1].lower() if len(parts) > 1 else ""
        key_name = "%s%s" % (
            hashlib.sha256(uploaded_file.read()).hexdigest(), ext)
        default_storage = get_picture_storage(request)

        location = default_storage.url(
            default_storage.save(key_name, uploaded_file))
        # We are removing the query parameters, as they contain
        # signature information, not the relevant URL location.
        parts = urlparse(location)
        location = urlunparse((parts.scheme, parts.netloc, parts.path,
            "", "", ""))
        location = self.request.build_absolute_uri(location)
        user_model = self.user_queryset.model
        with transaction.atomic():
            try:
                user = user_model.objects.get(
                    username=self.kwargs.get(self.lookup_url_kwarg))
            except user_model.DoesNotExist:
                user = None
            Contact.objects.update_or_create(
                slug=self.kwargs.get(self.lookup_url_kwarg),
                defaults={'picture': location, 'user': user})
        return Response(self.get_serializer().to_representation(
            {'location': location}), status=status.HTTP_201_CREATED)
