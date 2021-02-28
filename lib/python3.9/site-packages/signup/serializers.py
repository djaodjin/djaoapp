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

from django.core import validators
from django.contrib.auth import get_user_model
from django.utils.translation import ugettext_lazy as _
import phonenumbers
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from .models import Activity, Contact, Notification
from .utils import get_account_model, has_invalid_password
from .validators import (validate_email_or_phone,
    validate_username_or_email_or_phone)

LOGGER = logging.getLogger(__name__)


class PhoneField(serializers.CharField):

    def to_internal_value(self, data):
        """
        Returns a formatted phone number as a string.
        """
        if self.required:
            try:
                phone_number = phonenumbers.parse(data, None)
            except phonenumbers.NumberParseException as err:
                LOGGER.info("tel %s:%s", data, err)
                phone_number = None
            if not phone_number:
                try:
                    phone_number = phonenumbers.parse(data, "US")
                except phonenumbers.NumberParseException:
                    raise ValidationError(self.error_messages['invalid'])
            if phone_number and not phonenumbers.is_valid_number(phone_number):
                raise ValidationError(self.error_messages['invalid'])
            return phonenumbers.format_number(
                phone_number, phonenumbers.PhoneNumberFormat.E164)
        return None


class CommField(serializers.CharField):
    """
    Either an e-mail address or a phone number
    """
    default_error_messages = {
        'invalid': _('Enter a valid email address or phone number.')
    }

    def __init__(self, **kwargs):
        super(CommField, self).__init__(**kwargs)
        self.validators.append(validate_email_or_phone)


class UsernameOrCommField(serializers.CharField):
    """
    Either a username, e-mail address or a phone number
    """
    default_error_messages = {
        'invalid': _('Enter a valid username, email address or phone number.')
    }

    def __init__(self, **kwargs):
        super(UsernameOrCommField, self).__init__(**kwargs)
        self.validators.append(validate_username_or_email_or_phone)


class NoModelSerializer(serializers.Serializer):

    def create(self, validated_data):
        raise RuntimeError('`create()` should not be called.')

    def update(self, instance, validated_data):
        raise RuntimeError('`update()` should not be called.')


class ActivateUserSerializer(serializers.ModelSerializer):

    username = serializers.CharField(required=False,
        help_text=_("Username to identify the account"))
    new_password = serializers.CharField(required=False, write_only=True,
        style={'input_type': 'password'}, help_text=_("Password with which"\
            " a user can authenticate with the service"))
    full_name = serializers.CharField(required=False,
        help_text=_("Full name (effectively first name followed by last name)"))

    class Meta:
        model = get_user_model()
        fields = ('username', 'new_password', 'full_name')


class ActivitySerializer(serializers.ModelSerializer):

    account = serializers.SlugRelatedField(allow_null=True,
        slug_field='slug', queryset=get_account_model().objects.all(),
        help_text=_("Account the activity is associated to"))
    created_by = serializers.SlugRelatedField(
        read_only=True, slug_field='username',
        help_text=_("User that created the activity"))

    class Meta:
        model = Activity
        fields = ('created_at', 'created_by', 'text', 'account')
        read_only_fields = ('created_at', 'created_by')


class AuthenticatedUserPasswordSerializer(NoModelSerializer):

    password = serializers.CharField(write_only=True,
        style={'input_type': 'password'},
        help_text=_("Password of the user making the HTTP request"))

    class Meta:
        fields = ('password',)


class APIKeysSerializer(NoModelSerializer):
    """
    username and password for authentication through API.
    """
    secret = serializers.CharField(max_length=128, read_only=True,
        help_text=_("Secret API Key used to authenticate user on every HTTP"\
        " request"))

    class Meta:
        fields = ('secret',)


class PublicKeySerializer(AuthenticatedUserPasswordSerializer):
    """
    Updates a user public key
    """
    pubkey = serializers.CharField(max_length=500,
        style={'input_type': 'password'},
        help_text=_("New public key for the user referenced in the URL"))


class ContactSerializer(serializers.ModelSerializer):
    """
    This serializer is used in lists and other places where a Contact/User
    profile is referenced.
    For a detailed profile, see `ContactDetailSerializer`.
    """
    printable_name = serializers.CharField(
        help_text=_("Printable name"), read_only=True)
    credentials = serializers.SerializerMethodField(read_only=True,
        help_text=_("True if the user has valid login credentials"))

    class Meta:
        model = Contact
        fields = ('slug', 'printable_name', 'picture', 'email', 'created_at',
            'credentials',)
        read_only_fields = ('slug', 'printable_name', 'created_at',
            'credentials',)

    @staticmethod
    def get_credentials(obj):
        return (not has_invalid_password(obj.user)) if obj.user else False


class ContactDetailSerializer(ContactSerializer):
    """
    This serializer is used in APIs where a single Contact/User
    profile is returned.
    For a summary profile, see `ContactSerializer`.
    """
    activities = ActivitySerializer(many=True, read_only=True)

    class Meta(ContactSerializer.Meta):
        fields = ContactSerializer.Meta.fields + ('phone',
            'full_name', 'nick_name', 'extra', 'activities',)
        read_only_fields = ContactSerializer.Meta.read_only_fields + (
            'activities',)


class NotificationsSerializer(serializers.ModelSerializer):

    notifications = serializers.SlugRelatedField(many=True,
        slug_field='slug', queryset=Notification.objects.all())

    class Meta:
        model = get_user_model()
        fields = ('notifications',)


class CredentialsSerializer(NoModelSerializer):
    """
    username and password for authentication through API.
    """
    username = UsernameOrCommField(
        help_text=_("Username, e-mail address or phone number to identify"\
        " the account"))
    password = serializers.CharField(write_only=True,
        style={'input_type': 'password'},
        help_text=_("Secret password for the account"))
    code = serializers.IntegerField(required=False, write_only=True,
        style={'input_type': 'password'},
        help_text=_("One-time code. This field will be checked against"\
            " an expected code when multi-factor authentication (MFA)"\
            " is enabled."))


class CreateUserSerializer(serializers.ModelSerializer):

    username = serializers.CharField(required=False,
        help_text=_("Username to identify the account"))
    password = serializers.CharField(required=False, write_only=True,
        style={'input_type': 'password'}, help_text=_("Password with which"\
            " a user can authenticate with the service"))
    email = serializers.EmailField(
        help_text=_("Primary e-mail to contact user"), required=False)
    phone = PhoneField(
        help_text=_("Primary phone number to contact user"), required=False)
    full_name = serializers.CharField(
        help_text=_("Full name (effectively first name followed by last name)"))

    class Meta:
        model = get_user_model()
        fields = ('username', 'password', 'email', 'phone', 'full_name')


class PasswordResetConfirmSerializer(NoModelSerializer):

    new_password = serializers.CharField(write_only=True,
        style={'input_type': 'password'},
        help_text=_("New password for the user referenced in the URL"))


class PasswordChangeSerializer(PasswordResetConfirmSerializer):

    password = serializers.CharField(write_only=True,
        style={'input_type': 'password'},
        help_text=_("Password of the user making the HTTP request"))


class PasswordResetSerializer(NoModelSerializer):
    """
    Serializer to send an e-mail to a user in order to recover her account.
    """
    email = CommField(
        help_text=_("Email or phone number to recover the account"))


class TokenSerializer(NoModelSerializer):
    """
    token to verify or refresh.
    """
    token = serializers.CharField(
        help_text=_("Token used to authenticate user on every HTTP request"))


class ValidationErrorSerializer(NoModelSerializer):
    """
    Details on why token is invalid.
    """
    detail = serializers.CharField(help_text=_("Describes the reason for"\
        " the error in plain text"))


class UploadBlobSerializer(NoModelSerializer):
    """
    Upload a picture or other POD content
    """
    location = serializers.URLField(
        help_text=_("URL to uploaded content"))


class UserSerializer(serializers.ModelSerializer):
    """
    This serializer is a substitute for `ContactSerializer` whose intent is to
    facilitate composition of this App with other Django Apps which references
    a `django.contrib.auth.User model`. It is not used in this App.

    XXX currently used in `api.auth.JWTBase` for payloads.
    """

    # Only way I found out to remove the ``UniqueValidator``. We are not
    # interested to create new instances here.
    slug = serializers.CharField(source='username', validators=[
        validators.RegexValidator(r'^[\w.@+-]+$', _("Enter a valid username."),
            'invalid')],
        help_text=_("Username"))
    printable_name = serializers.CharField(source='get_full_name',
        help_text=_("Full name"))
    picture = serializers.SerializerMethodField(read_only=True,
        help_text=_("Picture"))
    email = serializers.EmailField(
        help_text=_("Primary e-mail to contact user"), required=False)
    phone = PhoneField(
        help_text=_("Primary phone number to contact user"), required=False)
    created_at = serializers.DateTimeField(source='date_joined',
        help_text=_("date at which the account was created"))
    credentials = serializers.SerializerMethodField(read_only=True,
        help_text=_("True if the user has valid login credentials"))
    # XXX username and full_name are duplicates of slug and printable_name
    # respectively. They are still included in this version for backward
    # compatibility.
    username = serializers.CharField(validators=[
        validators.RegexValidator(r'^[\w.@+-]+$', _("Enter a valid username."),
            'invalid')],
        help_text=_("Username"))
    full_name = serializers.CharField(source='get_full_name',
        help_text=_("Full name"))

    class Meta:
        model = get_user_model()
        fields = ('slug', 'printable_name', 'picture', 'email', 'phone',
            'created_at', 'credentials', 'username', 'full_name')
        read_only_fields = ('slug', 'printable_name', 'created_at',
            'credentials',)

    @staticmethod
    def get_credentials(obj):
        return not has_invalid_password(obj)

    @staticmethod
    def get_picture(obj):
        contact = obj.contacts.filter(picture__isnull=False).order_by(
            'created_at').first()
        if contact:
            return contact.picture
        return None
