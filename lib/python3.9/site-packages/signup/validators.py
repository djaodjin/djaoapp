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

from django.utils.deconstruct import deconstructible
from django.core.exceptions import ValidationError
from django.core.validators import validate_email, validate_slug
from django.utils.translation import gettext_lazy as _
from phonenumber_field import phonenumber
#pylint:disable=unused-import
from django.core.validators import (EmailValidator as EmailValidatorBase,
    RegexValidator)

from .utils import get_email_dynamic_validator


@deconstructible
class EmailValidator(EmailValidatorBase):

    dynamic_validator = get_email_dynamic_validator()

    def __call__(self, value):
        super(EmailValidator, self).__call__(value)
        if self.dynamic_validator:
            self.dynamic_validator(value)


@deconstructible
class PhoneValidator:
    message = _('Enter a valid phone number.')
    code = 'invalid'

    def __init__(self, message=None, code=None):
        if message is not None:
            self.message = message
        if code is not None:
            self.code = code

    def __call__(self, value, region=None):
        phone = phonenumber.to_python(value, region)
        if phone and not phone.is_valid():
            phone = phonenumber.to_python(value, region='US')
        if phone and not phone.is_valid():
            raise ValidationError(
                _("The phone number entered is not valid."),
                code="invalid_phone_number")
        return phone

    def __eq__(self, other):
        return (
            isinstance(other, PhoneValidator) and
            (self.message == other.message) and
            (self.code == other.code))


validate_phone = PhoneValidator() #pylint:disable=invalid-name


def validate_email_or_phone(value):
    try:
        validate_email(value)
    except ValidationError:
        try:
            validate_phone(value)
        except ValidationError:
            raise ValidationError(_('Enter a valid email or phone number.'),
                code='invalid')


def validate_username_or_email_or_phone(value): #pylint:disable=invalid-name
    try:
        validate_slug(value)
    except ValidationError:
        try:
            validate_email_or_phone(value)
        except ValidationError:
            raise ValidationError(
                _('Enter a valid username, email or phone number.'),
                code='invalid')


def as_email_or_phone(value):
    try:
        validate_email(value)
        return value, None
    except ValidationError:
        try:
            validate_phone(value)
            return None, value
        except ValidationError:
            pass
    return None, None
