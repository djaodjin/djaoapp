# Copyright (c) 2021, DjaoDjin inc.
# see LICENSE

"""
Validators
"""
from __future__ import unicode_literals

from django.conf import settings

from .compat import import_string, six


def validate_contact_form(full_name, email, message):
    if isinstance(settings.CONTACT_DYNAMIC_VALIDATOR, six.string_types):
        validate_func = import_string(settings.CONTACT_DYNAMIC_VALIDATOR)
        validate_func(full_name, email, message)
