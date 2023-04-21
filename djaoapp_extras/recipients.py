# Copyright (c) 2023, DjaoDjin inc.
# see LICENSE
from __future__ import unicode_literals

import logging

from django.conf import settings
from multitier.thread_locals import get_current_site
from saas import settings as saas_settings
from saas.models import get_broker
from saas.utils import get_organization_model
from signup.settings import NOTIFICATIONS_OPT_OUT

LOGGER = logging.getLogger(__name__)
SEND_EMAIL = settings.SEND_EMAIL


def _notified_managers(organization, notification_slug, originated_by=None):
    managers = organization.with_role(saas_settings.MANAGER)
    if originated_by:
        managers = managers.exclude(email=originated_by.get('email', ""))
    # checking whether those users are subscribed to the notification
    if NOTIFICATIONS_OPT_OUT:
        filtered = managers.exclude(notifications__slug=notification_slug)
    else:
        filtered = managers.filter(notifications__slug=notification_slug)
    return [notified.email for notified in filtered if notified.email]


def notified_recipients(notification_slug, context, broker=None, site=None):
    """
    Returns the organization email or the managers email if the organization
    does not have an e-mail set.
    """
    recipients = []
    bcc = []
    if not broker:
        broker = get_broker()
    if not site:
        site = get_current_site()
    originated_by = context.get('originated_by')
    if not originated_by:
        originated_by = {}
    reply_to = originated_by.get('email')
    if not reply_to and broker.email and broker.email != site.get_from_email():
        reply_to = broker.email

    # Notify a single user because there is a verification_key
    # in the e-mail body.
    if notification_slug in (
            'user_verification',
            'user_reset_password',
            'user_mfa_code',
            'user_welcome',
            'role_grant_created',):
        user = context.get('user')
        if user:
            user_email = user.get('email')
            if user_email:
                recipients = [user_email]

    # Notify the profile primary contact e-mail address
    elif notification_slug in (
            'claim_code_generated',
            'subscription_grant_created',
            'subscription_request_accepted',
            'role_request_created',
            'role_grant_accepted',
            'profile_updated',
            'order_executed',
            'card_updated',
            'charge_receipt',
            'card_expires_soon',
            'expires_soon'):
        organization_email = context.get('profile', {}).get('email', "")
        if organization_email:
            recipients = [organization_email]
        if notification_slug in (
            'subscription_request_accepted',
            'role_request_created',
            'role_grant_accepted',
            'profile_updated',
            'order_executed',
            'card_updated',
            'charge_receipt',
            'card_expires_soon',
            'expires_soon'):
            organization = get_organization_model().objects.get(
                slug=context.get('profile', {}).get('slug'))
            bcc = _notified_managers(organization, notification_slug,
                    originated_by=originated_by)
            # We also notify the provider managers that are interested
            # in these events.
            if notification_slug in (
                'subscription_request_accepted',):
                provider = get_organization_model().objects.get(
                    slug=context.get('provider', {}).get('slug'))
                bcc += _notified_managers(provider, notification_slug,
                    originated_by=originated_by)
            # We also notify the broker managers that are interested
            # in these events.
            elif notification_slug in (
                    'profile_updated',
                    'order_executed',
                    'card_updated',
                    'charge_receipt',
                    'card_expires_soon',
                    'expires_soon'):
                bcc += _notified_managers(broker, notification_slug,
                    originated_by=originated_by)

    # Notify the provider primary contact e-mail address
    elif notification_slug in (
            'subscription_grant_accepted',
            'subscription_request_created'):
        provider_email = context.get(
            'plan', {}).get('organization', {}).get('email', "")
        if provider_email:
            recipients = [provider_email]
        provider = get_organization_model().objects.get(
            slug=context.get('profile', {}).get('slug'))
        subscriber = get_organization_model().objects.get(
            slug=context.get('subscriber', {}).get('slug'))
        bcc = (_notified_managers(provider, notification_slug,
                originated_by=originated_by) +
               _notified_managers(subscriber, notification_slug,
                originated_by=originated_by))

    elif notification_slug in (
            'user_contact',
            'processor_setup_error',
            'user_registered',
            'user_activated',
            'weekly_sales_report_created'):
        # We are hanlding `recipients` a bit differently here because contact
        # requests are usually meant to be sent to a ticketing system.
        recipients = [broker.email]
        if notification_slug in (
                'processor_setup_error',
                'user_registered',
                'user_activated',
                'weekly_sales_report_created',):
            bcc = _notified_managers(broker, notification_slug)

    return recipients, bcc, reply_to
