# Copyright (c) 2025, DjaoDjin inc.
# see LICENSE
#pylint:disable=invalid-name,too-many-lines
import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in, user_login_failed
from django.db.models.signals import post_save
from django.dispatch import receiver
from rules.signals import user_welcome
from saas import settings as saas_settings
from saas.models import CartItem, get_broker
from saas.signals import (card_expires_soon, charge_updated,
    claim_code_generated, card_updated, expires_soon, order_executed,
    profile_updated, processor_setup_error, quota_reached,
    renewal_charge_failed, role_grant_created, role_request_created,
    role_grant_accepted, subscription_grant_accepted,
    subscription_grant_created, subscription_request_accepted,
    subscription_request_created, period_sales_report_created,
    use_charge_limit_crossed)
from signup.helpers import has_invalid_password
from signup.models import Contact
from signup.signals import user_registered, user_activated
from signup.utils import printable_name as user_printable_name
from djaoapp.signals import user_contact

from ..compat import gettext_lazy as _, reverse, six
from ..thread_locals import build_absolute_uri
from .serializers import (ContactUsNotificationSerializer,
    UserNotificationSerializer,
    ExpireProfileNotificationSerializer,
    SubscriptionExpireNotificationSerializer,
    ChangeProfileNotificationSerializer, AggregatedSalesNotificationSerializer,
    ChargeNotificationSerializer,
    RenewalFailedNotificationSerializer, InvoiceNotificationSerializer,
    ClaimNotificationSerializer, ProcessorSetupNotificationSerializer,
    RoleRequestNotificationSerializer, RoleGrantNotificationSerializer,
    SubscriptionAcceptedNotificationSerializer,
    SubscriptionCreatedNotificationSerializer, UseChargeLimitReachedSerializer)
from . import send_notification

#pylint: disable=unused-argument
#pylint: disable=protected-access

LOGGER = logging.getLogger(__name__)


def get_user_context_deprecated(user, site=None):
    context = {
        'username': user.username,
        'email': user.email,
        'first_name': user.first_name,
        'printable_name': user_printable_name(user)
    }
    if site:
        context.update({'location': site.as_absolute_uri(
            reverse('users_profile', args=(user,)))})
    return context


# We insure the method is only bounded once no matter how many times
# this module is loaded by using a dispatch_uid as advised here:
#   https://docs.djangoproject.com/en/dev/topics/signals/
@receiver(quota_reached,
          dispatch_uid="quota_reached_notice")
def quota_reached_notice(sender, usage, use_charge, subscription,
                         **kwargs): # no request in kwargs
    """
    Quota reached

    This notification is sent when a profile has passed the free quota
    allocated per billing period for use charges.

    **Tags: notification

    **Example

    .. code-block:: json

        {
          "event": "quota_reached",
          "broker": {
            "slug": "djaoapp",
            "printable_name": "DjaoApp",
            "full_name": "DjaoApp inc.",
            "nick_name": "DjaoApp",
            "picture": null,
            "type": "organization",
            "credentials": false,
            "created_at": "2024-01-01T00:00:00Z",
            "email": "djaoapp@localhost.localdomain",
            "phone": "415-555-5555",
            "street_address": "1 SaaS Road",
            "locality": "San Francisco",
            "region": "California",
            "postal_code": "94133",
            "country": "US",
            "default_timezone": "America/Los_Angeles",
            "is_provider": true,
            "is_bulk_buyer": false,
            "lang": "en",
            "extra": null
          },
          "back_url": "{{api_base_url}}",
          "profile": {
            "slug": "xia",
            "printable_name": "Xia",
            "full_name": "Xia Lee",
            "nick_name": "Xia",
            "picture": null,
            "type": "personal",
            "credentials": true,
            "created_at": "2024-01-01T00:00:00Z",
            "email": "xia@localhost.localdomain",
            "phone": "415-555-5556",
            "street_address": "1 SaaS Road",
            "locality": "San Francisco",
            "region": "California",
            "postal_code": "94133",
            "country": "US",
            "default_timezone": "America/Los_Angeles",
            "is_provider": false,
            "is_bulk_buyer": false,
            "lang": "en",
            "extra": null
          },
          "plan": {
            "slug": "premium",
            "title": "Premium"
          },
          "use_charge": {
            "slug": "http-requests",
            "title": "Number of HTTP requests",
            "description": "",
            "created_at": "2024-01-01T00:00:00Z",
            "use_amount": 1,
            "quota": 100000,
            "maximum_limit": 1000000,
            "extra": null
          },
          "usage": 100010
        }
    """
    LOGGER.debug("[signal] quota_reached_notice(usage=%d, "\
        "use_charge=%s, subscription=%s)", usage, use_charge, subscription)

    broker = get_broker()
    back_url = build_absolute_uri() # saas/models.py
    context = {
        'broker': broker,
        'back_url': back_url,
        'profile': subscription.organization,
        'plan': subscription.plan,
        'provider': subscription.plan.organization,
        'use_charge': use_charge,
        'usage': usage,
    }
    send_notification('quota_reached',
        context=UseChargeLimitReachedSerializer().to_representation(context),
        **kwargs)


# We insure the method is only bounded once no matter how many times
# this module is loaded by using a dispatch_uid as advised here:
#   https://docs.djangoproject.com/en/dev/topics/signals/
@receiver(use_charge_limit_crossed,
          dispatch_uid="use_charge_limit_crossed_notice")
def use_charge_limit_crossed_notice(sender, usage, use_charge, subscription,
                                    **kwargs): # no request in kwargs
    """
    Use charge limit crossed

    This notification is sent when a profile has passed the maximum limit
    to bill within a period for use charges.

    **Tags: notification

    **Example

    .. code-block:: json

        {
          "event": "use_charge_limit_crossed",
          "broker": {
            "slug": "djaoapp",
            "printable_name": "DjaoApp",
            "full_name": "DjaoApp inc.",
            "nick_name": "DjaoApp",
            "picture": null,
            "type": "organization",
            "credentials": false,
            "created_at": "2024-01-01T00:00:00Z",
            "email": "djaoapp@localhost.localdomain",
            "phone": "415-555-5555",
            "street_address": "1 SaaS Road",
            "locality": "San Francisco",
            "region": "California",
            "postal_code": "94133",
            "country": "US",
            "default_timezone": "America/Los_Angeles",
            "is_provider": true,
            "is_bulk_buyer": false,
            "lang": "en",
            "extra": null
          },
          "back_url": "{{api_base_url}}",
          "profile": {
            "slug": "xia",
            "printable_name": "Xia",
            "full_name": "Xia Lee",
            "nick_name": "Xia",
            "picture": null,
            "type": "personal",
            "credentials": true,
            "created_at": "2024-01-01T00:00:00Z",
            "email": "xia@localhost.localdomain",
            "phone": "415-555-5556",
            "street_address": "1 SaaS Road",
            "locality": "San Francisco",
            "region": "California",
            "postal_code": "94133",
            "country": "US",
            "default_timezone": "America/Los_Angeles",
            "is_provider": false,
            "is_bulk_buyer": false,
            "lang": "en",
            "extra": null
          },
          "plan": {
            "slug": "premium",
            "title": "Premium"
          },
          "use_charge": {
            "slug": "http-requests",
            "title": "Number of HTTP requests",
            "description": "",
            "created_at": "2024-01-01T00:00:00Z",
            "use_amount": 1,
            "quota": 100000,
            "maximum_limit": 1000000,
            "extra": null
          },
          "usage": 1000008
        }
    """
    LOGGER.debug("[signal] use_charge_limit_crossed_notice(usage=%d, "\
        "use_charge=%s, subscription=%s)", usage, use_charge, subscription)

    broker = get_broker()
    back_url = build_absolute_uri() # saas/models.py
    context = {
        'broker': broker,
        'back_url': back_url,
        'profile': subscription.organization,
        'plan': subscription.plan,
        'provider': subscription.plan.organization,
        'use_charge': use_charge,
        'usage': usage,
    }
    send_notification('use_charge_limit_crossed',
        context=UseChargeLimitReachedSerializer().to_representation(context),
        **kwargs)


# We insure the method is only bounded once no matter how many times
# this module is loaded by using a dispatch_uid as advised here:
#   https://docs.djangoproject.com/en/dev/topics/signals/
@receiver(user_contact, dispatch_uid="user_contact_notice")
def user_contact_notice(sender, provider, user, reason,
                        **kwargs): # request in kwargs
    """
    Contact us

    Someone requested information through the contact form.

    **Tags: notification

    **Example

    .. code-block:: json

        {
          "event": "user_contact",
          "broker": {
            "slug": "djaoapp",
            "printable_name": "DjaoApp",
            "full_name": "DjaoApp inc.",
            "nick_name": "DjaoApp",
            "picture": null,
            "type": "organization",
            "credentials": false,
            "created_at": "2024-01-01T00:00:00Z",
            "email": "djaoapp@localhost.localdomain",
            "phone": "415-555-5555",
            "street_address": "1 SaaS Road",
            "locality": "San Francisco",
            "region": "California",
            "postal_code": "94133",
            "country": "US",
            "default_timezone": "America/Los_Angeles",
            "is_provider": true,
            "is_bulk_buyer": false,
            "lang": "en",
            "extra": null
          },
          "back_url": "{{api_base_url}}",
          "originated_by": {
            "slug": "xia",
            "username": "xia",
            "printable_name": "Xia",
            "full_name": "Xia Lee",
            "nick_name": "Xia",
            "picture": null,
            "type": "personal",
            "credentials": true,
            "created_at": "2024-01-01T00:00:00Z",
            "last_login": "2024-01-01T00:00:00Z",
            "email": "xia@localhost.localdomain",
            "phone": "415-555-5556",
            "lang": "en",
            "extra": null
          },
          "detail": [["Message", "Please help!"]]
        }
    """
    broker = get_broker()
    if provider is None:
        provider = broker
    LOGGER.debug("[signal] user_contact_notice(provider=%s, user=%s)",
        provider, user)
    back_url = build_absolute_uri(       # djaoapp/api/contact.py,
        request=kwargs.get('request'))   # djaoapp/views/contact.py
    context = {
        'broker': broker,
        'back_url': back_url,
        'provider': provider,
        'originated_by': user,
        'detail': reason
    }
    send_notification('user_contact',
        context=ContactUsNotificationSerializer().to_representation(context),
        **kwargs)


# We insure the method is only bounded once no matter how many times
# this module is loaded by using a dispatch_uid as advised here:
#   https://docs.djangoproject.com/en/dev/topics/signals/
@receiver(user_logged_in, dispatch_uid="user_logged_in_notice")
def user_logged_in_notice(sender, request, user, **kwargs):
    """
    User logged in

    This notification is sent when a user logged in successfully.

    **Tags: notification

    **Example

    .. code-block:: json

        {
          "event": "user_logged_in",
          "broker": {
            "slug": "djaoapp",
            "printable_name": "DjaoApp",
            "full_name": "DjaoApp inc.",
            "nick_name": "DjaoApp",
            "picture": null,
            "type": "organization",
            "credentials": false,
            "created_at": "2024-01-01T00:00:00Z",
            "email": "djaoapp@localhost.localdomain",
            "phone": "415-555-5555",
            "street_address": "1 SaaS Road",
            "locality": "San Francisco",
            "region": "California",
            "postal_code": "94133",
            "country": "US",
            "default_timezone": "America/Los_Angeles",
            "is_provider": true,
            "is_bulk_buyer": false,
            "lang": "en",
            "extra": null
          },
          "back_url": "{{api_base_url}}",
          "user": {
            "slug": "xia",
            "username": "xia",
            "printable_name": "Xia",
            "full_name": "Xia Lee",
            "nick_name": "Xia",
            "picture": null,
            "type": "personal",
            "credentials": true,
            "created_at": "2024-01-01T00:00:00Z",
            "last_login": "2024-01-01T00:00:00Z",
            "email": "xia@localhost.localdomain",
            "phone": "415-555-5556",
            "lang": "en",
            "extra": null
          }
        }
    """
    LOGGER.debug("[signal] user_logged_in_notice(user=%s)", user)

    broker = get_broker()
    back_url = build_absolute_uri(request=kwargs.get('request')) # XXX not sent?
    context = {
        'broker': broker,
        'back_url': back_url,
        'user': user
    }
    #send_notification('user_logged_in',
    #    context=UserNotificationSerializer().to_representation(context),
    #    **kwargs)


# We insure the method is only bounded once no matter how many times
# this module is loaded by using a dispatch_uid as advised here:
#   https://docs.djangoproject.com/en/dev/topics/signals/
@receiver(user_login_failed, dispatch_uid="user_login_failed_notice")
def user_login_failed_notice(sender, credentials, request, **kwargs):
    """
    User login failed

    This notification is sent when a user login attempts has failed.

    **Tags: notification

    **Example

    .. code-block:: json

        {
          "event": "user_login_failed",
          "broker": {
            "slug": "djaoapp",
            "printable_name": "DjaoApp",
            "full_name": "DjaoApp inc.",
            "nick_name": "DjaoApp",
            "picture": null,
            "type": "organization",
            "credentials": false,
            "created_at": "2024-01-01T00:00:00Z",
            "email": "djaoapp@localhost.localdomain",
            "phone": "415-555-5555",
            "street_address": "1 SaaS Road",
            "locality": "San Francisco",
            "region": "California",
            "postal_code": "94133",
            "country": "US",
            "default_timezone": "America/Los_Angeles",
            "is_provider": true,
            "is_bulk_buyer": false,
            "lang": "en",
            "extra": null
          },
          "back_url": "{{api_base_url}}/recover/",
          "user": {
            "slug": "xia",
            "username": "xia",
            "printable_name": "Xia",
            "full_name": "Xia Lee",
            "nick_name": "Xia",
            "picture": null,
            "type": "personal",
            "credentials": true,
            "created_at": "2024-01-01T00:00:00Z",
            "last_login": "2024-01-01T00:00:00Z",
            "email": "xia@localhost.localdomain",
            "phone": "415-555-5556",
            "lang": "en",
            "extra": null
          }
        }
    """
    LOGGER.debug("[signal] user_login_failed_notice(credentials=%s)",
        credentials)
    try:
        model = get_user_model()
        user = model.objects.find_user(credentials.get('username'))

        broker = get_broker()
        back_url = build_absolute_uri( # XXX not sent?
            location=reverse('password_reset'))
        context = {
            'broker': broker,
            'back_url': back_url,
            'user': user
        }
        #send_notification('user_login_failed',
        #    context=UserNotificationSerializer().to_representation(context),
        #    **kwargs)
    except model.DoesNotExist:
        pass


# We insure the method is only bounded once no matter how many times
# this module is loaded by using a dispatch_uid as advised here:
#   https://docs.djangoproject.com/en/dev/topics/signals/
@receiver(user_registered, dispatch_uid="user_registered_notice")
def user_registered_notice(sender, user, **kwargs): # request in **kwargs
    """
    User registered

    This notification is sent when a user has registered.

    **Tags: notification

    **Example

    .. code-block:: json

        {
          "event": "user_registered",
          "broker": {
            "slug": "djaoapp",
            "printable_name": "DjaoApp",
            "full_name": "DjaoApp inc.",
            "nick_name": "DjaoApp",
            "picture": null,
            "type": "organization",
            "credentials": false,
            "created_at": "2024-01-01T00:00:00Z",
            "email": "djaoapp@localhost.localdomain",
            "phone": "415-555-5555",
            "street_address": "1 SaaS Road",
            "locality": "San Francisco",
            "region": "California",
            "postal_code": "94133",
            "country": "US",
            "default_timezone": "America/Los_Angeles",
            "is_provider": true,
            "is_bulk_buyer": false,
            "lang": "en",
            "extra": null
          },
          "back_url": "{{api_base_url}}",
          "user": {
            "slug": "xia",
            "username": "xia",
            "printable_name": "Xia",
            "full_name": "Xia Lee",
            "nick_name": "Xia",
            "picture": null,
            "type": "personal",
            "credentials": true,
            "created_at": "2024-01-01T00:00:00Z",
            "last_login": "2024-01-01T00:00:00Z",
            "email": "xia@localhost.localdomain",
            "phone": "415-555-5556",
            "lang": "en",
            "extra": null
          }
        }
    """
    LOGGER.debug("[signal] user_registered_notice(user=%s)", user)
    back_url = build_absolute_uri( # signup/mixins.py
        request=kwargs.get('request'))
    context = {
        'broker': get_broker(),
        'back_url': back_url,
        'user': user
    }
    send_notification('user_registered',
        context=UserNotificationSerializer().to_representation(context),
        **kwargs)


# We insure the method is only bounded once no matter how many times
# this module is loaded by using a dispatch_uid as advised here:
#   https://docs.djangoproject.com/en/dev/topics/signals/
@receiver(user_welcome, dispatch_uid="user_welcome_notice")
def user_welcome_notice(sender, user, **kwargs): # request in **kwargs
    """
    User welcome

    This notification is sent when a user visits an app URL for the first time.

    **Tags: notification

    **Example

    .. code-block:: json

        {
          "event": "user_welcome_email",
          "broker": {
            "slug": "djaoapp",
            "printable_name": "DjaoApp",
            "full_name": "DjaoApp inc.",
            "nick_name": "DjaoApp",
            "picture": null,
            "type": "organization",
            "credentials": false,
            "created_at": "2024-01-01T00:00:00Z",
            "email": "djaoapp@localhost.localdomain",
            "phone": "415-555-5555",
            "street_address": "1 SaaS Road",
            "locality": "San Francisco",
            "region": "California",
            "postal_code": "94133",
            "country": "US",
            "default_timezone": "America/Los_Angeles",
            "is_provider": true,
            "is_bulk_buyer": false,
            "lang": "en",
            "extra": null
          },
          "back_url": "{{api_base_url}}",
          "user": {
            "slug": "xia",
            "username": "xia",
            "printable_name": "Xia",
            "full_name": "Xia Lee",
            "nick_name": "Xia",
            "picture": null,
            "type": "personal",
            "credentials": true,
            "created_at": "2024-01-01T00:00:00Z",
            "last_login": "2024-01-01T00:00:00Z",
            "email": "xia@localhost.localdomain",
            "phone": "415-555-5556",
            "lang": "en",
            "extra": null
          }
        }
    """
    LOGGER.debug("[signal] user_welcome(user=%s)", user)
    back_url = build_absolute_uri( # XXX not sent
        request=kwargs.get('request'))
    context = {
        'broker': get_broker(),
        'back_url': back_url,
        'user': user
    }
    send_notification('user_welcome',
        context=UserNotificationSerializer().to_representation(context),
        **kwargs)


# We insure the method is only bounded once no matter how many times
# this module is loaded by using a dispatch_uid as advised here:
#   https://docs.djangoproject.com/en/dev/topics/signals/
@receiver(user_activated, dispatch_uid="user_activated_notice")
def user_activated_notice(sender, user, **kwargs): # request in **kwargs
    """
    User activated

    This notification is sent when a user has activated his/her account.

    **Tags: notification

    **Example

    .. code-block:: json

        {
          "event": "user_activated",
          "broker": {
            "slug": "djaoapp",
            "printable_name": "DjaoApp",
            "full_name": "DjaoApp inc.",
            "nick_name": "DjaoApp",
            "picture": null,
            "type": "organization",
            "credentials": false,
            "created_at": "2024-01-01T00:00:00Z",
            "email": "djaoapp@localhost.localdomain",
            "phone": "415-555-5555",
            "street_address": "1 SaaS Road",
            "locality": "San Francisco",
            "region": "California",
            "postal_code": "94133",
            "country": "US",
            "default_timezone": "America/Los_Angeles",
            "is_provider": true,
            "is_bulk_buyer": false,
            "lang": "en",
            "extra": null
          },
          "back_url": "{{api_base_url}}",
          "user": {
            "slug": "xia",
            "username": "xia",
            "printable_name": "Xia",
            "full_name": "Xia Lee",
            "nick_name": "Xia",
            "picture": null,
            "type": "personal",
            "credentials": true,
            "created_at": "2024-01-01T00:00:00Z",
            "last_login": "2024-01-01T00:00:00Z",
            "email": "xia@localhost.localdomain",
            "phone": "415-555-5556",
            "lang": "en",
            "extra": null
          }
        }
    """
    LOGGER.debug("[signal] user_activated_notice(user=%s)", user)
    back_url = build_absolute_uri(     # signup/mixins.py
        request=kwargs.get('request'))
    context = {
        'broker': get_broker(),
        'back_url': back_url,
        'user': user,
    }
    send_notification('user_activated',
        context=UserNotificationSerializer().to_representation(context),
        **kwargs)


def get_charge_updated_context(charge, site=None):
    # used in `PrintableChargeReceiptView.get_context_data`
    back_url = build_absolute_uri(location=reverse('saas_charge_receipt', args=(
        charge.customer, charge)))
    context = {
        'broker': get_broker(),
        'back_url': back_url,
        'created_by': charge.created_by,
        'profile': charge.customer,
        'charge': charge,
        'charge_items': [{
            'invoiced': item.invoiced,
            'refunded': item.refunded,
            } for item in charge.line_items],
        'provider': charge.provider,
        'originated_by': charge.created_by,
    }
    if charge.refunded.exists():
        total_refunded = charge.invoiced_total_after_refund
        context.update({
            'charge_total': {
                'amount': total_refunded.amount,
                'unit': total_refunded.unit
            }})
    return context


# We insure the method is only bounded once no matter how many times
# this module is loaded by using a dispatch_uid as advised here:
#   https://docs.djangoproject.com/en/dev/topics/signals/
@receiver(charge_updated, dispatch_uid="charge_updated_notice")
def charge_updated_notice(sender, charge, user, **kwargs):
    """
    Charge receipt

    This notification is sent when a charge is created on a credit card.
    It is also sent when the charge is refunded.

    **Tags: notification

    **Example

    .. code-block:: json

        {
          "event": "charge_updated",
          "broker": {
            "slug": "djaoapp",
            "printable_name": "DjaoApp",
            "full_name": "DjaoApp inc.",
            "nick_name": "DjaoApp",
            "picture": null,
            "type": "organization",
            "credentials": false,
            "created_at": "2024-01-01T00:00:00Z",
            "email": "djaoapp@localhost.localdomain",
            "phone": "415-555-5555",
            "street_address": "1 SaaS Road",
            "locality": "San Francisco",
            "region": "California",
            "postal_code": "94133",
            "country": "US",
            "default_timezone": "America/Los_Angeles",
            "is_provider": true,
            "is_bulk_buyer": false,
            "lang": "en",
            "extra": null
          },
          "back_url": "{{api_base_url}}",
          "profile": {
            "slug": "xia",
            "printable_name": "Xia",
            "full_name": "Xia Lee",
            "nick_name": "Xia",
            "picture": null,
            "type": "personal",
            "credentials": true,
            "created_at": "2024-01-01T00:00:00Z",
            "email": "xia@localhost.localdomain",
            "phone": "415-555-5556",
            "street_address": "1 SaaS Road",
            "locality": "San Francisco",
            "region": "California",
            "postal_code": "94133",
            "country": "US",
            "default_timezone": "America/Los_Angeles",
            "is_provider": false,
            "is_bulk_buyer": false,
            "lang": "en",
            "extra": null
          },
          "originated_by": {
            "slug": "xia",
            "username": "xia",
            "printable_name": "Xia",
            "full_name": "Xia Lee",
            "nick_name": "Xia",
            "picture": null,
            "type": "personal",
            "credentials": true,
            "created_at": "2024-01-01T00:00:00Z",
            "last_login": "2024-01-01T00:00:00Z",
            "email": "xia@localhost.localdomain",
            "phone": "415-555-5556",
            "lang": "en",
            "extra": null
          },
          "charge_items": [{
            "invoiced": {
              "created_at": "2024-01-01T00:00:00Z",
              "description": "Subscription to premium until 2025/12/31 (12 months)",
              "amount": 11900,
              "is_debit": false,
              "orig_account": "Receivable",
              "orig_profile": {
                  "slug": "djaoapp",
                  "printable_name": "DjaoApp",
                  "picture": null,
                  "type": "organization",
                  "credentials": false
              },
              "orig_amount": 11900,
              "orig_unit": "usd",
              "dest_account": "Payable",
              "dest_profile": {
                  "slug": "xia",
                  "printable_name": "Xia",
                  "picture": null,
                  "type": "personal",
                  "credentials": true
              },
              "dest_amount": 11900,
              "dest_unit": "usd"
            },
            "refunded": []
          }],
          "charge": {
            "created_at": "2024-01-01T00:00:00Z",
            "amount": 11900,
            "unit": "usd",
            "readable_amount": "$119.00",
            "description": "Subscription to premium until 2025/12/31 (12 months)",
            "last4": "4242",
            "exp_date": "07/2023",
            "processor_key": "ch_abc123",
            "state": "done"
          },
          "provider": {
            "slug": "djaoapp",
            "printable_name": "DjaoApp",
            "full_name": "DjaoApp inc.",
            "nick_name": "DjaoApp",
            "picture": null,
            "type": "organization",
            "credentials": false,
            "created_at": "2024-01-01T00:00:00Z",
            "email": "djaoapp@localhost.localdomain",
            "phone": "415-555-5555",
            "street_address": "1 SaaS Road",
            "locality": "San Francisco",
            "region": "California",
            "postal_code": "94133",
            "country": "US",
            "default_timezone": "America/Los_Angeles",
            "is_provider": true,
            "is_bulk_buyer": false,
            "lang": "en",
            "extra": null
          }
        }
    """
    if charge.is_paid:
        LOGGER.debug("[signal] charge_updated_notice(charge=%s, user=%s)",
            charge, user)
        context = get_charge_updated_context(charge) # saas/models.py
                                                     # saas/api/charges.py
        if user and charge.created_by != user:
            context.update({'originated_by': user})
        else:
            context.update({'originated_by': None})
        send_notification('charge_updated',
            context=ChargeNotificationSerializer().to_representation(context),
            **kwargs)


@receiver(card_updated, dispatch_uid="card_updated_notice")
def card_updated_notice(sender, organization, user, old_card, new_card,
                        **kwargs): # no request in kwargs
    """
    Card updated

    This notification is sent when a credit card on file is updated.

    **Tags: notification

    **Example

    .. code-block:: json

        {
          "event": "card_updated",
          "broker": {
            "slug": "djaoapp",
            "printable_name": "DjaoApp",
            "full_name": "DjaoApp inc.",
            "nick_name": "DjaoApp",
            "picture": null,
            "type": "organization",
            "credentials": false,
            "created_at": "2024-01-01T00:00:00Z",
            "email": "djaoapp@localhost.localdomain",
            "phone": "415-555-5555",
            "street_address": "1 SaaS Road",
            "locality": "San Francisco",
            "region": "California",
            "postal_code": "94133",
            "country": "US",
            "default_timezone": "America/Los_Angeles",
            "is_provider": true,
            "is_bulk_buyer": false,
            "lang": "en",
            "extra": null
          },
          "back_url": "{{api_base_url}}",
          "originated_by": {
            "slug": "xia",
            "username": "xia",
            "printable_name": "Xia",
            "full_name": "Xia Lee",
            "nick_name": "Xia",
            "picture": null,
            "type": "personal",
            "credentials": true,
            "created_at": "2024-01-01T00:00:00Z",
            "last_login": "2024-01-01T00:00:00Z",
            "email": "xia@localhost.localdomain",
            "phone": "415-555-5556",
            "lang": "en",
            "extra": null
          },
          "profile": {
            "slug": "xia",
            "printable_name": "Xia Lee",
            "full_name": "Xia Lee",
            "nick_name": "Xia",
            "picture": null,
            "type": "personal",
            "credentials": true,
            "created_at": "2024-01-01T00:00:00Z",
            "email": "xia@localhost.localdomain",
            "phone": "415-555-5555",
            "street_address": "1 SaaS Road",
            "locality": "San Francisco",
            "region": "California",
            "postal_code": "94133",
            "country": "US",
            "default_timezone": "America/Los_Angeles",
            "is_provider": true,
            "is_bulk_buyer": false,
            "lang": "en",
            "extra": null
          },
          "changes": {
            "last4": {
              "pre": "4674",
              "post": "4242"
            },
            "exp_date": {
              "pre": "07/2024",
              "post": "07/2023"
            }
          }
        }
    """
    LOGGER.debug("[signal] card_updated_notice(organization=%s, user=%s,"\
        "old_card=%s, new_card=%s)", organization, user, old_card, new_card)
    back_url = build_absolute_uri( # saas/backends/stripe_processor/base.py
        location=reverse('saas_update_card', args=(organization,)))
    context = {
        'broker': get_broker(),
        'back_url': back_url,
        'originated_by': user,
        'profile': organization,
        'changes': {
            'last4': {
                'pre': old_card['last4'],
                'post': new_card['last4'],
            },
            'exp_date': {
                'pre': old_card['exp_date'],
                'post': new_card['exp_date'],
            }
        }
    }
    send_notification('card_updated',
      context=ChangeProfileNotificationSerializer().to_representation(context),
      **kwargs)


# We insure the method is only bounded once no matter how many times
# this module is loaded by using a dispatch_uid as advised here:
#   https://docs.djangoproject.com/en/dev/topics/signals/
@receiver(order_executed, dispatch_uid="order_executed_notice")
def order_executed_notice(sender, invoiced_items, user,
                          **kwargs): # no request in kwargs
    """
    Order confirmation

    This notification is sent when an order has been confirmed
    but a charge has not been successfully processed yet.

    **Tags: notification

    **Example

    .. code-block:: json

        {
          "event": "order_executed",
          "broker": {
            "slug": "djaoapp",
            "printable_name": "DjaoApp",
            "full_name": "DjaoApp inc.",
            "nick_name": "DjaoApp",
            "picture": null,
            "type": "organization",
            "credentials": false,
            "created_at": "2024-01-01T00:00:00Z",
            "email": "djaoapp@localhost.localdomain",
            "phone": "415-555-5555",
            "street_address": "1 SaaS Road",
            "locality": "San Francisco",
            "region": "California",
            "postal_code": "94133",
            "country": "US",
            "default_timezone": "America/Los_Angeles",
            "is_provider": true,
            "is_bulk_buyer": false,
            "lang": "en",
            "extra": null
          },
          "back_url": "{{api_base_url}}",
          "profile": {
            "slug": "xia",
            "printable_name": "Xia",
            "full_name": "Xia Lee",
            "nick_name": "Xia",
            "picture": null,
            "type": "personal",
            "credentials": true,
            "created_at": "2024-01-01T00:00:00Z",
            "email": "xia@localhost.localdomain",
            "phone": "415-555-5556",
            "street_address": "1 SaaS Road",
            "locality": "San Francisco",
            "region": "California",
            "postal_code": "94133",
            "country": "US",
            "default_timezone": "America/Los_Angeles",
            "is_provider": false,
            "is_bulk_buyer": false,
            "lang": "en",
            "extra": null
          },
          "originated_by": {
            "slug": "xia",
            "username": "xia",
            "printable_name": "Xia",
            "full_name": "Xia Lee",
            "nick_name": "Xia",
            "picture": null,
            "type": "personal",
            "credentials": true,
            "created_at": "2024-01-01T00:00:00Z",
            "last_login": "2024-01-01T00:00:00Z",
            "email": "xia@localhost.localdomain",
            "phone": "415-555-5556",
            "lang": "en",
            "extra": null
          },
          "invoiced_items": [{
              "created_at": "2024-01-01T00:00:00Z",
              "description": "Subscription to premium until 2025/12/31 (12 months)",
              "amount": 11900,
              "is_debit": false,
              "orig_account": "Receivable",
              "orig_profile": {
                  "slug": "djaoapp",
                  "printable_name": "DjaoApp",
                  "picture": null,
                  "type": "organization",
                  "credentials": false
              },
              "orig_amount": 11900,
              "orig_unit": "usd",
              "dest_account": "Payable",
              "dest_profile": {
                  "slug": "xia",
                  "printable_name": "Xia",
                  "picture": null,
                  "type": "personal",
                  "credentials": true
              },
              "dest_amount": 11900,
              "dest_unit": "usd"
          }],
          "provider": {
            "slug": "djaoapp",
            "printable_name": "DjaoApp",
            "full_name": "DjaoApp inc.",
            "nick_name": "DjaoApp",
            "picture": null,
            "type": "organization",
            "credentials": false,
            "created_at": "2024-01-01T00:00:00Z",
            "email": "djaoapp@localhost.localdomain",
            "phone": "415-555-5555",
            "street_address": "1 SaaS Road",
            "locality": "San Francisco",
            "region": "California",
            "postal_code": "94133",
            "country": "US",
            "default_timezone": "America/Los_Angeles",
            "is_provider": true,
            "is_bulk_buyer": false,
            "lang": "en",
            "extra": null
          }
        }
    """
    invoiced_items = list(invoiced_items)
    organization = (invoiced_items[0].dest_organization
        if invoiced_items else None)
    LOGGER.debug("[signal] order_executed_notice(invoiced_items=%s, user=%s)",
        [invoiced_item.pk for invoiced_item in invoiced_items], user)
    broker = get_broker()
    back_url = build_absolute_uri() # saas/models.py
    provider = broker # XXX
    context = {
        'broker': broker,
        'back_url': back_url,
        'originated_by': user,
        'profile': organization,
        'provider': provider,
        'invoiced_items': invoiced_items,
    }
    send_notification('order_executed',
        context=InvoiceNotificationSerializer().to_representation(context),
        **kwargs)


# We insure the method is only bounded once no matter how many times
# this module is loaded by using a dispatch_uid as advised here:
#   https://docs.djangoproject.com/en/dev/topics/signals/
@receiver(renewal_charge_failed, dispatch_uid="renewal_charge_failed_notice")
def renewal_charge_failed_notice(sender, invoiced_items, total_price,
                                 final_notice, **kwargs): # no request in kwargs
    """
    Renewal failed

    This notification is sent when attempting to charge the credit card
    on file for renewal failed.

    **Tags: notification

    **Example

    .. code-block:: json

        {
          "event": "renewal_charge_failed",
          "broker": {
            "slug": "djaoapp",
            "printable_name": "DjaoApp",
            "full_name": "DjaoApp inc.",
            "nick_name": "DjaoApp",
            "picture": null,
            "type": "organization",
            "credentials": false,
            "created_at": "2024-01-01T00:00:00Z",
            "email": "djaoapp@localhost.localdomain",
            "phone": "415-555-5555",
            "street_address": "1 SaaS Road",
            "locality": "San Francisco",
            "region": "California",
            "postal_code": "94133",
            "country": "US",
            "default_timezone": "America/Los_Angeles",
            "is_provider": true,
            "is_bulk_buyer": false,
            "lang": "en",
            "extra": null
          },
          "back_url": "{{api_base_url}}",
          "profile": {
            "slug": "xia",
            "printable_name": "Xia",
            "full_name": "Xia Lee",
            "nick_name": "Xia",
            "picture": null,
            "type": "personal",
            "credentials": true,
            "created_at": "2024-01-01T00:00:00Z",
            "email": "xia@localhost.localdomain",
            "phone": "415-555-5556",
            "street_address": "1 SaaS Road",
            "locality": "San Francisco",
            "region": "California",
            "postal_code": "94133",
            "country": "US",
            "default_timezone": "America/Los_Angeles",
            "is_provider": false,
            "is_bulk_buyer": false,
            "lang": "en",
            "extra": null
          },
          "charge_total": {
            "amount": 11900,
            "unit": "usd"
          },
          "invoiced_items": [{
              "created_at": "2024-01-01T00:00:00Z",
              "description": "Subscription to premium until 2025/12/31 (12 months)",
              "amount": 11900,
              "is_debit": false,
              "orig_account": "Receivable",
              "orig_profile": {
                  "slug": "djaoapp",
                  "printable_name": "DjaoApp",
                  "picture": null,
                  "type": "organization",
                  "credentials": false
              },
              "orig_amount": 11900,
              "orig_unit": "usd",
              "dest_account": "Payable",
              "dest_profile": {
                  "slug": "xia",
                  "printable_name": "Xia",
                  "picture": null,
                  "type": "personal",
                  "credentials": true
              },
              "dest_amount": 11900,
              "dest_unit": "usd"
          }],
          "nb_renewal_attempts": 1,
          "max_renewal_attempts": 3,
          "final_notice": false,
          "provider": {
            "slug": "djaoapp",
            "printable_name": "DjaoApp",
            "full_name": "DjaoApp inc.",
            "nick_name": "DjaoApp",
            "picture": null,
            "type": "organization",
            "credentials": false,
            "created_at": "2024-01-01T00:00:00Z",
            "email": "djaoapp@localhost.localdomain",
            "phone": "415-555-5555",
            "street_address": "1 SaaS Road",
            "locality": "San Francisco",
            "region": "California",
            "postal_code": "94133",
            "country": "US",
            "default_timezone": "America/Los_Angeles",
            "is_provider": true,
            "is_bulk_buyer": false,
            "lang": "en",
            "extra": null
          }
        }
    """
    #pylint:disable=too-many-locals
    invoiced_items = list(invoiced_items)
    organization = (invoiced_items[0].dest_organization
        if invoiced_items else None)
    LOGGER.debug("[signal] renewal_charge_failed_notice(invoiced_items=%s,"\
        " total_price=%s, final_notice=%s)",
        [invoiced_item.pk for invoiced_item in invoiced_items],
        total_price, final_notice)
    broker = get_broker()
    provider = broker # XXX
    back_url = build_absolute_uri( # saas/renewals.py
        location=reverse('saas_organization_cart', args=(organization,)))
    context = {
        'broker': broker,
        'provider': provider,
        'profile': organization,
        'invoiced_items': invoiced_items,
        'charge_total': total_price,
        'nb_renewal_attempts': organization.nb_renewal_attempts,
        'max_renewal_attempts': saas_settings.MAX_RENEWAL_ATTEMPTS,
        'final_notice': final_notice,
        'back_url': back_url
    }
    send_notification('renewal_charge_failed',
      context=RenewalFailedNotificationSerializer().to_representation(context),
      **kwargs)


@receiver(claim_code_generated, dispatch_uid="claim_code_generated_notice")
def claim_code_generated_notice(sender, subscriber, claim_code, user,
                                **kwargs): # not request in kwargs
    """
    Claim code

    This notification is sent to the user invited through a groupBuy.

    **Tags: notification

    **Example

    .. code-block:: json

       {
          "event": "claim_code_generated",
          "broker": {
            "slug": "djaoapp",
            "printable_name": "DjaoApp",
            "full_name": "DjaoApp inc.",
            "nick_name": "DjaoApp",
            "picture": null,
            "type": "organization",
            "credentials": false,
            "created_at": "2024-01-01T00:00:00Z",
            "email": "djaoapp@localhost.localdomain",
            "phone": "415-555-5555",
            "street_address": "1 SaaS Road",
            "locality": "San Francisco",
            "region": "California",
            "postal_code": "94133",
            "country": "US",
            "default_timezone": "America/Los_Angeles",
            "is_provider": true,
            "is_bulk_buyer": false,
            "lang": "en",
            "extra": null
          },
          "back_url": "{{api_base_url}}",
          "profile": {
            "slug": "xia",
            "printable_name": "Xia",
            "full_name": "Xia Lee",
            "nick_name": "Xia",
            "picture": null,
            "type": "personal",
            "credentials": true,
            "created_at": "2024-01-01T00:00:00Z",
            "email": "xia@localhost.localdomain",
            "phone": "415-555-5556",
            "street_address": "1 SaaS Road",
            "locality": "San Francisco",
            "region": "California",
            "postal_code": "94133",
            "country": "US",
            "default_timezone": "America/Los_Angeles",
            "is_provider": false,
            "is_bulk_buyer": false,
            "lang": "en",
            "extra": null
          },
          "originated_by": {
            "slug": "xia",
            "username": "xia",
            "printable_name": "Xia",
            "full_name": "Xia Lee",
            "nick_name": "Xia",
            "picture": null,
            "type": "personal",
            "credentials": true,
            "created_at": "2024-01-01T00:00:00Z",
            "last_login": "2024-01-01T00:00:00Z",
            "email": "xia@localhost.localdomain",
            "phone": "415-555-5556",
            "lang": "en",
            "extra": null
          },
          "cart_items": [{
            "created_at": "2024-01-01T00:00:00Z",
            "user": {
              "slug": "emilie",
              "username": "emilie",
              "printable_name": "Emilie",
              "full_name": "Emilie Jolie",
              "nick_name": "Emilie",
              "picture": null,
              "type": "user",
              "credentials": false,
              "created_at": "2024-01-01T00:00:00Z",
              "last_login": null,
              "email": "emilie@localhost.localdomain",
              "phone": "415-555-5557",
              "lang": "en",
              "extra": null
            },
            "plan": {
              "slug": "premium",
              "title": "Premium"
            },
            "option": 1,
            "full_name": "Emilie Jolie",
            "sync_on": "emilie@localhost.localdomain",
            "email": "emilie@localhost.localdomain"
          }],
          "provider": {
            "slug": "djaoapp",
            "printable_name": "DjaoApp",
            "full_name": "DjaoApp inc.",
            "nick_name": "DjaoApp",
            "picture": null,
            "type": "organization",
            "credentials": false,
            "created_at": "2024-01-01T00:00:00Z",
            "email": "djaoapp@localhost.localdomain",
            "phone": "415-555-5555",
            "street_address": "1 SaaS Road",
            "locality": "San Francisco",
            "region": "California",
            "postal_code": "94133",
            "country": "US",
            "default_timezone": "America/Los_Angeles",
            "is_provider": true,
            "is_bulk_buyer": false,
            "lang": "en",
            "extra": null
          }
        }
    """
    cart_items = CartItem.objects.by_claim_code(claim_code)
    provider = CartItem.objects.provider(cart_items)
    LOGGER.debug("[signal] claim_code_notice(subscriber=%s, claim_code=%s,"\
        " user=%s)", subscriber, claim_code, user)
    # XXX We don't use `_notified_recipients` here as an attempt
    # only have one person respnsible for using the claim code.
    back_url = build_absolute_uri( # saas/models.py
        location=reverse('saas_cart')) + ("?code=%s" % claim_code)
    context = {
        'broker': get_broker(),
        'back_url': back_url,
        'profile': subscriber,
        'provider': provider,
        'cart_items': cart_items,
        'detail': "", # XXX
        'originated_by': user
    }
    send_notification('claim_code_generated',
        context=ClaimNotificationSerializer().to_representation(context),
        **kwargs)


@receiver(profile_updated, dispatch_uid="profile_updated_notice")
def profile_updated_notice(sender, organization, changes, user,
                           **kwargs): # request in kwargs
    """
    Profile updated

    This notification is sent when a profile is updated.

    **Tags: notification

    **Example

    .. code-block:: json

       {
          "event": "profile_updated",
          "broker": {
            "slug": "djaoapp",
            "printable_name": "DjaoApp",
            "full_name": "DjaoApp inc.",
            "nick_name": "DjaoApp",
            "picture": null,
            "type": "organization",
            "credentials": false,
            "created_at": "2024-01-01T00:00:00Z",
            "email": "djaoapp@localhost.localdomain",
            "phone": "415-555-5555",
            "street_address": "1 SaaS Road",
            "locality": "San Francisco",
            "region": "California",
            "postal_code": "94133",
            "country": "US",
            "default_timezone": "America/Los_Angeles",
            "is_provider": true,
            "is_bulk_buyer": false,
            "lang": "en",
            "extra": null
          },
          "back_url": "{{api_base_url}}",
          "profile": {
            "slug": "xia",
            "printable_name": "Xia",
            "full_name": "Xia Lee",
            "nick_name": "Xia",
            "picture": null,
            "type": "personal",
            "credentials": true,
            "created_at": "2024-01-01T00:00:00Z",
            "email": "xia@localhost.localdomain",
            "phone": "415-555-5556",
            "street_address": "1 SaaS Road",
            "locality": "San Francisco",
            "region": "California",
            "postal_code": "94133",
            "country": "US",
            "default_timezone": "America/Los_Angeles",
            "is_provider": false,
            "is_bulk_buyer": false,
            "lang": "en",
            "extra": null
          },
          "originated_by": {
            "slug": "xia",
            "username": "xia",
            "printable_name": "Xia",
            "full_name": "Xia Lee",
            "nick_name": "Xia",
            "picture": null,
            "type": "personal",
            "credentials": true,
            "created_at": "2024-01-01T00:00:00Z",
            "last_login": "2024-01-01T00:00:00Z",
            "email": "xia@localhost.localdomain",
            "phone": "415-555-5556",
            "lang": "en",
            "extra": null
          },
          "changes": {
            "full_name": {
              "pre": "Xia Lee",
              "post": "Xia Wang"
            }
          }
        }
    """
    if not changes:
        return
    #pylint:disable=unused-variable
    LOGGER.info("%s updated", organization,
        extra={'event': 'update-fields', 'organization': str(organization),
               'changes': changes})
    broker = get_broker()
    request = kwargs.get('request')
    back_url = build_absolute_uri( # saas/views/profile.py
        location=reverse(          # saas/api/organizations.py
            'saas_organization_profile', args=(organization,)),
        request=request)
    # Some changes are still typed by the model field (ex: Country).
    # We want to make sure we have a JSON-serializable `changes` dict here.
    non_empty_fields_updated = False
    for change in six.itervalues(changes):
        pre = change.get('pre')
        if pre:
            non_empty_fields_updated = True
        change.update({
            'pre': str(pre),
            'post': str(change.get('post'))
        })
    context={
        'broker': broker,
        'back_url': back_url,
        'originated_by': request.user if request else None,
        'profile': organization,
        'changes': changes
    }
    if non_empty_fields_updated:
        # We are not going to send notifications if all fields updated
        # were previously empty.
        send_notification('profile_updated',
            context=ChangeProfileNotificationSerializer().to_representation(
            context), **kwargs)


# We insure the method is only bounded once no matter how many times
# this module is loaded by using a dispatch_uid as advised here:
#   https://docs.djangoproject.com/en/dev/topics/signals/
@receiver(processor_setup_error, dispatch_uid="processor_setup_error_notice")
def processor_setup_error_notice(sender, provider, error_message, customer,
                                 **kwargs): # no request in kwargs
    """
    Error with processor setup

    The processor returned an error when a user attempted to pay for a cart.

    **Tags: notification

    **Example

    .. code-block:: json

       {
          "event": "processor_setup_error",
          "broker": {
            "slug": "djaoapp",
            "printable_name": "DjaoApp",
            "full_name": "DjaoApp inc.",
            "nick_name": "DjaoApp",
            "picture": null,
            "type": "organization",
            "credentials": false,
            "created_at": "2024-01-01T00:00:00Z",
            "email": "djaoapp@localhost.localdomain",
            "phone": "415-555-5555",
            "street_address": "1 SaaS Road",
            "locality": "San Francisco",
            "region": "California",
            "postal_code": "94133",
            "country": "US",
            "default_timezone": "America/Los_Angeles",
            "is_provider": true,
            "is_bulk_buyer": false,
            "lang": "en",
            "extra": null
          },
          "back_url": "{{api_base_url}}",
          "profile": {
            "slug": "xia",
            "printable_name": "Xia",
            "full_name": "Xia Lee",
            "nick_name": "Xia",
            "picture": null,
            "type": "personal",
            "credentials": true,
            "created_at": "2024-01-01T00:00:00Z",
            "email": "xia@localhost.localdomain",
            "phone": "415-555-5556",
            "street_address": "1 SaaS Road",
            "locality": "San Francisco",
            "region": "California",
            "postal_code": "94133",
            "country": "US",
            "default_timezone": "America/Los_Angeles",
            "is_provider": false,
            "is_bulk_buyer": false,
            "lang": "en",
            "extra": null
          },
          "originated_by": {
            "slug": "xia",
            "username": "xia",
            "printable_name": "Xia",
            "full_name": "Xia Lee",
            "nick_name": "Xia",
            "picture": null,
            "type": "personal",
            "credentials": true,
            "created_at": "2024-01-01T00:00:00Z",
            "last_login": "2024-01-01T00:00:00Z",
            "email": "xia@localhost.localdomain",
            "phone": "415-555-5556",
            "lang": "en",
            "extra": null
          },
          "detail": "There is no payment processor account connected.",
          "provider": {
            "slug": "djaoapp",
            "printable_name": "DjaoApp",
            "full_name": "DjaoApp inc.",
            "nick_name": "DjaoApp",
            "picture": null,
            "type": "organization",
            "credentials": false,
            "created_at": "2024-01-01T00:00:00Z",
            "email": "djaoapp@localhost.localdomain",
            "phone": "415-555-5555",
            "street_address": "1 SaaS Road",
            "locality": "San Francisco",
            "region": "California",
            "postal_code": "94133",
            "country": "US",
            "default_timezone": "America/Los_Angeles",
            "is_provider": true,
            "is_bulk_buyer": false,
            "lang": "en",
            "extra": null
          }
        }
    """
    back_url = build_absolute_uri(                              # saas/models.py
        location=reverse('saas_update_bank', args=(provider,)))
    context = {
        'broker': get_broker(),
        'back_url': back_url,
        'profile': customer,
        'provider': provider,
        'detail': error_message,
    }
    request_user = kwargs.get('request_user', None)
    context.update({'originated_by': request_user if request_user else None})
    send_notification('processor_setup_error',
      context=ProcessorSetupNotificationSerializer().to_representation(context),
      **kwargs)


# We insure the method is only bounded once no matter how many times
# this module is loaded by using a dispatch_uid as advised here:
#   https://docs.djangoproject.com/en/dev/topics/signals/
@receiver(role_grant_created, dispatch_uid="role_grant_created_notice")
def role_grant_created_notice(sender, role, reason=None,
                              **kwargs): # request in kwargs
    """
    Role granted

    This notification is sent when a user has been granted a role on a profile.

    **Tags: notification

    **Example

    .. code-block:: json

       {
          "event": "role_grant_created",
          "broker": {
            "slug": "djaoapp",
            "printable_name": "DjaoApp",
            "full_name": "DjaoApp inc.",
            "nick_name": "DjaoApp",
            "picture": null,
            "type": "organization",
            "credentials": false,
            "created_at": "2024-01-01T00:00:00Z",
            "email": "djaoapp@localhost.localdomain",
            "phone": "415-555-5555",
            "street_address": "1 SaaS Road",
            "locality": "San Francisco",
            "region": "California",
            "postal_code": "94133",
            "country": "US",
            "default_timezone": "America/Los_Angeles",
            "is_provider": true,
            "is_bulk_buyer": false,
            "lang": "en",
            "extra": null
          },
          "back_url": "{{api_base_url}}",
          "profile": {
            "slug": "xia",
            "printable_name": "Xia",
            "full_name": "Xia Lee",
            "nick_name": "Xia",
            "picture": null,
            "type": "personal",
            "credentials": true,
            "created_at": "2024-01-01T00:00:00Z",
            "email": "xia@localhost.localdomain",
            "phone": "415-555-5556",
            "street_address": "1 SaaS Road",
            "locality": "San Francisco",
            "region": "California",
            "postal_code": "94133",
            "country": "US",
            "default_timezone": "America/Los_Angeles",
            "is_provider": false,
            "is_bulk_buyer": false,
            "lang": "en",
            "extra": null
          },
          "originated_by": {
            "slug": "xia",
            "username": "xia",
            "printable_name": "Xia",
            "full_name": "Xia Lee",
            "nick_name": "Xia",
            "picture": null,
            "type": "personal",
            "credentials": true,
            "created_at": "2024-01-01T00:00:00Z",
            "last_login": "2024-01-01T00:00:00Z",
            "email": "xia@localhost.localdomain",
            "phone": "415-555-5556",
            "lang": "en",
            "extra": null
          },
          "user": {
            "slug": "emilie",
            "username": "emilie",
            "printable_name": "Emilie",
            "full_name": "Emilie Jolie",
            "nick_name": "Emilie",
            "picture": null,
            "type": "user",
            "credentials": false,
            "created_at": "2024-01-01T00:00:00Z",
            "last_login": "",
            "email": "emilie@localhost.localdomain",
            "phone": "415-555-5557",
            "lang": "en",
            "extra": null
          },
          "role_description": {
            "slug": "manager",
            "title": "Managers"
          }
        }
    """
    user = role.user
    organization = role.organization
    request = kwargs.get('request')
    back_url = build_absolute_uri(                          # saas/api/roles.py
        location=reverse('organization_app', args=(organization,)),
        request=request)
    if role.grant_key:
        back_url = build_absolute_uri(
            location=reverse('saas_role_grant_accept', args=(role.grant_key,)),
            request=request)
    if has_invalid_password(user):
        reason = _("You have been invited to create an account"\
            " to join %(organization)s.") % {
            'organization': role.organization.printable_name}
        Contact.objects.prepare_email_verification(
            user.email, user=user, reason=reason)
    context = {
        'broker': get_broker(),
        'back_url': back_url,
        'profile': organization,
        'role_description': {
            'slug': role.role_description.slug,
            'title': role.role_description.title,
        },
        'detail': reason if reason is not None else "",
        'user': user
    }
    request_user = kwargs.get('request_user', None)
    context.update({'originated_by': request_user if request_user else None})
    LOGGER.debug("[signal] role_grant_created_notice(role=%s,"\
        " reason=%s)", role, reason)
    send_notification('role_grant_created',
        context=RoleGrantNotificationSerializer().to_representation(context),
        **kwargs)


# We insure the method is only bounded once no matter how many times
# this module is loaded by using a dispatch_uid as advised here:
#   https://docs.djangoproject.com/en/dev/topics/signals/
@receiver(role_request_created, dispatch_uid="role_request_created_notice")
def role_request_created_notice(sender, role, reason=None,
                                **kwargs): # request in kwargs
    """
    Role requested

    This notification is sent when a user has requested a role on a profile.

    **Tags: notification

    **Example

    .. code-block:: json

       {
          "event": "role_request_created",
          "broker": {
            "slug": "djaoapp",
            "printable_name": "DjaoApp",
            "full_name": "DjaoApp inc.",
            "nick_name": "DjaoApp",
            "picture": null,
            "type": "organization",
            "credentials": false,
            "created_at": "2024-01-01T00:00:00Z",
            "email": "djaoapp@localhost.localdomain",
            "phone": "415-555-5555",
            "street_address": "1 SaaS Road",
            "locality": "San Francisco",
            "region": "California",
            "postal_code": "94133",
            "country": "US",
            "default_timezone": "America/Los_Angeles",
            "is_provider": true,
            "is_bulk_buyer": false,
            "lang": "en",
            "extra": null
          },
          "back_url": "{{api_base_url}}",
          "profile": {
            "slug": "xia",
            "printable_name": "Xia",
            "full_name": "Xia Lee",
            "nick_name": "Xia",
            "picture": null,
            "type": "personal",
            "credentials": true,
            "created_at": "2024-01-01T00:00:00Z",
            "email": "xia@localhost.localdomain",
            "phone": "415-555-5556",
            "street_address": "1 SaaS Road",
            "locality": "San Francisco",
            "region": "California",
            "postal_code": "94133",
            "country": "US",
            "default_timezone": "America/Los_Angeles",
            "is_provider": false,
            "is_bulk_buyer": false,
            "lang": "en",
            "extra": null
          },
          "originated_by": {
            "slug": "xia",
            "username": "xia",
            "printable_name": "Xia",
            "full_name": "Xia Lee",
            "nick_name": "Xia",
            "picture": null,
            "type": "personal",
            "credentials": true,
            "created_at": "2024-01-01T00:00:00Z",
            "last_login": "2024-01-01T00:00:00Z",
            "email": "xia@localhost.localdomain",
            "phone": "415-555-5556",
            "lang": "en",
            "extra": null
          },
          "user": {
            "slug": "emilie",
            "username": "emilie",
            "printable_name": "Emilie",
            "full_name": "Emilie Jolie",
            "nick_name": "Emilie",
            "picture": null,
            "type": "user",
            "credentials": false,
            "created_at": "2024-01-01T00:00:00Z",
            "last_login": "",
            "email": "emilie@localhost.localdomain",
            "phone": "415-555-5557",
            "lang": "en",
            "extra": null
          }
        }
    """
    organization = role.organization
    user = role.user
    back_url = build_absolute_uri(                         # saas/api/roles.py
        location=reverse('saas_role_list', args=(organization,)),
        request=kwargs.get('request'))
    LOGGER.debug("[signal] role_request_created_notice("\
        "organization=%s, user=%s, reason=%s)",
        organization, user, reason)
    context = {
        'broker': get_broker(),
        'back_url': back_url,
        'profile': organization,
        'detail': reason if reason is not None else "",
        'user': user
    }
    request_user = kwargs.get('request_user', None)
    context.update({'originated_by': request_user if request_user else None})
    send_notification('role_request_created',
        context=RoleRequestNotificationSerializer().to_representation(context),
        **kwargs)


# We insure the method is only bounded once no matter how many times
# this module is loaded by using a dispatch_uid as advised here:
#   https://docs.djangoproject.com/en/dev/topics/signals/
@receiver(role_grant_accepted, dispatch_uid="role_grant_accepted_notice")
def role_grant_accepted_notice(sender, role, grant_key,
                               **kwargs): # request in kwargs
    """
    Role grant accepted

    This notification is sent when a user has accepted a role that was
    granted on a profile.

    **Tags: notification

    **Example

    .. code-block:: json

       {
          "event": "role_grant_accepted",
          "broker": {
            "slug": "djaoapp",
            "printable_name": "DjaoApp",
            "full_name": "DjaoApp inc.",
            "nick_name": "DjaoApp",
            "picture": null,
            "type": "organization",
            "credentials": false,
            "created_at": "2024-01-01T00:00:00Z",
            "email": "djaoapp@localhost.localdomain",
            "phone": "415-555-5555",
            "street_address": "1 SaaS Road",
            "locality": "San Francisco",
            "region": "California",
            "postal_code": "94133",
            "country": "US",
            "default_timezone": "America/Los_Angeles",
            "is_provider": true,
            "is_bulk_buyer": false,
            "lang": "en",
            "extra": null
          },
          "back_url": "{{api_base_url}}",
          "profile": {
            "slug": "xia",
            "printable_name": "Xia",
            "full_name": "Xia Lee",
            "nick_name": "Xia",
            "picture": null,
            "type": "personal",
            "credentials": true,
            "created_at": "2024-01-01T00:00:00Z",
            "email": "xia@localhost.localdomain",
            "phone": "415-555-5556",
            "street_address": "1 SaaS Road",
            "locality": "San Francisco",
            "region": "California",
            "postal_code": "94133",
            "country": "US",
            "default_timezone": "America/Los_Angeles",
            "is_provider": false,
            "is_bulk_buyer": false,
            "lang": "en",
            "extra": null
          },
          "originated_by": {
            "slug": "xia",
            "username": "xia",
            "printable_name": "Xia",
            "full_name": "Xia Lee",
            "nick_name": "Xia",
            "picture": null,
            "type": "personal",
            "credentials": true,
            "created_at": "2024-01-01T00:00:00Z",
            "last_login": "2024-01-01T00:00:00Z",
            "email": "xia@localhost.localdomain",
            "phone": "415-555-5556",
            "lang": "en",
            "extra": null
          },
          "user": {
            "slug": "emilie",
            "username": "emilie",
            "printable_name": "Emilie",
            "full_name": "Emilie Jolie",
            "nick_name": "Emilie",
            "picture": null,
            "type": "user",
            "credentials": false,
            "created_at": "2024-01-01T00:00:00Z",
            "last_login": "",
            "email": "emilie@localhost.localdomain",
            "phone": "415-555-5557",
            "lang": "en",
            "extra": null
          },
          "role_description": {
            "slug": "manager",
            "title": "Managers"
          }
        }
    """
    LOGGER.debug("[signal] role_grant_accepted_notice("\
        " role=%s, grant_key=%s)", role, grant_key)
    request_user = kwargs.get('request_user', None)
    originated_by = request_user if request_user else None
    back_url = build_absolute_uri( # saas/api/roles.py saas/views/roles.py
        location=reverse('saas_role_detail', args=(
            role.organization, role.role_description)),
        request=kwargs.get('request'))
    context={
        'broker': get_broker(),
        'back_url': back_url,
        'profile': role.organization,
        'role_description': {
            'slug': role.role_description.slug,
            'title': role.role_description.title,
        },
        'user': originated_by,
        'detail': "",
        'originated_by': originated_by
    }
    send_notification('role_grant_accepted',
        context=RoleGrantNotificationSerializer().to_representation(context),
        **kwargs)


# We insure the method is only bounded once no matter how many times
# this module is loaded by using a dispatch_uid as advised here:
#   https://docs.djangoproject.com/en/dev/topics/signals/
@receiver(subscription_grant_accepted,
          dispatch_uid="subscription_grant_accepted_notice")
def subscription_grant_accepted_notice(sender, subscription, grant_key,
                                       **kwargs): # request in kwargs
    """
    Subscription grant accepted

    This notification is sent when a profile has accepted a subscription
    that was previously granted.

    **Tags: notification

    **Example

    .. code-block:: json

       {
          "event": "subscription_grant_accepted",
          "broker": {
            "slug": "djaoapp",
            "printable_name": "DjaoApp",
            "full_name": "DjaoApp inc.",
            "nick_name": "DjaoApp",
            "picture": null,
            "type": "organization",
            "credentials": false,
            "created_at": "2024-01-01T00:00:00Z",
            "email": "djaoapp@localhost.localdomain",
            "phone": "415-555-5555",
            "street_address": "1 SaaS Road",
            "locality": "San Francisco",
            "region": "California",
            "postal_code": "94133",
            "country": "US",
            "default_timezone": "America/Los_Angeles",
            "is_provider": true,
            "is_bulk_buyer": false,
            "lang": "en",
            "extra": null
          },
          "back_url": "{{api_base_url}}",
          "profile": {
            "slug": "xia",
            "printable_name": "Xia",
            "full_name": "Xia Lee",
            "nick_name": "Xia",
            "picture": null,
            "type": "personal",
            "credentials": true,
            "created_at": "2024-01-01T00:00:00Z",
            "email": "xia@localhost.localdomain",
            "phone": "415-555-5556",
            "street_address": "1 SaaS Road",
            "locality": "San Francisco",
            "region": "California",
            "postal_code": "94133",
            "country": "US",
            "default_timezone": "America/Los_Angeles",
            "is_provider": false,
            "is_bulk_buyer": false,
            "lang": "en",
            "extra": null
          },
          "originated_by": {
            "slug": "xia",
            "username": "xia",
            "printable_name": "Xia",
            "full_name": "Xia Lee",
            "nick_name": "Xia",
            "picture": null,
            "type": "personal",
            "credentials": true,
            "created_at": "2024-01-01T00:00:00Z",
            "last_login": "2024-01-01T00:00:00Z",
            "email": "xia@localhost.localdomain",
            "phone": "415-555-5556",
            "lang": "en",
            "extra": null
          },
          "plan": {
            "slug": "premium",
            "title": "Premium"
          }
        }
    """
    provider = subscription.plan.organization
    request = kwargs.get('request')
    originated_by = request.user if request else None
    LOGGER.debug("[signal] subscribe_grant_accepted_notice("\
        " subscription=%s, grant_key=%s)", subscription, grant_key)
    back_url = build_absolute_uri( # saas/views/optins.py
        location=reverse('organization_app', args=(provider,)),
        request=request)
    context = {
        'broker': get_broker(),
        'back_url': back_url,
        'profile': subscription.plan.organization,
        'plan': subscription.plan,
        'subscriber': subscription.organization,
        'originated_by': originated_by
    }
    send_notification('subscription_grant_accepted',
        context=SubscriptionAcceptedNotificationSerializer().to_representation(
        context), **kwargs)


# We insure the method is only bounded once no matter how many times
# this module is loaded by using a dispatch_uid as advised here:
#   https://docs.djangoproject.com/en/dev/topics/signals/
@receiver(subscription_grant_created,
          dispatch_uid="subscription_grant_created_notice")
def subscription_grant_created_notice(sender, subscription, reason=None,
                                      invite=False,
                                      **kwargs): # request in kwargs
    """
    Subscription granted

    This notification is sent when a profile is granted a subscription
    to a plan.

    **Tags: notification

    **Example

    .. code-block:: json

       {
          "event": "subscription_grant_created",
          "broker": {
            "slug": "djaoapp",
            "printable_name": "DjaoApp",
            "full_name": "DjaoApp inc.",
            "nick_name": "DjaoApp",
            "picture": null,
            "type": "organization",
            "credentials": false,
            "created_at": "2024-01-01T00:00:00Z",
            "email": "djaoapp@localhost.localdomain",
            "phone": "415-555-5555",
            "street_address": "1 SaaS Road",
            "locality": "San Francisco",
            "region": "California",
            "postal_code": "94133",
            "country": "US",
            "default_timezone": "America/Los_Angeles",
            "is_provider": true,
            "is_bulk_buyer": false,
            "lang": "en",
            "extra": null
          },
          "back_url": "{{api_base_url}}",
          "profile": {
            "slug": "xia",
            "printable_name": "Xia",
            "full_name": "Xia Lee",
            "nick_name": "Xia",
            "picture": null,
            "type": "personal",
            "credentials": true,
            "created_at": "2024-01-01T00:00:00Z",
            "email": "xia@localhost.localdomain",
            "phone": "415-555-5556",
            "street_address": "1 SaaS Road",
            "locality": "San Francisco",
            "region": "California",
            "postal_code": "94133",
            "country": "US",
            "default_timezone": "America/Los_Angeles",
            "is_provider": false,
            "is_bulk_buyer": false,
            "lang": "en",
            "extra": null
          },
          "originated_by": {
            "slug": "xia",
            "username": "xia",
            "printable_name": "Xia",
            "full_name": "Xia Lee",
            "nick_name": "Xia",
            "picture": null,
            "type": "personal",
            "credentials": true,
            "created_at": "2024-01-01T00:00:00Z",
            "last_login": "2024-01-01T00:00:00Z",
            "email": "xia@localhost.localdomain",
            "phone": "415-555-5556",
            "lang": "en",
            "extra": null
          },
          "plan": {
            "slug": "premium",
            "title": "Premium"
          }
        }
    """
    #pylint:disable=too-many-locals
    if subscription.grant_key:
        request = kwargs.get('request')
        originated_by = request.user if request else None
        organization = subscription.organization
        back_url = build_absolute_uri( # saas/api/subscriptions.py
            location=reverse('subscription_grant_accept', args=(
            organization, subscription.grant_key,)),
            request=request)
        LOGGER.debug("[signal] subscribe_grant_created_notice("\
            " subscription=%s, reason=%s, invite=%s)",
            subscription, reason, invite)
        # We don't use `_notified_recipients` because
        #    1. We need the actual User object to update/create a Contact
        #    2. We should not send to the organization e-mail address
        #       because the e-mail there might not be linked to a manager.
        context = {
            'broker': get_broker(),
            'back_url': back_url,
            'profile': organization,
            'plan': subscription.plan,
            'provider': subscription.plan.organization,
            'detail': reason if reason is not None else "",
            'is_invite': invite,
            'originated_by': originated_by
        }
        send_notification('subscription_grant_created',
            context=SubscriptionCreatedNotificationSerializer(
            ).to_representation(context), **kwargs)


# We insure the method is only bounded once no matter how many times
# this module is loaded by using a dispatch_uid as advised here:
#   https://docs.djangoproject.com/en/dev/topics/signals/
@receiver(subscription_request_accepted,
          dispatch_uid="subscription_request_accepted_notice")
def subscription_request_accepted_notice(sender, subscription, request_key,
                                         **kwargs): # request in kwargs
    """
    Subscription request accepted

    This notification is sent when a provider accepts to grant a subscription
    a profile previously requested.

    **Tags: notification

    **Example

    .. code-block:: json

       {
          "event": "subscription_request_accepted",
          "broker": {
            "slug": "djaoapp",
            "printable_name": "DjaoApp",
            "full_name": "DjaoApp inc.",
            "nick_name": "DjaoApp",
            "picture": null,
            "type": "organization",
            "credentials": false,
            "created_at": "2024-01-01T00:00:00Z",
            "email": "djaoapp@localhost.localdomain",
            "phone": "415-555-5555",
            "street_address": "1 SaaS Road",
            "locality": "San Francisco",
            "region": "California",
            "postal_code": "94133",
            "country": "US",
            "default_timezone": "America/Los_Angeles",
            "is_provider": true,
            "is_bulk_buyer": false,
            "lang": "en",
            "extra": null
          },
          "back_url": "{{api_base_url}}",
          "profile": {
            "slug": "xia",
            "printable_name": "Xia",
            "full_name": "Xia Lee",
            "nick_name": "Xia",
            "picture": null,
            "type": "personal",
            "credentials": true,
            "created_at": "2024-01-01T00:00:00Z",
            "email": "xia@localhost.localdomain",
            "phone": "415-555-5556",
            "street_address": "1 SaaS Road",
            "locality": "San Francisco",
            "region": "California",
            "postal_code": "94133",
            "country": "US",
            "default_timezone": "America/Los_Angeles",
            "is_provider": false,
            "is_bulk_buyer": false,
            "lang": "en",
            "extra": null
          },
          "originated_by": {
            "slug": "xia",
            "username": "xia",
            "printable_name": "Xia",
            "full_name": "Xia Lee",
            "nick_name": "Xia",
            "picture": null,
            "type": "personal",
            "credentials": true,
            "created_at": "2024-01-01T00:00:00Z",
            "last_login": "2024-01-01T00:00:00Z",
            "email": "xia@localhost.localdomain",
            "phone": "415-555-5556",
            "lang": "en",
            "extra": null
          },
          "plan": {
            "slug": "premium",
            "title": "Premium"
          }
        }
    """
    subscriber = subscription.organization
    LOGGER.debug("[signal] subscribe_req_accepted_notice("\
        " subscription=%s, request_key=%s)", subscription, request_key)
    request = kwargs.get('request')
    originated_by = request.user if request else None
    back_url = build_absolute_uri(location=reverse( # saas/api/subscriptions.py
        'organization_app', args=(subscriber,)),    # saas/views/optins.py
        request=request)
    context = {
        'broker': get_broker(),
        'back_url': back_url,
        'profile': subscriber,
        'plan': subscription.plan,
        'provider': subscription.plan.organization,
        'originated_by': originated_by
    }
    send_notification('subscription_request_accepted',
        context=SubscriptionAcceptedNotificationSerializer().to_representation(
        context), **kwargs)


# We insure the method is only bounded once no matter how many times
# this module is loaded by using a dispatch_uid as advised here:
#   https://docs.djangoproject.com/en/dev/topics/signals/
@receiver(subscription_request_created,
          dispatch_uid="subscription_request_created_notice")
def subscription_request_created_notice(sender, subscription, reason=None,
                                        **kwargs): # request in kwargs
    """
    Subscription requested

    This notification is sent when a profile is requesting a subscription
    to a plan.


    **Tags: notification

    **Example

    .. code-block:: json

       {
          "event": "subscription_request_created",
          "broker": {
            "slug": "djaoapp",
            "printable_name": "DjaoApp",
            "full_name": "DjaoApp inc.",
            "nick_name": "DjaoApp",
            "picture": null,
            "type": "organization",
            "credentials": false,
            "created_at": "2024-01-01T00:00:00Z",
            "email": "djaoapp@localhost.localdomain",
            "phone": "415-555-5555",
            "street_address": "1 SaaS Road",
            "locality": "San Francisco",
            "region": "California",
            "postal_code": "94133",
            "country": "US",
            "default_timezone": "America/Los_Angeles",
            "is_provider": true,
            "is_bulk_buyer": false,
            "lang": "en",
            "extra": null
          },
          "back_url": "{{api_base_url}}",
          "profile": {
            "slug": "xia",
            "printable_name": "Xia",
            "full_name": "Xia Lee",
            "nick_name": "Xia",
            "picture": null,
            "type": "personal",
            "credentials": true,
            "created_at": "2024-01-01T00:00:00Z",
            "email": "xia@localhost.localdomain",
            "phone": "415-555-5556",
            "street_address": "1 SaaS Road",
            "locality": "San Francisco",
            "region": "California",
            "postal_code": "94133",
            "country": "US",
            "default_timezone": "America/Los_Angeles",
            "is_provider": false,
            "is_bulk_buyer": false,
            "lang": "en",
            "extra": null
          },
          "originated_by": {
            "slug": "xia",
            "username": "xia",
            "printable_name": "Xia",
            "full_name": "Xia Lee",
            "nick_name": "Xia",
            "picture": null,
            "type": "personal",
            "credentials": true,
            "created_at": "2024-01-01T00:00:00Z",
            "last_login": "2024-01-01T00:00:00Z",
            "email": "xia@localhost.localdomain",
            "phone": "415-555-5556",
            "lang": "en",
            "extra": null
          },
          "plan": {
            "slug": "premium",
            "title": "Premium"
          }
        }
    """
    if subscription.request_key:
        request = kwargs.get('request')
        originated_by = request.user if request else None
        organization = subscription.organization
        back_url = build_absolute_uri(location=reverse( # XXX no trigger?
            'subscription_request_accept', args=(
            organization, subscription.request_key,)),
            request=request)
        LOGGER.debug("[signal] subscribe_req_created_notice("\
                     " subscription=%s, reason=%s)", subscription, reason)
        context = {
            'broker': get_broker(),
            'back_url': back_url,
            'profile': subscription.plan.organization,
            'plan': subscription.plan,
            'subscriber': organization,
            'detail': reason if reason is not None else "",
            'originated_by': originated_by
        }
        send_notification('subscription_request_created',
            context=SubscriptionCreatedNotificationSerializer(
            ).to_representation(context),
            **kwargs)


# We insure the method is only bounded once no matter how many times
# this module is loaded by using a dispatch_uid as advised here:
#   https://docs.djangoproject.com/en/dev/topics/signals/
@receiver(card_expires_soon, dispatch_uid="card_expires_soon_notice")
def card_expires_soon_notice(sender, organization, nb_days,
                             **kwargs): # no request in kwargs
    """
    Card expires soon

    This notification is sent when a credit card on file is about to expire.

    **Tags: notification

    **Example

    .. code-block:: json

       {
          "event": "card_expires_soon",
          "broker": {
            "slug": "djaoapp",
            "printable_name": "DjaoApp",
            "full_name": "DjaoApp inc.",
            "nick_name": "DjaoApp",
            "picture": null,
            "type": "organization",
            "credentials": false,
            "created_at": "2024-01-01T00:00:00Z",
            "email": "djaoapp@localhost.localdomain",
            "phone": "415-555-5555",
            "street_address": "1 SaaS Road",
            "locality": "San Francisco",
            "region": "California",
            "postal_code": "94133",
            "country": "US",
            "default_timezone": "America/Los_Angeles",
            "is_provider": true,
            "is_bulk_buyer": false,
            "lang": "en",
            "extra": null
          },
          "back_url": "{{api_base_url}}",
          "profile": {
            "slug": "xia",
            "printable_name": "Xia",
            "full_name": "Xia Lee",
            "nick_name": "Xia",
            "picture": null,
            "type": "personal",
            "credentials": true,
            "created_at": "2024-01-01T00:00:00Z",
            "email": "xia@localhost.localdomain",
            "phone": "415-555-5556",
            "street_address": "1 SaaS Road",
            "locality": "San Francisco",
            "region": "California",
            "postal_code": "94133",
            "country": "US",
            "default_timezone": "America/Los_Angeles",
            "is_provider": false,
            "is_bulk_buyer": false,
            "lang": "en",
            "extra": null
          },
          "last4": "4242",
          "exp_date": "07/2023",
          "nb_expiration_days": 15
        }
    """
    LOGGER.debug("[signal] card_expires_soon_notice("\
                 " organization=%s, nb_days=%s)", organization, nb_days)
    back_url = build_absolute_uri(location=reverse(          # saas/renewals.py
        'saas_update_card', args=(organization,)))
    card = organization.retrieve_card()
    context = {
        'broker': get_broker(),
        'back_url': back_url,
        'profile': organization,
        'nb_expiration_days': nb_days,
        'last4': card.get('last4'),
        'exp_date': card.get('exp_date'),
    }
    send_notification('card_expires_soon',
      context=ExpireProfileNotificationSerializer().to_representation(context),
      **kwargs)


# We insure the method is only bounded once no matter how many times
# this module is loaded by using a dispatch_uid as advised here:
#   https://docs.djangoproject.com/en/dev/topics/signals/
@receiver(expires_soon, dispatch_uid="expires_soon_notice")
def expires_soon_notice(sender, subscription, nb_days,
                        **kwargs): # no request in kwargs
    """
    Subscription expires soon

    This notification is sent when a subscription is about to expire.

    **Tags: notification

    **Example

    .. code-block:: json

       {
          "event": "expires_soon",
          "broker": {
            "slug": "djaoapp",
            "printable_name": "DjaoApp",
            "full_name": "DjaoApp inc.",
            "nick_name": "DjaoApp",
            "picture": null,
            "type": "organization",
            "credentials": false,
            "created_at": "2024-01-01T00:00:00Z",
            "email": "djaoapp@localhost.localdomain",
            "phone": "415-555-5555",
            "street_address": "1 SaaS Road",
            "locality": "San Francisco",
            "region": "California",
            "postal_code": "94133",
            "country": "US",
            "default_timezone": "America/Los_Angeles",
            "is_provider": true,
            "is_bulk_buyer": false,
            "lang": "en",
            "extra": null
          },
          "back_url": "{{api_base_url}}",
          "profile": {
            "slug": "xia",
            "printable_name": "Xia",
            "full_name": "Xia Lee",
            "nick_name": "Xia",
            "picture": null,
            "type": "personal",
            "credentials": true,
            "created_at": "2024-01-01T00:00:00Z",
            "email": "xia@localhost.localdomain",
            "phone": "415-555-5556",
            "street_address": "1 SaaS Road",
            "locality": "San Francisco",
            "region": "California",
            "postal_code": "94133",
            "country": "US",
            "default_timezone": "America/Los_Angeles",
            "is_provider": false,
            "is_bulk_buyer": false,
            "lang": "en",
            "extra": null
          },
          "plan": {
            "slug": "premium",
            "title": "Premium"
          },
          "provider": {
            "slug": "djaoapp",
            "printable_name": "DjaoApp",
            "full_name": "DjaoApp inc.",
            "nick_name": "DjaoApp",
            "picture": null,
            "type": "organization",
            "credentials": false,
            "created_at": "2024-01-01T00:00:00Z",
            "email": "djaoapp@localhost.localdomain",
            "phone": "415-555-5555",
            "street_address": "1 SaaS Road",
            "locality": "San Francisco",
            "region": "California",
            "postal_code": "94133",
            "country": "US",
            "default_timezone": "America/Los_Angeles",
            "is_provider": true,
            "is_bulk_buyer": false,
            "lang": "en",
            "extra": null
          },
          "nb_expiration_days": 15
        }
    """
    LOGGER.debug("[signal] expires_soon_notice("\
                 " subscription=%s, nb_days=%s)", subscription, nb_days)
    back_url = build_absolute_uri(location=reverse(           # saas/renewals.py
        'saas_organization_cart', args=(
        subscription.organization,))) + ("?plan=%s" % subscription.plan)
    context = {
        'broker': get_broker(),
        'back_url': back_url,
        'profile': subscription.organization,
        'nb_expiration_days': nb_days,
        'plan': subscription.plan,
        'provider': subscription.plan.organization
    }
    send_notification('expires_soon',
        context=SubscriptionExpireNotificationSerializer().to_representation(
            context), **kwargs)


# We insure the method is only bounded once no matter how many times
# this module is loaded by using a dispatch_uid as advised here:
#   https://docs.djangoproject.com/en/dev/topics/signals/
@receiver(period_sales_report_created,
          dispatch_uid="period_sales_report_created_notice")
def period_sales_report_created_notice(sender, provider, dates, data, unit,
                                       scale=1, **kwargs): #no request in kwargs
    """
    Weekly sales report

    This notification contains the weekly sales results.

    **Tags: notification

    **Example

    .. code-block:: json

       {
          "event": "period_sales_report_created",
          "broker": {
            "slug": "djaoapp",
            "printable_name": "DjaoApp",
            "full_name": "DjaoApp inc.",
            "nick_name": "DjaoApp",
            "picture": null,
            "type": "organization",
            "credentials": false,
            "created_at": "2024-01-01T00:00:00Z",
            "email": "djaoapp@localhost.localdomain",
            "phone": "415-555-5555",
            "street_address": "1 SaaS Road",
            "locality": "San Francisco",
            "region": "California",
            "postal_code": "94133",
            "country": "US",
            "default_timezone": "America/Los_Angeles",
            "is_provider": true,
            "is_bulk_buyer": false,
            "lang": "en",
            "extra": null
          },
          "back_url": "{{api_base_url}}",
          "profile": {
            "slug": "xia",
            "printable_name": "Xia",
            "full_name": "Xia Lee",
            "nick_name": "Xia",
            "picture": null,
            "type": "personal",
            "credentials": true,
            "created_at": "2024-01-01T00:00:00Z",
            "email": "xia@localhost.localdomain",
            "phone": "415-555-5556",
            "street_address": "1 SaaS Road",
            "locality": "San Francisco",
            "region": "California",
            "postal_code": "94133",
            "country": "US",
            "default_timezone": "America/Los_Angeles",
            "is_provider": false,
            "is_bulk_buyer": false,
            "lang": "en",
            "extra": null
          },
          "scale": 1,
          "unit": "usd",
          "title": "2024-01-07T00:00:00Z",
          "results": []
        }
    """
    #pylint:disable=too-many-arguments
    prev_week, _unused = dates
    last_sunday = prev_week[-1]
    date = last_sunday.strftime("%A %b %d, %Y")
    # XXX using the provider in templates is incorrect. "Any questions
    # or comments..." should show DjaoDjin support email address.
    back_url = build_absolute_uri() # saas/.../report_weekly_revenue.py
    context = {
        'back_url': back_url,
        'broker': get_broker(),
        'profile': provider,
        'scale': scale,
        'unit': unit,
        'title': date,
        'results': data
    }
    send_notification('period_sales_report_created',
        context=AggregatedSalesNotificationSerializer().to_representation(
            context), **kwargs)


@receiver(post_save, sender=get_user_model())
def on_user_post_save(sender, instance, created, raw, **kwargs):
    #pylint:disable=unused-argument
    if created and instance.is_superuser:
        get_broker().add_manager(instance)
