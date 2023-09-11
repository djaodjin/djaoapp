# Copyright (c) 2023, DjaoDjin inc.
# see LICENSE
#pylint:disable=invalid-name,too-many-lines
import logging

from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver
from multitier.thread_locals import get_current_site
from rules.utils import get_current_app # XXX for `welcome_email`
from saas import settings as saas_settings
from saas.models import CartItem, get_broker
from saas.signals import (card_expires_soon, charge_updated,
    claim_code_generated, card_updated, expires_soon, order_executed,
    profile_updated, processor_setup_error,
    renewal_charge_failed, role_grant_created, role_request_created,
    role_grant_accepted, subscription_grant_accepted,
    subscription_grant_created, subscription_request_accepted,
    subscription_request_created, weekly_sales_report_created)
from signup.helpers import has_invalid_password
from signup.models import Contact
from signup.signals import (user_registered, user_activated,
    user_reset_password, user_verification, user_mfa_code)
from signup.utils import printable_name as user_printable_name
from djaoapp.signals import contact_requested

from ..compat import gettext_lazy as _, reverse, six
from .serializers import (ContactUsNotificationSerializer,
    UserNotificationSerializer, ExpireUserNotificationSerializer,
    OneTimeCodeNotificationSerializer,
    ExpireProfileNotificationSerializer,
    SubscriptionExpireNotificationSerializer,
    ChangeProfileNotificationSerializer, AggregatedSalesNotificationSerializer,
    ChargeNotificationSerializer,
    RenewalFailedNotificationSerializer, InvoiceNotificationSerializer,
    ClaimNotificationSerializer, ProcessorSetupNotificationSerializer,
    RoleRequestNotificationSerializer, RoleGrantNotificationSerializer,
    SubscriptionAcceptedNotificationSerializer,
    SubscriptionCreatedNotificationSerializer)
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
@receiver(contact_requested, dispatch_uid="contact_requested_notice")
def contact_requested_notice(sender, provider, user, reason, **kwargs):
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
            "created_at": "2022-01-01T00:00:00Z",
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
            "created_at": "2022-01-01T00:00:00Z",
            "last_login": "2022-01-01T00:00:00Z",
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
    LOGGER.debug("[signal] contact_requested_notice(provider=%s, user=%s)",
        provider, user)
    site = get_current_site()
    back_url = site.as_absolute_uri()
    context = {
        'broker': broker,
        'back_url': back_url,
        'provider': provider,
        'originated_by': user,
        'detail': reason
    }
    send_notification('user_contact',
        context=ContactUsNotificationSerializer().to_representation(context),
        site=site)


# We insure the method is only bounded once no matter how many times
# this module is loaded by using a dispatch_uid as advised here:
#   https://docs.djangoproject.com/en/dev/topics/signals/
@receiver(user_registered, dispatch_uid="user_registered_notice")
def user_registered_notice(sender, user, **kwargs):
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
            "created_at": "2022-01-01T00:00:00Z",
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
            "created_at": "2022-01-01T00:00:00Z",
            "last_login": "2022-01-01T00:00:00Z",
            "email": "xia@localhost.localdomain",
            "phone": "415-555-5556",
            "lang": "en",
            "extra": null
          }
        }
    """
    LOGGER.debug("[signal] user_registered_notice(user=%s)", user)
    site = get_current_site()
    app = get_current_app()
    context = {
        'broker': get_broker(),
        'back_url': site.as_absolute_uri(),
        'user': user
    }
    send_notification('user_registered',
        context=UserNotificationSerializer().to_representation(context),
        site=site)
    if hasattr(app, 'welcome_email') and app.welcome_email:
        send_notification('user_welcome',
            context=UserNotificationSerializer().to_representation(context),
            site=site)


# We insure the method is only bounded once no matter how many times
# this module is loaded by using a dispatch_uid as advised here:
#   https://docs.djangoproject.com/en/dev/topics/signals/
@receiver(user_activated, dispatch_uid="user_activated_notice")
def user_activated_notice(sender, user, verification_key, request, **kwargs):
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
            "created_at": "2022-01-01T00:00:00Z",
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
            "created_at": "2022-01-01T00:00:00Z",
            "last_login": "2022-01-01T00:00:00Z",
            "email": "xia@localhost.localdomain",
            "phone": "415-555-5556",
            "lang": "en",
            "extra": null
          }
        }
    """
    LOGGER.debug("[signal] user_activated_notice(user=%s, verification_key=%s)",
        user, verification_key)
    site = get_current_site()
    context = {
        'broker': get_broker(),
        'back_url': site.as_absolute_uri(),
        'user': user,
    }
    send_notification('user_activated',
        context=UserNotificationSerializer().to_representation(context),
        site=site)


# We insure the method is only bounded once no matter how many times
# this module is loaded by using a dispatch_uid as advised here:
#   https://docs.djangoproject.com/en/dev/topics/signals/
@receiver(user_verification, dispatch_uid="user_verification_notice")
def user_verification_notice(
        sender, user, request, back_url, expiration_days, **kwargs):
    """
    Verification of e-mail address

    This notification is sent to verify an e-mail address of a user.

    **Tags: notification

    **Example

    .. code-block:: json

        {
          "event": "user_verification",
          "broker": {
            "slug": "djaoapp",
            "printable_name": "DjaoApp",
            "full_name": "DjaoApp inc.",
            "nick_name": "DjaoApp",
            "picture": null,
            "type": "organization",
            "credentials": false,
            "created_at": "2022-01-01T00:00:00Z",
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
          "back_url": "{{api_base_url}}activate/abcdef123/",
          "user": {
            "slug": "xia",
            "username": "xia",
            "printable_name": "Xia",
            "full_name": "Xia Lee",
            "nick_name": "Xia",
            "picture": null,
            "type": "personal",
            "credentials": true,
            "created_at": "2022-01-01T00:00:00Z",
            "last_login": "2022-01-01T00:00:00Z",
            "email": "xia@localhost.localdomain",
            "phone": "415-555-5556",
            "lang": "en",
            "extra": null
          },
          "nb_expiration_days": 2
        }
    """
    LOGGER.debug("[signal] user_verification_notice(user=%s, back_url=%s,"\
        " expiration_days=%s)", user, back_url, expiration_days)
    site = get_current_site()
    context = {
        'broker': get_broker(),
        'back_url': back_url,
        'user': user,
        'nb_expiration_days': expiration_days
    }
    send_notification('user_verification',
        context=ExpireUserNotificationSerializer().to_representation(context),
        site=site)


# We insure the method is only bounded once no matter how many times
# this module is loaded by using a dispatch_uid as advised here:
#   https://docs.djangoproject.com/en/dev/topics/signals/
@receiver(user_reset_password, dispatch_uid="user_reset_password_notice")
def user_reset_password_notice(sender, user, request, back_url,
                               expiration_days, **kwargs):
    """
    Password reset

    This notification is sent to a user that has requested
    to reset their password through a "forgot password?" link.

    **Tags: notification

    **Example

    .. code-block:: json

        {
          "event": "user_verification",
          "broker": {
            "slug": "djaoapp",
            "printable_name": "DjaoApp",
            "full_name": "DjaoApp inc.",
            "nick_name": "DjaoApp",
            "picture": null,
            "type": "organization",
            "credentials": false,
            "created_at": "2022-01-01T00:00:00Z",
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
          "back_url": "{{api_base_url}}activate/abcdef123/",
          "user": {
            "slug": "xia",
            "username": "xia",
            "printable_name": "Xia",
            "full_name": "Xia Lee",
            "nick_name": "Xia",
            "picture": null,
            "type": "personal",
            "credentials": true,
            "created_at": "2022-01-01T00:00:00Z",
            "last_login": "2022-01-01T00:00:00Z",
            "email": "xia@localhost.localdomain",
            "phone": "415-555-5556",
            "lang": "en",
            "extra": null
          },
          "nb_expiration_days": 2
        }
    """
    LOGGER.debug("[signal] user_reset_password_notice(user=%s, back_url=%s,"\
        " expiration_days=%s)", user, back_url, expiration_days)
    site = get_current_site()
    context = {
        'broker': get_broker(),
        'back_url': back_url,
        'user': user,
        'nb_expiration_days': expiration_days,
    }
    send_notification('user_reset_password',
        context=ExpireUserNotificationSerializer().to_representation(context),
        site=site)


@receiver(user_mfa_code, dispatch_uid="user_mfa_code_notice")
def user_mfa_code_notice(sender, user, code, request, **kwargs):
    """
    One-time code generated

    A one-time code was generated for Multi-factor authentication (MFA).

    **Tags: notification

    **Example

    .. code-block:: json

        {
          "event": "user_mfa_code",
          "broker": {
            "slug": "djaoapp",
            "printable_name": "DjaoApp",
            "full_name": "DjaoApp inc.",
            "nick_name": "DjaoApp",
            "picture": null,
            "type": "organization",
            "credentials": false,
            "created_at": "2022-01-01T00:00:00Z",
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
          "back_url": "{{api_base_url}}activate/abcdef123/",
          "user": {
            "slug": "xia",
            "username": "xia",
            "printable_name": "Xia",
            "full_name": "Xia Lee",
            "nick_name": "Xia",
            "picture": null,
            "type": "personal",
            "credentials": true,
            "created_at": "2022-01-01T00:00:00Z",
            "last_login": "2022-01-01T00:00:00Z",
            "email": "xia@localhost.localdomain",
            "phone": "415-555-5556",
            "lang": "en",
            "extra": null
          },
          "nb_expiration_days": 2,
          "code": "1234"
        }
    """
    contact = user
    LOGGER.debug("[signal] user_mfa_code_notice(user=%s, code=%s,"\
        " request=%s)", contact.user, code, request)
    site = get_current_site()
    back_url = site.as_absolute_uri(reverse('login'))
    context = {
        'broker': get_broker(),
        'user': contact.user,
        'nb_expiration_days': 1, # XXX
        'code': code,
        'back_url': back_url
    }
    send_notification('user_mfa_code',
        context=OneTimeCodeNotificationSerializer().to_representation(context),
        site=site)


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
            "created_at": "2022-01-01T00:00:00Z",
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
            "created_at": "2022-01-01T00:00:00Z",
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
            "created_at": "2022-01-01T00:00:00Z",
            "last_login": "2022-01-01T00:00:00Z",
            "email": "xia@localhost.localdomain",
            "phone": "415-555-5556",
            "lang": "en",
            "extra": null
          },
          "charge_items": [{
            "invoiced": {
              "created_at": "2022-01-01T00:00:00Z",
              "description": "subscription to premium",
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
            "created_at": "2022-01-01T00:00:00Z",
            "amount": 11900,
            "unit": "usd",
            "readable_amount": "$119.00",
            "description": "subscription to premium",
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
            "created_at": "2022-01-01T00:00:00Z",
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
        site = get_current_site()
        back_url = site.as_absolute_uri(reverse('saas_charge_receipt', args=(
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
            'provider': charge.broker,
        }
        if charge.refunded.exists():
            total_refunded = charge.invoiced_total_after_refund
            context.update({
                'charge_total': {
                    'amount': total_refunded.amount,
                    'unit': total_refunded.unit
                }})
        if user and charge.created_by != user:
            context.update({'originated_by': user})
        else:
            context.update({'originated_by': None})
        send_notification('charge_updated',
            context=ChargeNotificationSerializer().to_representation(context),
            site=site)


@receiver(card_updated, dispatch_uid="card_updated_notice")
def card_updated_notice(sender, organization, user, old_card, new_card,
                        **kwargs):
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
            "created_at": "2022-01-01T00:00:00Z",
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
            "created_at": "2022-01-01T00:00:00Z",
            "last_login": "2022-01-01T00:00:00Z",
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
            "created_at": "2022-01-01T00:00:00Z",
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
              "pre": "07/2022",
              "post": "07/2023"
            }
          }
        }
    """
    LOGGER.debug("[signal] card_updated_notice(organization=%s, user=%s,"\
        "old_card=%s, new_card=%s)", organization, user, old_card, new_card)
    site = get_current_site()
    context = {
        'broker': get_broker(),
        'back_url': site.as_absolute_uri(
            reverse('saas_update_card', args=(organization,))),
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
      site=site)


# We insure the method is only bounded once no matter how many times
# this module is loaded by using a dispatch_uid as advised here:
#   https://docs.djangoproject.com/en/dev/topics/signals/
@receiver(order_executed, dispatch_uid="order_executed_notice")
def order_executed_notice(sender, invoiced_items, user, **kwargs):
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
            "created_at": "2022-01-01T00:00:00Z",
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
            "created_at": "2022-01-01T00:00:00Z",
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
            "created_at": "2022-01-01T00:00:00Z",
            "last_login": "2022-01-01T00:00:00Z",
            "email": "xia@localhost.localdomain",
            "phone": "415-555-5556",
            "lang": "en",
            "extra": null
          },
          "invoiced_items": [{
              "created_at": "2022-01-01T00:00:00Z",
              "description": "subscription to premium",
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
            "created_at": "2022-01-01T00:00:00Z",
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
    site = get_current_site()
    provider = broker # XXX
    context = {
        'broker': broker,
        'back_url': site.as_absolute_uri(),
        'originated_by': user,
        'profile': organization,
        'provider': provider,
        'invoiced_items': invoiced_items,
    }
    send_notification('order_executed',
        context=InvoiceNotificationSerializer().to_representation(context),
        site=site)


# We insure the method is only bounded once no matter how many times
# this module is loaded by using a dispatch_uid as advised here:
#   https://docs.djangoproject.com/en/dev/topics/signals/
@receiver(renewal_charge_failed, dispatch_uid="renewal_charge_failed_notice")
def renewal_charge_failed_notice(sender, invoiced_items, total_price,
                                 final_notice, **kwargs):
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
            "created_at": "2022-01-01T00:00:00Z",
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
            "created_at": "2022-01-01T00:00:00Z",
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
              "created_at": "2022-01-01T00:00:00Z",
              "description": "subscription to premium",
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
            "created_at": "2022-01-01T00:00:00Z",
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
    site = get_current_site()
    back_url = site.as_absolute_uri(
        reverse('saas_organization_cart', args=(organization,)))
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
      site=site)


@receiver(claim_code_generated, dispatch_uid="claim_code_generated_notice")
def claim_code_generated_notice(sender, subscriber, claim_code, user, **kwargs):
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
            "created_at": "2022-01-01T00:00:00Z",
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
            "created_at": "2022-01-01T00:00:00Z",
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
            "created_at": "2022-01-01T00:00:00Z",
            "last_login": "2022-01-01T00:00:00Z",
            "email": "xia@localhost.localdomain",
            "phone": "415-555-5556",
            "lang": "en",
            "extra": null
          },
          "cart_items": [{
            "created_at": "2022-01-01T00:00:00Z",
            "user": {
              "slug": "emilie",
              "username": "emilie",
              "printable_name": "Emilie",
              "full_name": "Emilie Jolie",
              "nick_name": "Emilie",
              "picture": null,
              "type": "user",
              "credentials": false,
              "created_at": "2022-01-01T00:00:00Z",
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
            "created_at": "2022-01-01T00:00:00Z",
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
    site = get_current_site()
    back_url = (site.as_absolute_uri(reverse('saas_cart')) +
        '?code=%s' % claim_code)
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
        site=site)


@receiver(profile_updated, dispatch_uid="profile_updated_notice")
def profile_updated_notice(sender, organization, changes, user, **kwargs):
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
            "created_at": "2022-01-01T00:00:00Z",
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
            "created_at": "2022-01-01T00:00:00Z",
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
            "created_at": "2022-01-01T00:00:00Z",
            "last_login": "2022-01-01T00:00:00Z",
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
    site = get_current_site()
    # Some changes are still typed by the model field (ex: Country).
    # We want to make sure we have a JSON-serializable `changes` dict here.
    for change in six.itervalues(changes):
        change.update({
            'pre': str(change.get('pre')),
            'post': str(change.get('post'))
        })
    context={
        'broker': broker,
        'back_url': site.as_absolute_uri(
            reverse('saas_organization_profile', args=(organization,))),
        'originated_by': user,
        'profile': organization,
        'changes': changes
    }
    send_notification('profile_updated',
      context=ChangeProfileNotificationSerializer().to_representation(context),
      site=site)


# We insure the method is only bounded once no matter how many times
# this module is loaded by using a dispatch_uid as advised here:
#   https://docs.djangoproject.com/en/dev/topics/signals/
@receiver(processor_setup_error, dispatch_uid="processor_setup_error_notice")
def processor_setup_error_notice(sender, provider, error_message, customer,
                                 **kwargs):
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
            "created_at": "2022-01-01T00:00:00Z",
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
            "created_at": "2022-01-01T00:00:00Z",
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
            "created_at": "2022-01-01T00:00:00Z",
            "last_login": "2022-01-01T00:00:00Z",
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
            "created_at": "2022-01-01T00:00:00Z",
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
    site = get_current_site()
    context = {
        'broker': get_broker(),
        'back_url': site.as_absolute_uri(
            reverse('saas_update_bank', args=(provider,))),
        'profile': customer,
        'provider': provider,
        'detail': error_message,
    }
    request_user = kwargs.get('request_user', None)
    context.update({'originated_by': request_user if request_user else None})
    send_notification('processor_setup_error',
      context=ProcessorSetupNotificationSerializer().to_representation(context),
      site=site)


# We insure the method is only bounded once no matter how many times
# this module is loaded by using a dispatch_uid as advised here:
#   https://docs.djangoproject.com/en/dev/topics/signals/
@receiver(role_grant_created, dispatch_uid="role_grant_created_notice")
def role_grant_created_notice(sender, role, reason=None, **kwargs):
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
            "created_at": "2022-01-01T00:00:00Z",
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
            "created_at": "2022-01-01T00:00:00Z",
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
            "created_at": "2022-01-01T00:00:00Z",
            "last_login": "2022-01-01T00:00:00Z",
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
            "created_at": "2022-01-01T00:00:00Z",
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
    site = get_current_site()
    back_url = reverse('organization_app', args=(organization,))
    if role.grant_key:
        back_url = reverse('saas_role_grant_accept',
            args=(role.grant_key,))
    if has_invalid_password(user):
        reason = _("You have been invited to create an account"\
            " to join %(organization)s.") % {
            'organization': role.organization.printable_name}
        Contact.objects.prepare_email_verification(
            user.email, user=user, reason=reason)
    context = {
        'broker': get_broker(),
        'back_url': site.as_absolute_uri(back_url),
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
        site=site)


# We insure the method is only bounded once no matter how many times
# this module is loaded by using a dispatch_uid as advised here:
#   https://docs.djangoproject.com/en/dev/topics/signals/
@receiver(role_request_created, dispatch_uid="role_request_created_notice")
def role_request_created_notice(sender, role, reason=None, **kwargs):
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
            "created_at": "2022-01-01T00:00:00Z",
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
            "created_at": "2022-01-01T00:00:00Z",
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
            "created_at": "2022-01-01T00:00:00Z",
            "last_login": "2022-01-01T00:00:00Z",
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
            "created_at": "2022-01-01T00:00:00Z",
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
    site = get_current_site()
    LOGGER.debug("[signal] role_request_created_notice("\
        "organization=%s, user=%s, reason=%s)",
        organization, user, reason)
    context = {
        'broker': get_broker(),
        'back_url': site.as_absolute_uri(
            reverse('saas_role_list', args=(organization,))),
        'profile': organization,
        'detail': reason if reason is not None else "",
        'user': user
    }
    request_user = kwargs.get('request_user', None)
    context.update({'originated_by': request_user if request_user else None})
    send_notification('role_request_created',
        context=RoleRequestNotificationSerializer().to_representation(context),
        site=site)


# We insure the method is only bounded once no matter how many times
# this module is loaded by using a dispatch_uid as advised here:
#   https://docs.djangoproject.com/en/dev/topics/signals/
@receiver(role_grant_accepted, dispatch_uid="role_grant_accepted_notice")
def role_grant_accepted_notice(sender, role, grant_key, request=None, **kwargs):
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
            "created_at": "2022-01-01T00:00:00Z",
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
            "created_at": "2022-01-01T00:00:00Z",
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
            "created_at": "2022-01-01T00:00:00Z",
            "last_login": "2022-01-01T00:00:00Z",
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
            "created_at": "2022-01-01T00:00:00Z",
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
    originated_by = request.user if request else None
    site = get_current_site()
    context={
        'broker': get_broker(),
        'back_url': site.as_absolute_uri(reverse('saas_role_detail',
            args=(role.organization, role.role_description))),
        'profile': role.organization,
        'role_description': {
            'slug': role.role_description.slug,
            'title': role.role_description.title,
        },
        'user': originated_by,
        'detail': "",
    }
    request_user = kwargs.get('request_user', None)
    context.update({'originated_by': request_user if request_user else None})
    send_notification('role_grant_accepted',
        context=RoleGrantNotificationSerializer().to_representation(context),
        site=site)


# We insure the method is only bounded once no matter how many times
# this module is loaded by using a dispatch_uid as advised here:
#   https://docs.djangoproject.com/en/dev/topics/signals/
@receiver(subscription_grant_accepted,
          dispatch_uid="subscription_grant_accepted_notice")
def subscription_grant_accepted_notice(sender, subscription, grant_key,
                                       request=None, **kwargs):
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
            "created_at": "2022-01-01T00:00:00Z",
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
            "created_at": "2022-01-01T00:00:00Z",
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
            "created_at": "2022-01-01T00:00:00Z",
            "last_login": "2022-01-01T00:00:00Z",
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
    originated_by = request.user if request else None
    LOGGER.debug("[signal] subscribe_grant_accepted_notice("\
        " subscription=%s, grant_key=%s)", subscription, grant_key)
    site = get_current_site()
    context = {
        'broker': get_broker(),
        'back_url': site.as_absolute_uri(reverse('organization_app',
            args=(provider,))),
        'profile': subscription.plan.organization,
        'plan': subscription.plan,
        'subscriber': subscription.organization,
        'originated_by': originated_by
    }
    send_notification('subscription_grant_accepted',
        context=SubscriptionAcceptedNotificationSerializer().to_representation(
        context),
        site=site)


# We insure the method is only bounded once no matter how many times
# this module is loaded by using a dispatch_uid as advised here:
#   https://docs.djangoproject.com/en/dev/topics/signals/
@receiver(subscription_grant_created,
          dispatch_uid="subscription_grant_created_notice")
def subscription_grant_created_notice(sender, subscription, reason=None,
                                      invite=False, request=None, **kwargs):
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
            "created_at": "2022-01-01T00:00:00Z",
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
            "created_at": "2022-01-01T00:00:00Z",
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
            "created_at": "2022-01-01T00:00:00Z",
            "last_login": "2022-01-01T00:00:00Z",
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
        origiinated_by = request.user if request else None
        organization = subscription.organization
        site = get_current_site()
        back_url = site.as_absolute_uri(reverse('subscription_grant_accept',
            args=(organization, subscription.grant_key,)))
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
            'originated_by': origiinated_by
        }
        send_notification('subscription_grant_created',
            context=SubscriptionCreatedNotificationSerializer(
            ).to_representation(context),
            site=site)


# We insure the method is only bounded once no matter how many times
# this module is loaded by using a dispatch_uid as advised here:
#   https://docs.djangoproject.com/en/dev/topics/signals/
@receiver(subscription_request_accepted,
          dispatch_uid="subscription_request_accepted_notice")
def subscription_request_accepted_notice(sender, subscription, request_key,
                                         request=None, **kwargs):
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
            "created_at": "2022-01-01T00:00:00Z",
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
            "created_at": "2022-01-01T00:00:00Z",
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
            "created_at": "2022-01-01T00:00:00Z",
            "last_login": "2022-01-01T00:00:00Z",
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
    site = get_current_site()
    originated_by = request.user if request else None
    context = {
        'broker': get_broker(),
        'back_url': site.as_absolute_uri(reverse('organization_app',
            args=(subscriber,))),
        'profile': subscriber,
        'plan': subscription.plan,
        'provider': subscription.plan.organization,
        'originated_by': originated_by
    }
    send_notification('subscription_request_accepted',
        context=SubscriptionAcceptedNotificationSerializer().to_representation(
        context),
        site=site)


# We insure the method is only bounded once no matter how many times
# this module is loaded by using a dispatch_uid as advised here:
#   https://docs.djangoproject.com/en/dev/topics/signals/
@receiver(subscription_request_created,
          dispatch_uid="subscription_request_created_notice")
def subscription_request_created_notice(sender, subscription, reason=None,
                                        request=None, **kwargs):
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
            "created_at": "2022-01-01T00:00:00Z",
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
            "created_at": "2022-01-01T00:00:00Z",
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
            "created_at": "2022-01-01T00:00:00Z",
            "last_login": "2022-01-01T00:00:00Z",
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
        originated_by = request.user if request else None
        organization = subscription.organization
        site = get_current_site()
        LOGGER.debug("[signal] subscribe_req_created_notice("\
                     " subscription=%s, reason=%s)", subscription, reason)
        context = {
            'broker': get_broker(),
            'back_url': site.as_absolute_uri(reverse(
                'subscription_request_accept', args=(
                    organization, subscription.request_key,))),
            'profile': subscription.plan.organization,
            'plan': subscription.plan,
            'subscriber': organization,
            'detail': reason if reason is not None else "",
            'originated_by': originated_by
        }
        send_notification('subscription_request_created',
            context=SubscriptionCreatedNotificationSerializer(
            ).to_representation(context),
            site=site)


# We insure the method is only bounded once no matter how many times
# this module is loaded by using a dispatch_uid as advised here:
#   https://docs.djangoproject.com/en/dev/topics/signals/
@receiver(card_expires_soon, dispatch_uid="card_expires_soon_notice")
def card_expires_soon_notice(sender, organization, nb_days, **kwargs):
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
            "created_at": "2022-01-01T00:00:00Z",
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
            "created_at": "2022-01-01T00:00:00Z",
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
    site = get_current_site()
    back_url = site.as_absolute_uri(reverse('saas_update_card',
        args=(organization,)))
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
      site=site)


# We insure the method is only bounded once no matter how many times
# this module is loaded by using a dispatch_uid as advised here:
#   https://docs.djangoproject.com/en/dev/topics/signals/
@receiver(expires_soon, dispatch_uid="expires_soon_notice")
def expires_soon_notice(sender, subscription, nb_days, **kwargs):
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
            "created_at": "2022-01-01T00:00:00Z",
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
            "created_at": "2022-01-01T00:00:00Z",
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
            "created_at": "2022-01-01T00:00:00Z",
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
    site = get_current_site()
    back_url = "%s?plan=%s" % (site.as_absolute_uri(
        reverse('saas_organization_cart',
            args=(subscription.organization,))), subscription.plan)
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
            context),
        site=site)


# We insure the method is only bounded once no matter how many times
# this module is loaded by using a dispatch_uid as advised here:
#   https://docs.djangoproject.com/en/dev/topics/signals/
@receiver(weekly_sales_report_created,
          dispatch_uid="weekly_sales_report_created_notice")
def weekly_sales_report_created_notice(sender, provider, dates, data, **kwargs):
    """
    Weekly sales report

    This notification contains the weekly sales results.

    **Tags: notification

    **Example

    .. code-block:: json

       {
          "event": "weekly_sales_report_created",
          "broker": {
            "slug": "djaoapp",
            "printable_name": "DjaoApp",
            "full_name": "DjaoApp inc.",
            "nick_name": "DjaoApp",
            "picture": null,
            "type": "organization",
            "credentials": false,
            "created_at": "2022-01-01T00:00:00Z",
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
            "created_at": "2022-01-01T00:00:00Z",
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
          "table": [],
          "date": "2022-01-07T00:00:00Z"
        }
    """
    prev_week, notused = dates #pylint:disable=unused-variable
    last_sunday = prev_week[-1]
    date = last_sunday.strftime("%A %b %d, %Y")
    # XXX using the provider in templates is incorrect. "Any questions
    # or comments..." should show DjaoDjin support email address.
    site = get_current_site()
    context = {
        'back_url': site.as_absolute_uri(),
        'broker': get_broker(),
        'profile': provider,
        'table': data,
        'date': date
    }
    send_notification('weekly_sales_report_created',
        context=AggregatedSalesNotificationSerializer().to_representation(
            context),
        site=site)


@receiver(post_save, sender=get_user_model())
def on_user_post_save(sender, instance, created, raw, **kwargs):
    #pylint:disable=unused-argument
    if created and instance.is_superuser:
        get_broker().add_manager(instance)
