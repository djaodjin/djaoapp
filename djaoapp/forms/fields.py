# Copyright (c) 2018, DjaoDjin inc.
# see LICENSE

from __future__ import unicode_literals

import logging

import phonenumbers
from django.core.exceptions import ValidationError
from django.forms import fields
from django.utils.translation import ugettext_lazy as _

LOGGER = logging.getLogger(__name__)


class PhoneNumberField(fields.CharField):
    default_error_messages = {
        'invalid': _("Enter a valid phone number. If you still get an error,"\
" please try to enter it as an international phone number (start by typing +,"\
" then the country code, then the number. Ex: +14155145544)"),
    }

    def to_python(self, value):
        """
        Returns a formatted phone number as a string.
        """
        if self.required:
            try:
                phone_number = phonenumbers.parse(value, None)
            except phonenumbers.NumberParseException as err:
                LOGGER.info("tel %s:%s", value, err)
                phone_number = None
            if not phone_number:
                try:
                    phone_number = phonenumbers.parse(value, "US")
                except phonenumbers.NumberParseException:
                    raise ValidationError(self.error_messages['invalid'])
            if phone_number and not phonenumbers.is_valid_number(phone_number):
                raise ValidationError(self.error_messages['invalid'])
            return phonenumbers.format_number(
                phone_number, phonenumbers.PhoneNumberFormat.E164)
        return None
