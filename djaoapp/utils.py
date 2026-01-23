# Copyright (c) 2026, DjaoDjin inc.
# see LICENSE
from __future__ import unicode_literals

import datetime, logging

from django.conf import settings
from django.core.mail import get_connection as get_connection_base
from rules.models import Rule
from rules.utils import get_current_app
from saas.decorators import _valid_manager
from saas.models import get_broker

from .compat import import_string, reverse
from .thread_locals import build_absolute_uri

LOGGER = logging.getLogger(__name__)


AUTH_ENABLED = 0
AUTH_LOGIN_ONLY = 1
AUTH_DISABLED = 2

USER_REGISTRATION = 0
PERSONAL_REGISTRATION = 1
IMPLICIT_REGISTRATION = 3


def get_registration_captcha_keys(request=None):
    """
    The function returns a dictionnary
    `{'public_key': _*****_, 'private_key': _*****_ }`
    with the pair of keys to call the reCAPTACH API with, or an empty
    dictionnary if captcha should be disabled on the registration page.
    """
    if getattr(settings, 'REGISTRATION_REQUIRES_RECAPTCHA', False):
        #pylint:disable=protected-access
        if not hasattr(get_registration_captcha_keys, '_recaptcha_public_key'):
            try:
                get_registration_captcha_keys._recaptcha_public_key = \
                    import_string(settings.RECAPTCHA_PUBLIC_KEY)
            except ImportError:
                get_registration_captcha_keys._recaptcha_public_key = None
        if callable(get_registration_captcha_keys._recaptcha_public_key):
            recaptcha_public_key = \
                get_registration_captcha_keys._recaptcha_public_key()
        else:
            recaptcha_public_key = settings.RECAPTCHA_PUBLIC_KEY

        if not hasattr(get_registration_captcha_keys, '_recaptcha_private_key'):
            try:
                get_registration_captcha_keys._recaptcha_private_key = \
                    import_string(settings.RECAPTCHA_PRIVATE_KEY)
            except ImportError:
                get_registration_captcha_keys._recaptcha_private_key = None
        if callable(get_registration_captcha_keys._recaptcha_private_key):
            recaptcha_private_key = \
                get_registration_captcha_keys._recaptcha_private_key()
        else:
            recaptcha_private_key = settings.RECAPTCHA_PRIVATE_KEY

        if recaptcha_public_key and recaptcha_private_key:
            return {
                'public_key': recaptcha_public_key,
                'private_key': recaptcha_private_key}
    return {}


def get_contact_captcha_keys(request=None):
    """
    The function returns a dictionnary
    `{'public_key': _*****_, 'private_key': _*****_ }`
    with the pair of keys to call the reCAPTACH API with, or an empty
    dictionnary if captcha should be disabled on the contact-us page.
    """
    if getattr(settings, 'CONTACT_REQUIRES_RECAPTCHA', False):
        #pylint:disable=protected-access
        if not hasattr(get_contact_captcha_keys, '_recaptcha_public_key'):
            try:
                get_contact_captcha_keys._recaptcha_public_key = \
                    import_string(settings.RECAPTCHA_PUBLIC_KEY)
            except ImportError:
                get_contact_captcha_keys._recaptcha_public_key = None
        if callable(get_contact_captcha_keys._recaptcha_public_key):
            recaptcha_public_key = \
                get_contact_captcha_keys._recaptcha_public_key()
        else:
            recaptcha_public_key = settings.RECAPTCHA_PUBLIC_KEY

        if not hasattr(get_contact_captcha_keys, '_recaptcha_private_key'):
            try:
                get_contact_captcha_keys._recaptcha_private_key = \
                    import_string(settings.RECAPTCHA_PRIVATE_KEY)
            except ImportError:
                get_contact_captcha_keys._recaptcha_private_key = None
        if callable(get_contact_captcha_keys._recaptcha_private_key):
            recaptcha_private_key = \
                get_contact_captcha_keys._recaptcha_private_key()
        else:
            recaptcha_private_key = settings.RECAPTCHA_PRIVATE_KEY

        if recaptcha_public_key and recaptcha_private_key:
            return {
                'public_key': recaptcha_public_key,
                'private_key': recaptcha_private_key}
    return {}


def get_email_connection(site=None):
    """
    Returns a connection to the e-mail server for the site.
    """
    if settings.EMAIL_CONNECTION_CALLABLE:
        return import_string(settings.EMAIL_CONNECTION_CALLABLE)(site)

    return get_connection_base(fail_silently=True)


def get_notified_on_errors(site=None):
    """
    We are emailing the owner of the site here so we want
    to access the information at the hosting provider.
    """
    if settings.NOTIFIED_ON_ERRORS_CALLABLE:
        return import_string(settings.NOTIFIED_ON_ERRORS_CALLABLE)(site)

    return settings.ADMINS

# Authentication workflow
# -----------------------
def get_disabled_authentication(request, user):
    """
    Used to override SIGNUP['DISABLED_AUTHENTICATION']
    """
    return (settings.AUTHENTICATION_OVERRIDE == AUTH_DISABLED
        and not _valid_manager(user, [get_broker()]))


def get_disabled_registration(request):#pylint:disable=unused-argument
    """
    Used to override SIGNUP['DISABLED_REGISTRATION']
    """
    return settings.AUTHENTICATION_OVERRIDE != AUTH_ENABLED


def get_force_personal_profile(request):
    return settings.REGISTRATION_STYLE in (
        PERSONAL_REGISTRATION, IMPLICIT_REGISTRATION)


def get_user_api_key_lifetime(request, user):
    # XXX return based on profile.
    return datetime.timedelta(days=365)

def get_user_otp_required(request, user):
    return user.role.filter(
        role_description__otp_required=True).exists()


def product_url(subscriber=None, plan=None, request=None):
    """
    Used to override SAAS['PRODUCT_URL_CALLABLE']
    """
    location = None
    if plan:
        candidate_rule = Rule.objects.filter(
            app=get_current_app(request),
            kwargs__contains=str(plan)).order_by('-rank').first()
        if candidate_rule:
            location = candidate_rule.path.replace(
                '{profile}', str(subscriber)).replace(
                '{plan}',  str(plan))
    if not location:
        location = reverse('product_default_start')
        if subscriber:
            location += '%s/' % subscriber
        if plan:
            location += '%s/' % plan

    return build_absolute_uri(location=location, request=request)
