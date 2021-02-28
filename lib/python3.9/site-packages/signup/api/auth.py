# Copyright (c) 2021, DjaoDjin inc.
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

import logging

from django.contrib.auth import (REDIRECT_FIELD_NAME, get_user_model,
    authenticate, login as auth_login, logout as auth_logout)
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
import jwt
from rest_framework import exceptions, permissions, status, serializers
from rest_framework.generics import GenericAPIView, CreateAPIView
from rest_framework.response import Response


from .. import settings, signals
from ..auth import validate_redirect
from ..compat import reverse, six
from ..decorators import check_has_credentials
from ..docs import OpenAPIResponse, no_body, swagger_auto_schema
from ..helpers import as_timestamp, datetime_or_now, full_name_natural_split
from ..mixins import ActivateMixin
from ..models import Contact
from ..serializers import (ActivateUserSerializer, CredentialsSerializer,
    CreateUserSerializer,
    PasswordResetSerializer, PasswordResetConfirmSerializer,
    TokenSerializer, UserSerializer, ValidationErrorSerializer)
from ..utils import (get_disabled_authentication, get_disabled_registration,
    get_login_throttle, get_password_reset_throttle)


LOGGER = logging.getLogger(__name__)


class AllowAuthenticationEnabled(permissions.BasePermission):
    """
    Allows access only authentication is not disabled.
    """
    message = _("authentication has been temporarly disabled.")

    def has_permission(self, request, view):
        return not get_disabled_authentication(request)


class AllowRegistrationEnabled(permissions.BasePermission):
    """
    Allows access only when registration is not disabled.
    """
    message = _("registration is disabled.")

    def has_permission(self, request, view):
        return not get_disabled_registration(request)


class JWTBase(GenericAPIView):

    permission_classes = [AllowAuthenticationEnabled]
    serializer_class = TokenSerializer

    def create_token(self, user, expires_at=None):
        if not expires_at:
            exp = (as_timestamp(datetime_or_now())
                + self.request.session.get_expiry_age())
        else:
            exp = as_timestamp(expires_at)
        payload = UserSerializer().to_representation(user)
        payload.update({'exp': exp})
        token = jwt.encode(payload, settings.JWT_SECRET_KEY,
            settings.JWT_ALGORITHM).decode('utf-8')
        LOGGER.info("%s signed in.", user,
            extra={'event': 'login', 'request': self.request})
        return Response(TokenSerializer().to_representation({'token': token}),
            status=status.HTTP_201_CREATED)

    @staticmethod
    def optional_session_cookie(request, user):
        if request.query_params.get('cookie', False):
            auth_login(request, user)

    def permission_denied(self, request, message=None):
        # We override this function from `APIView`. The request will never
        # be authenticated by definition since we are dealing with login
        # and register APIs.
        raise exceptions.PermissionDenied(detail=message)


class JWTActivate(ActivateMixin, JWTBase):
    """
    Retrieves user associated to an activation key

    Retrieves information about a user based on an activation key.

    **Tags: auth

    **Example

    .. code-block:: http

        GET /api/auth/activate/0123456789abcef0123456789abcef/ HTTP/1.1

    responds

    .. code-block:: json

        {
          "slug": "joe1",
          "username": "joe1",
          "email": "joe1@localhost.localdomain",
          "full_name": "Joe Act",
          "printable_name": "Joe Act",
          "created_at": "2020-05-30T00:00:00Z"
        }
    """
    model = get_user_model()
    serializer_class = ActivateUserSerializer

    def get_serializer_class(self):
        if self.request.method.lower() == 'get':
            return UserSerializer
        return super(JWTActivate, self).get_serializer_class()

    def get(self, request, *args, **kwargs):#pylint:disable=unused-argument
        verification_key = self.kwargs.get(self.key_url_kwarg)
        token = Contact.objects.get_token(verification_key=verification_key)
        if not token:
            raise serializers.ValidationError({'detail': "invalid request"})
        serializer = self.get_serializer(token.user)
        return Response(serializer.data)

    @swagger_auto_schema(responses={
        201: OpenAPIResponse("", TokenSerializer),
        400: OpenAPIResponse("parameters error", ValidationErrorSerializer)})
    def post(self, request, *args, **kwargs):#pylint:disable=unused-argument
        """
        Activates a user

        Activates a new user and returns a JSON Web Token that can subsequently
        be used to authenticate the new user in HTTP requests.

        **Tags: auth

        **Example

        .. code-block:: http

            POST /api/auth/activate/0123456789abcef0123456789abcef/ HTTP/1.1

        .. code-block:: json

            {
              "username": "joe1",
              "new_password": "yoyo",
              "full_name": "Joe Card1"
            }

        responds

        .. code-block:: json

            {
                "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VybmFtZSI6\
    ImpvZTEiLCJlbWFpbCI6ImpvZSsxQGRqYW9kamluLmNvbSIsImZ1bGxfbmFtZ\
    SI6IkpvZSAgQ2FyZDEiLCJleHAiOjE1Mjk2NTUyMjR9.GFxjU5AvcCQbVylF1P\
    JwcBUUMECj8AKxsHtRHUSypco"
            }
        """
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            # We are not using `is_valid(raise_exception=True)` here
            # because we do not want to give clues on the reasons for failure.
            user = self.activate_user(**serializer.validated_data)
            if user:
                # Okay, security check complete. Log the user in.
                user_with_backend = authenticate(
                    request, username=user.username,
                    password=serializer.validated_data.get('new_password'))
                self.optional_session_cookie(request, user_with_backend)
                return self.create_token(user_with_backend)
        raise serializers.ValidationError({'detail': "invalid request"})


class JWTLogin(JWTBase):
    """
    Logs a user in

    Returns a JSON Web Token that can be used in requests that require
    authentication.

    **Tags: auth

    **Example

    .. code-block:: http

        POST /api/auth/ HTTP/1.1

    .. code-block:: json

        {
          "username": "donny",
          "password": "yoyo"
        }

    responds

    .. code-block:: json

        {"token":"eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VybmFtZSI6\
ImRvbm55IiwiZW1haWwiOiJzbWlyb2xvKzRAZGphb2RqaW4uY29tIiwiZnV\
sbF9uYW1lIjoiRG9ubnkgQ29vcGVyIiwiZXhwIjoxNTI5NjU4NzEwfQ.F2y\
1iwj5NHlImmPfSff6IHLN7sUXpBFmX0qjCbFTe6A"}
    """
    model = get_user_model()
    serializer_class = CredentialsSerializer

    def check_user_throttles(self, request, user):
        throttle = get_login_throttle()
        if throttle:
            throttle(request, self, user)

    @swagger_auto_schema(responses={
        201: OpenAPIResponse("", TokenSerializer),
        400: OpenAPIResponse("parameters error", ValidationErrorSerializer)})
    def post(self, request, *args, **kwargs):
        #pylint:disable=unused-argument,too-many-nested-blocks
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            username = serializer.validated_data.get('username')
            password = serializer.validated_data.get('password')
            try:
                user = self.model.objects.find_user(username)

                # Rate-limit based on the user.
                self.check_user_throttles(self.request, user)

                user = authenticate(
                    request, username=username, password=password)
                if user:
                    contact = Contact.objects.find_by_username_or_comm(
                        username).first()
                    if contact and contact.mfa_backend:
                        if not contact.mfa_priv_key:
                            contact.create_mfa_token()
                            raise serializers.ValidationError({'detail': _(
                                "missing MFA token")})
                        code = serializer.validated_data.get('code')
                        if code != contact.mfa_priv_key:
                            if (contact.mfa_nb_attempts
                                >= settings.MFA_MAX_ATTEMPTS):
                                contact.clear_mfa_token()
                                raise exceptions.PermissionDenied({'detail': _(
    "You have exceeded the number of attempts to enter the MFA code."\
    " Please start again.")})
                            contact.mfa_nb_attempts += 1
                            contact.save()
                            raise serializers.ValidationError({'detail': _(
                                "MFA code does not match.")})
                        contact.clear_mfa_token()
                    self.optional_session_cookie(request, user)
                    return self.create_token(user)

                if not check_has_credentials(request, user):
                    raise serializers.ValidationError({'detail': _(
                "This email address has already been registered!"\
               " You should now secure and activate your account following"\
                " the instructions we just emailed you. Thank you.")})
            except self.model.DoesNotExist:
                pass
        raise exceptions.PermissionDenied()


class JWTPasswordResetConfirm(JWTBase):
    """
    Confirms a password reset

    Sets a new password after a recover password was triggered
    and returns a JSON Web Token that can subsequently
    be used to authenticate the new user in HTTP requests.

    **Tags: auth

    **Example

    .. code-block:: http

        POST /api/auth/reset/0123456789abcef0123456789abcef/abc123/ HTTP/1.1

    .. code-block:: json

        {
          "new_password": "yoyo",
          "new_password2": "yoyo"
        }

    responds

    .. code-block:: json

        {
            "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VybmFtZSI6\
ImpvZTEiLCJlbWFpbCI6ImpvZSsxQGRqYW9kamluLmNvbSIsImZ1bGxfbmFtZ\
SI6IkpvZSAgQ2FyZDEiLCJleHAiOjE1Mjk2NTUyMjR9.GFxjU5AvcCQbVylF1P\
JwcBUUMECj8AKxsHtRHUSypco"
        }
    """
    model = get_user_model()
    serializer_class = PasswordResetConfirmSerializer
    token_generator = default_token_generator

    @swagger_auto_schema(responses={
        201: OpenAPIResponse("", TokenSerializer),
        400: OpenAPIResponse("parameters error", ValidationErrorSerializer)})
    def post(self, request, *args, **kwargs):#pylint:disable=unused-argument
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            # We are not using `is_valid(raise_exception=True)` here
            # because we do not want to give clues on the reasons for failure.
            try:
                uid = urlsafe_base64_decode(self.kwargs.get('uidb64'))
                if not isinstance(uid, six.string_types):
                    # See Django2.2 release notes
                    uid = uid.decode()
                user = self.model.objects.get(pk=uid)
            except (TypeError, ValueError, OverflowError,
                    self.model.DoesNotExist):
                user = None
            if user is not None and self.token_generator.check_token(
                                        user, self.kwargs.get('token')):
                new_password = serializer.validated_data['new_password']
                user.set_password(new_password)
                user.save()
                LOGGER.info("%s reset her/his password.", user,
                    extra={'event': 'resetpassword', 'request': request})
                user_with_backend = authenticate(
                    request, username=user.username, password=new_password)
                self.optional_session_cookie(request, user_with_backend)
                return self.create_token(user_with_backend)
        raise serializers.ValidationError({'detail': "invalid request"})


class JWTRegister(JWTBase):
    """
    Registers a user

    Creates a new user and returns a JSON Web Token that can subsequently
    be used to authenticate the new user in HTTP requests.

    **Tags: auth

    **Example

    .. code-block:: http

        POST /api/auth/register/ HTTP/1.1

    .. code-block:: json

        {
          "username": "joe1",
          "password": "yoyo",
          "email": "joe+1@example.com",
          "full_name": "Joe Card1"
        }

    responds

    .. code-block:: json

        {
            "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VybmFtZSI6\
ImpvZTEiLCJlbWFpbCI6ImpvZSsxQGRqYW9kamluLmNvbSIsImZ1bGxfbmFtZ\
SI6IkpvZSAgQ2FyZDEiLCJleHAiOjE1Mjk2NTUyMjR9.GFxjU5AvcCQbVylF1P\
JwcBUUMECj8AKxsHtRHUSypco"
        }
    """
    model = get_user_model()
    permission_classes = [AllowAuthenticationEnabled, AllowRegistrationEnabled]
    serializer_class = CreateUserSerializer

    def register_user(self, **validated_data):
        #pylint: disable=maybe-no-member
        email = validated_data['email']
        users = self.model.objects.filter(email=email)
        if users.exists():
            user = users.get()
            if check_has_credentials(self.request, user):
                raise serializers.ValidationError(mark_safe(_(
                    'This email address has already been registered!'\
' Please <a href="%s">login</a> with your credentials. Thank you.'
                    % reverse('login'))))
            raise serializers.ValidationError(mark_safe(_(
                "This email address has already been registered!"\
" You should now secure and activate your account following "\
" the instructions we just emailed you. Thank you.")))

        first_name, mid_name, last_name = full_name_natural_split(
            validated_data['full_name'], middle_initials=False)
        if mid_name:
            first_name = (first_name + " " + mid_name).strip()
        username = validated_data.get('username', None)
        password = validated_data.get('password', None)
        user = self.model.objects.create_user(username,
            email=email, password=password,
            first_name=first_name, last_name=last_name)

        # Bypassing authentication here, we are doing frictionless registration
        # the first time around.
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        return user

    def register(self, serializer):
        return self.register_user(**serializer.validated_data)

    @swagger_auto_schema(responses={
        201: OpenAPIResponse("", TokenSerializer),
        400: OpenAPIResponse("parameters error", ValidationErrorSerializer)})
    def post(self, request, *args, **kwargs):#pylint:disable=unused-argument
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            # We are not using `is_valid(raise_exception=True)` here
            # because we do not want to give clues on the reasons for failure.
            user = self.register(serializer)
            if user:
                self.optional_session_cookie(request, user)
                return self.create_token(user)
        raise serializers.ValidationError({'detail': "invalid request"})


class JWTLogout(JWTBase):
    """
    Logs a user out

    Removes all cookies associated with the session.

    This API endpoint is only useful when the user is using Cookie-based
    authentication. Tokens expire; they cannot be revoked.

    **Tags: auth

    **Example

    .. code-block:: http

        POST /api/auth/logout/  HTTP/1.1
    """
    @swagger_auto_schema(request_body=no_body, responses={
        200: OpenAPIResponse("success", no_body)})
    def post(self, request, *args, **kwargs):#pylint:disable=unused-argument
        LOGGER.info("%s signed out.", self.request.user,
            extra={'event': 'logout', 'request': request})
        auth_logout(request)
        response = Response(status=status.HTTP_200_OK)
        if settings.LOGOUT_CLEAR_COOKIES:
            for cookie in settings.LOGOUT_CLEAR_COOKIES:
                response.delete_cookie(cookie)
        return response


class PasswordResetAPIView(CreateAPIView):
    """
    Emails a password reset link

    The user is uniquely identified by her email address.

    **Tags: auth

    **Examples

    .. code-block:: http

         POST /api/auth/recover/ HTTP/1.1

    .. code-block:: json

        {
            "email": "xia@localhost.localdomain"
        }

    responds

    .. code-block:: json

        {
            "email": "xia@localhost.localdomain"
        }
    """
    model = get_user_model()
    permission_classes = [AllowAuthenticationEnabled]
    serializer_class = PasswordResetSerializer
    token_generator = default_token_generator

    def check_user_throttles(self, request, user):
        throttle = get_password_reset_throttle()
        if throttle:
            throttle(request, self, user)

    def perform_create(self, serializer):
        try:
            username = serializer.validated_data.get('email')
            user = self.model.objects.find_user(username)

            # Rate-limit based on the user.
            self.check_user_throttles(self.request, user)

            next_url = validate_redirect(self.request)
            if check_has_credentials(self.request, user, next_url=next_url):
                # Make sure that a reset password email is sent to a user
                # that actually has an activated account.
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                if not isinstance(uid, six.string_types):
                    # See Django2.2 release notes
                    uid = uid.decode()
                token = self.token_generator.make_token(user)
                back_url = self.request.build_absolute_uri(
                    reverse('password_reset_confirm', args=(uid, token)))
                if next_url:
                    back_url += '?%s=%s' % (REDIRECT_FIELD_NAME, next_url)
                signals.user_reset_password.send(
                    sender=__name__, user=user, request=self.request,
                    back_url=back_url, expiration_days=settings.KEY_EXPIRATION)
            else:
                raise serializers.ValidationError({'detail': _(
                    "Please activate your"\
                    " account first. You should receive an email shortly.")})
        except self.model.DoesNotExist:
            # We don't want to give a clue about registered users, yet
            # it already possible to do a straight register to get the same.
            raise serializers.ValidationError({'detail': _(
                "We cannot find an account"\
                " for this e-mail address. Please verify the spelling.")})

    def permission_denied(self, request, message=None):
        # We override this function from `APIView`. The request will never
        # be authenticated by definition since we are dealing with login
        # and register APIs.
        raise exceptions.PermissionDenied(detail=message)
