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

import logging, re

from django.apps import apps as django_apps
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured, NON_FIELD_ERRORS
from django.core.files.storage import default_storage
from django.db import IntegrityError
from django.utils.crypto import get_random_string
from django.utils.translation import ugettext_lazy as _
import jwt
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.settings import api_settings

from . import settings
from .compat import import_string, six

LOGGER = logging.getLogger(__name__)


def get_accept_list(request):
    http_accept = request.META.get('HTTP_ACCEPT', '*/*')
    return [item.strip() for item in http_accept.split(',')]


def generate_random_code():
    return int(generate_random_slug(6, allowed_chars="0123456789"))


def generate_random_slug(length=40, prefix=None,
                         allowed_chars="abcdef0123456789"):
    """
    This function is used, for example, to create Coupon code mechanically
    when a customer pays for the subscriptions of an organization which
    does not yet exist in the database.
    """
    if prefix:
        length = length - len(prefix)
    if settings.RANDOM_SEQUENCE:
        suffix = settings.RANDOM_SEQUENCE[settings.RANDOM_SEQUENCE_IDX]
        settings.RANDOM_SEQUENCE_IDX += 1
    else:
        suffix = get_random_string(length=length, allowed_chars=allowed_chars)
    if prefix:
        return str(prefix) + suffix
    return suffix


def get_account_model():
    """
    Returns the ``Account`` model that is active in this project.
    """
    try:
        return django_apps.get_model(settings.ACCOUNT_MODEL)
    except ValueError:
        raise ImproperlyConfigured(
            "ACCOUNT_MODEL must be of the form 'app_label.model_name'")
    except LookupError:
        raise ImproperlyConfigured("ACCOUNT_MODEL refers to model '%s'"\
" that has not been installed" % settings.ACCOUNT_MODEL)


def has_invalid_password(user):
    return not user.password or user.password.startswith('!')


def printable_name(user):
    full_name = user.get_full_name()
    if full_name:
        return full_name
    return user.username


def update_db_row(instance, form):
    """
    Updates the record in the underlying database, or adds a validation
    error in the form. When an error is added, the form is returned otherwise
    this function returns `None`.
    """
    try:
        try:
            instance.save()
        except IntegrityError as err:
            handle_uniq_error(err)
    except ValidationError as err:
        fill_form_errors(form, err)
        return form
    return None


def fill_form_errors(form, err):
    """
    Fill a Django form from DRF ValidationError exceptions.
    """
    if isinstance(err.detail, dict):
        for field, msg in six.iteritems(err.detail):
            if field in form.fields:
                form.add_error(field, msg)
            elif field == api_settings.NON_FIELD_ERRORS_KEY:
                form.add_error(NON_FIELD_ERRORS, msg)
            else:
                form.add_error(NON_FIELD_ERRORS,
                    _("No field '%(field)s': %(msg)s" % {
                    'field': field, 'msg': msg}))


def handle_uniq_error(err, renames=None):
    """
    Will raise a ``ValidationError`` with the appropriate error message.
    """
    field_name = None
    err_msg = str(err).splitlines().pop()
    # PostgreSQL unique constraint.
    look = re.match(
        r'DETAIL:\s+Key \(([a-z_]+)\)=\(.*\) already exists\.', err_msg)
    if look:
        field_name = look.group(1)
    else:
        look = re.match(
          r'DETAIL:\s+Key \(lower\(([a-z_]+)::text\)\)=\(.*\) already exists\.',
            err_msg)
        if look:
            field_name = look.group(1)
        else:
            # SQLite unique constraint.
            look = re.match(
                r'UNIQUE constraint failed: [a-z_]+\.([a-z_]+)', err_msg)
            if look:
                field_name = look.group(1)
            else:
                # On CentOS 7, installed sqlite 3.7.17
                # returns differently-formatted error message.
                look = re.match(
                    r'column ([a-z_]+) is not unique', err_msg)
                if look:
                    field_name = look.group(1)
    if field_name:
        if renames and field_name in renames:
            field_name = renames[field_name]
        if field_name in ('email',):
            # We treat these fields differently because translation of `this`
            # is different depending on the `field_name`.
            raise ValidationError({field_name:
                _("This e-mail address is already taken.")})
        raise ValidationError({field_name:
            _("This %(field)s is already taken.") % {'field': field_name}})
    raise err


def verify_token(token):
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            True, # verify
            options={'verify_exp': True},
            algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignature:
        raise serializers.ValidationError(
            _("Signature has expired."))
    except jwt.DecodeError:
        raise serializers.ValidationError(
            _("Error decoding signature."))
    username = payload.get('username', None)
    if not username:
        raise serializers.ValidationError(
            _("Missing username in payload"))
    # Make sure user exists
    user_model = get_user_model()
    try:
        user = user_model.objects.get(username=username)
    except user_model.DoesNotExist:
        raise serializers.ValidationError(_("User does not exist."))
    return user


def get_disabled_authentication(request):
    if isinstance(settings.DISABLED_AUTHENTICATION, six.string_types):
        return import_string(settings.DISABLED_AUTHENTICATION)(request)
    return bool(settings.DISABLED_AUTHENTICATION)


def get_disabled_registration(request):
    if isinstance(settings.DISABLED_REGISTRATION, six.string_types):
        return import_string(settings.DISABLED_REGISTRATION)(request)
    return bool(settings.DISABLED_REGISTRATION)


def get_email_dynamic_validator():
    if isinstance(settings.EMAIL_DYNAMIC_VALIDATOR, six.string_types):
        return import_string(settings.EMAIL_DYNAMIC_VALIDATOR)
    return None


def get_login_throttle():
    if isinstance(settings.LOGIN_THROTTLE, six.string_types):
        return import_string(settings.LOGIN_THROTTLE)
    return None


def get_password_reset_throttle():
    if isinstance(settings.PASSWORD_RESET_THROTTLE, six.string_types):
        return import_string(settings.PASSWORD_RESET_THROTTLE)
    return None


def get_picture_storage(request, account=None, **kwargs):
    if settings.PICTURE_STORAGE_CALLABLE:
        try:
            return import_string(settings.PICTURE_STORAGE_CALLABLE)(
                request, account=account, **kwargs)
        except ImportError:
            pass
    return default_storage
