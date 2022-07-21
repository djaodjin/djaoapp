# Copyright (c) 2022, DjaoDjin inc.
# see LICENSE
from __future__ import unicode_literals

import json, logging, smtplib

from deployutils.crypt import JSONEncoder
from django.conf import settings
from django.core.mail import get_connection as get_connection_base
from django.db import models
from django.utils import translation
from extended_templates.backends import get_email_backend
from multitier.thread_locals import get_current_site
from rules.models import BaseApp
from saas import settings as saas_settings
from saas.models import get_broker
from saas.utils import get_organization_model
from signup.models import Contact
from signup.settings import NOTIFICATIONS_OPT_OUT

from .compat import python_2_unicode_compatible, gettext_lazy as _

LOGGER = logging.getLogger(__name__)
SEND_EMAIL = settings.SEND_EMAIL


@python_2_unicode_compatible
class App(BaseApp):

    show_edit_tools = models.NullBooleanField(default=True)

    class Meta:
        db_table = 'rules_app'

    def __str__(self):
        return str(self.slug)


    def send_notification(self, event_name, context=None, site=None):
        """
        Sends a notification e-mail using the current site connection,
        defaulting to sending an e-mail to broker profile managers
        if there is any problem with the connection settings.
        """
        #pylint:disable=too-many-arguments
        context.update({"event": event_name})
        template = 'notification/%s.eml' % event_name
        if event_name in ('role_grant_created',):
            role_description_slug = context.get(
                'role_description', {}).get('slug')
            if role_description_slug:
                template = [
                    "notification/%s_role_grant_created.eml" %
                    role_description_slug] + [template]
        if not site:
            site = get_current_site()

        recipients, bcc, reply_to = _notified_recipients(
            event_name, context)
        LOGGER.debug("%s.send_notification("\
            "recipients=%s, reply_to='%s', bcc=%s"\
            "event=%s)", self, recipients, reply_to, bcc,
            json.dumps(context, indent=2, cls=JSONEncoder))
        lang_code = None
        contact = Contact.objects.filter(
            email__in=recipients).order_by('email').first()
        if contact:
            lang_code = contact.lang

        if SEND_EMAIL:
            try:
                with translation.override(lang_code):
                    get_email_backend(
                        connection=site.get_email_connection()).send(
                        from_email=site.get_from_email(),
                        recipients=recipients,
                        reply_to=reply_to,
                        bcc=bcc,
                        template=template,
                        context=context)
            except smtplib.SMTPException as err:
                LOGGER.warning("[signal] problem sending email from %s"\
                    " on connection for %s. %s",
                    site.get_from_email(), site, err)
                context.update({'errors': [_("There was an error sending"\
        " the following email to %(recipients)s. This is most likely due to"\
        " a misconfiguration of the e-mail notifications whitelabel settings"\
        " for your site %(site)s.") % {
            'recipients': recipients, 'site': site.as_absolute_uri()}]})
                #pylint:disable=unused-variable
                notified_on_errors, unused1, unused2 = _notified_recipients(
                    '', {
                    'broker': get_organization_model().objects.using(
                        site._state.db).get(pk=site.account_id)})
                if notified_on_errors:
                    get_email_backend(
                        connection=get_connection_base(fail_silently=True)).send(
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipients=notified_on_errors,
                        template=template,
                        context=context)
            except Exception as err:
                # Something went horribly wrong, like the email password was not
                # decrypted correctly. We want to notifiy the operations team
                # but the end user shouldn't see a 500 error as a result
                # of notifications sent in the HTTP request pipeline.
                LOGGER.exception(err)


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


def _notified_recipients(notification_slug, context, broker=None, site=None):
    """
    Returns the organization email or the managers email if the organization
    does not have an e-mail set.
    """
    recipients = []
    bcc = []
    reply_to = None
    if not broker:
        broker = get_broker()
    if not site:
        site = get_current_site()
    if broker.email and broker.email != site.get_from_email():
        reply_to = broker.email
    originated_by = context.get('originated_by')
    if not originated_by:
        originated_by = {}

    if notification_slug in (
            'user_verification',
            'user_reset_password',
            'user_mfa_code',
            'user_welcome',
            ):
        user_email = context.get('user', {}).get('email', "")
        if user_email:
            recipients = [user_email]

    elif notification_slug in (
            'user_contact',):
        # We are hanlding `recipients` a bit differently here because contact
        # requests are usually meant to be sent to a ticketing system.
        recipients = [broker.email]
        user_email = originated_by.get('email', "")
        if user_email:
            reply_to = user_email

    elif notification_slug in (
            'claim_code_generated'):
        organization_email = context.get('profile', {}).get('email', "")
        if organization_email:
            recipients = [organization_email]
        reply_to = originated_by.get('email', "")

    elif notification_slug in (
            'organization_updated',
            'order_executed',
            'card_updated',
            'charge_receipt',
            'card_expires_soon',
            'expires_soon'):
        organization_email = context.get('profile', {}).get('email', "")
        if organization_email:
            recipients = [organization_email]
        organization = get_organization_model().objects.get(
            slug=context.get('profile', {}).get('slug'))
        bcc = (_notified_managers(organization, notification_slug,
                originated_by=originated_by)
            + _notified_managers(broker, notification_slug,
                originated_by=originated_by))

    elif notification_slug in (
            'role_grant_created',):
        user_email = context.get('user', {}).get('email', "")
        if user_email:
            recipients = [user_email]
        organization = get_organization_model().objects.get(
            slug=context.get('profile', {}).get('slug'))
        bcc = _notified_managers(organization, notification_slug,
                originated_by=originated_by)
        reply_to = originated_by.get('email', "")

    elif notification_slug in (
            'role_request_created',
            'role_grant_accepted',):
        organization_email = context.get('profile', {}).get('email', "")
        if organization_email:
            recipients = [organization_email]
        organization = get_organization_model().objects.get(
            slug=context.get('profile', {}).get('slug'))
        bcc = _notified_managers(organization, notification_slug,
                originated_by=originated_by)
        reply_to = originated_by.get('email', "")

    elif notification_slug in (
            'subscription_grant_created',
            'subscription_request_accepted',):
        # provider to subscriber
        organization_email = context.get('profile', {}).get('email', "")
        if organization_email:
            recipients = [organization_email]
        subscriber = get_organization_model().objects.get(
            slug=context.get('profile', {}).get('slug'))
        provider = get_organization_model().objects.get(
            slug=context.get('provider', {}).get('slug'))
        bcc = (_notified_managers(subscriber, notification_slug,
                originated_by=originated_by) +
               _notified_managers(provider, notification_slug,
                originated_by=originated_by))
        reply_to = originated_by.get('email', "")

    elif notification_slug in (
            'subscription_grant_accepted',
            'subscription_request_created'):
        # subscriber to provider
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
        reply_to = originated_by.get('email', "")

    elif notification_slug in (
            'processor_setup_error',
            'user_registered',
            'user_activated',
            'weekly_sales_report_created'):
        recipients = [broker.email]
        bcc = _notified_managers(broker, notification_slug)
        reply_to = broker.email

    return recipients, bcc, reply_to
