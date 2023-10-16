# Copyright (c) 2023, DjaoDjin inc.
# see LICENSE
from __future__ import unicode_literals

from django.conf import settings

from .compat import import_string, six

def enables_processor_test_keys(request=None):
    if isinstance(settings.ENABLES_PROCESSOR_TEST_KEYS, six.string_types):
        return import_string(settings.ENABLES_PROCESSOR_TEST_KEYS)(request)
    return bool(settings.ENABLES_PROCESSOR_TEST_KEYS)


def get_registration_captcha_keys(request=None):
    if isinstance(settings.REGISTRATION_CAPTCHA_KEYS, six.string_types):
        return import_string(settings.REGISTRATION_CAPTCHA_KEYS)(request)
    if settings.RECAPTCHA_PUBLIC_KEY and settings.RECAPTCHA_PRIVATE_KEY:
        return {'public_key': settings.RECAPTCHA_PUBLIC_KEY,
            'private_key': settings.RECAPTCHA_PRIVATE_KEY}
    return {}


def get_contact_captcha_keys(request=None):
    if isinstance(settings.CONTACT_CAPTCHA_KEYS, six.string_types):
        return import_string(settings.CONTACT_CAPTCHA_KEYS)(request)
    if settings.RECAPTCHA_PUBLIC_KEY and settings.RECAPTCHA_PRIVATE_KEY:
        return {'public_key': settings.RECAPTCHA_PUBLIC_KEY,
            'private_key': settings.RECAPTCHA_PRIVATE_KEY}
    return {}
