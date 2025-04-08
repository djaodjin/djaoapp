# Copyright (c) 2025, DjaoDjin inc.
# see LICENSE
from __future__ import unicode_literals

import json, logging, smtplib

from deployutils.crypt import JSONEncoder
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import get_connection as get_connection_base
from django.template import TemplateSyntaxError
from django.utils import translation
from extended_templates.backends import get_email_backend
from extended_templates.backends.eml import EmlTemplateError
from saas import settings as saas_settings
from saas.models import get_broker
from saas.utils import get_organization_model
from signup import settings as signup_settings
from signup.models import Contact

from ...compat import gettext_lazy as _
from ...thread_locals import build_absolute_uri
from ...utils import get_email_connection, get_notified_on_errors
from ..serializers import ExpireUserNotificationSerializer


LOGGER = logging.getLogger(__name__)


def _notified_managers(organization, notification_slug, originated_by=None):
    managers = organization.with_role(saas_settings.MANAGER)
    if originated_by:
        managers = managers.exclude(email=originated_by.get('email', ""))
    # checking whether those users are subscribed to the notification
    if signup_settings.NOTIFICATIONS_OPT_OUT:
        filtered = managers.exclude(notifications__slug=notification_slug)
    else:
        filtered = managers.filter(notifications__slug=notification_slug)
    return [notified.email for notified in filtered if notified.email]


def notified_recipients(notification_slug, context, broker=None):
    """
    Returns the organization email or the managers email if the organization
    does not have an e-mail set.
    """
    #pylint:disable=too-many-locals
    organization_model = get_organization_model()
    recipients = []
    bcc = []
    if not broker:
        broker = get_broker()
    originated_by = context.get('originated_by')
    if not originated_by:
        originated_by = {}
    reply_to = originated_by.get('email')
    if (not reply_to and broker.email and
        broker.email != settings.DEFAULT_FROM_EMAIL):
        reply_to = broker.email

    # Notify a single user because there is a verification_key
    # in the e-mail body.
    if notification_slug in (
            'role_grant_created',
            'user_reset_password',
            'user_logged_in',
            'user_login_failed',
            'user_verification',
            'user_welcome',):
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
            'charge_updated',
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
            'charge_updated',
            'card_expires_soon',
            'expires_soon'):
            try:
                # When the theme editor attempts to "Send Test Email",
                # it is highly likely the sample data does not exist
                # in the database.
                organization = organization_model.objects.get(
                    slug=context.get('profile', {}).get('slug'))
                bcc = _notified_managers(organization, notification_slug,
                        originated_by=originated_by)
            except organization_model.DoesNotExist:
                bcc = []
            # We also notify the provider managers that are interested
            # in these events.
            if notification_slug in (
                'subscription_request_accepted',):
                try:
                    # When the theme editor attempts to "Send Test Email",
                    # it is highly likely the sample data does not exist
                    # in the database.
                    provider = organization_model.objects.get(
                        slug=context.get('provider', {}).get('slug'))
                    bcc += _notified_managers(provider, notification_slug,
                        originated_by=originated_by)
                except organization_model.DoesNotExist:
                    pass
            # We also notify the broker managers that are interested
            # in these events.
            elif notification_slug in (
                    'profile_updated',
                    'order_executed',
                    'card_updated',
                    'charge_updated',
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
            try:
                # When the theme editor attempts to "Send Test Email",
                # it is highly likely the sample data does not exist
                # in the database.
                provider = organization_model.objects.get(
                    slug=context.get('profile', {}).get('slug'))
                bcc = _notified_managers(provider, notification_slug,
                    originated_by=originated_by)
            except organization_model.DoesNotExist:
                bcc = []
            try:
                # When the theme editor attempts to "Send Test Email",
                # it is highly likely the sample data does not exist
                # in the database.
                subscriber = organization_model.objects.get(
                    slug=context.get('subscriber', {}).get('slug'))
                bcc += _notified_managers(subscriber, notification_slug,
                    originated_by=originated_by)
            except organization_model.DoesNotExist:
                pass

    elif notification_slug in (
            'user_contact',
            'processor_setup_error',
            'user_registered',
            'user_activated',
            'period_sales_report_created',
            'notification_error'):
        # We are hanlding `recipients` a bit differently here because contact
        # requests are usually meant to be sent to a ticketing system.
        recipients = [broker.email]
        if notification_slug in (
                'processor_setup_error',
                'user_registered',
                'user_activated',
                'period_sales_report_created',
                'notification_error'):
            bcc = _notified_managers(broker, notification_slug)

    # When we are dealing with personal profiles (or if the e-mail
    # address of the profile is the same as a the e-mail of a user),
    # We want to be mindful of a user preferences with regards to
    # enabled/disabled e-mail notifications.
    matching_users = get_user_model().objects.filter(email__in=recipients)
    recipients = [email for email in recipients
        if not email in matching_users.values_list('email', flat=True)]
    if signup_settings.NOTIFICATIONS_OPT_OUT:
        filtered = matching_users.exclude(notifications__slug=notification_slug)
    else:
        filtered = matching_users.filter(notifications__slug=notification_slug)
    recipients += [notified.email for notified in filtered if notified.email]

    return recipients, bcc, reply_to


class NotificationEmailBackend(object):

    def send_notification(self, event_name, context=None, request=None,
                          **kwargs):
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
        recipients = kwargs.get('recipients', [])
        bcc = []
        reply_to = recipients
        if not recipients:
            recipients, bcc, reply_to = notified_recipients(
                event_name, context)

        if not bool(settings.NOTIFICATION_EMAIL_DISABLED):
            # If we have explicitely disabled e-mail notification,
            # there is nothing to do.
            self.send_mail(template, context, recipients,
                bcc=bcc, reply_to=reply_to, request=request)


    def send_mail(self, template, context, recipients, bcc=None, reply_to=None,
                  request=None):
        #pylint:disable=too-many-arguments
        if not bcc:
            bcc = []

        LOGGER.debug("djaoapp_extras.recipients.send_notification("\
            "recipients=%s, reply_to='%s', bcc=%s,"\
            "event=%s)", recipients, reply_to, bcc,
            json.dumps(context, indent=2, cls=JSONEncoder))
        lang_code = None
        if request:
            lang_code = translation.get_language_from_request(request)
        if not lang_code:
            contact = Contact.objects.filter(
                email__in=recipients).order_by('email').first()
            if contact:
                lang_code = contact.lang

        try:
            # When this method is called through an HTTP request initiated
            # in a browser client, the lang_code will be set by the browser
            # language. We don't want to override it here.
            if lang_code:
                with translation.override(lang_code):
                    get_email_backend(
                        connection=get_email_connection()).send(
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipients=recipients,
                        reply_to=reply_to,
                        bcc=bcc,
                        template=template,
                        context=context)
            else:
                # use implicit lang_code set in the context of execution
                get_email_backend(
                    connection=get_email_connection()).send(
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipients=recipients,
                    reply_to=reply_to,
                    bcc=bcc,
                    template=template,
                    context=context)
        except smtplib.SMTPException as err:
            context.update({'errors': [_("There was an error sending"\
    " the following email to %(recipients)s. This is most likely due to"\
    " a misconfiguration of the e-mail notifications whitelabel settings"\
    " for your site %(site)s.") % {
        'recipients': recipients, 'site': build_absolute_uri()}]})
            notified_on_errors = get_notified_on_errors()
            LOGGER.warning("[signal] problem sending email from %s"\
                " on connection for %s: %s", settings.DEFAULT_FROM_EMAIL,
                build_absolute_uri(), err)
            if notified_on_errors:
                get_email_backend(
                    connection=get_connection_base(fail_silently=True)).send(
                    recipients=notified_on_errors,
                    template=template,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    context=context)
        except EmlTemplateError as err:
            LOGGER.warning(str(err))
        except TemplateSyntaxError as err:
            # If there is a problem with the template, notify the user.
            context.update({'errors': [_("There was an error sending"\
    " an email notification to %(recipients)s. This is due to a template"\
    " syntax error in %(template_name)s:") % {
        'recipients': recipients, 'template_name': template},
                "%(err_message)s" % {'err_message': str(err)}]})
            notified_on_errors = get_notified_on_errors()
            LOGGER.warning("[signal] notified %s of syntax error"\
                " in email notification template %s on site %(site)s: %s",
                notified_on_errors, template, build_absolute_uri(), err)
            if notified_on_errors:
                get_email_backend(
                    connection=get_connection_base(fail_silently=True)).send(
                    notified_on_errors, 'notification/syntax_error.eml',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    context=context)
        except Exception as err:
            # Something went horribly wrong, like the email password was not
            # decrypted correctly. We want to notifiy the operations team
            # but the end user shouldn't see a 500 error as a result
            # of notifications sent in the HTTP request pipeline.
            LOGGER.exception(err)


class EmailVerificationBackend(NotificationEmailBackend):

    def send(self, email, email_code,
             back_url=None, expiration_days=signup_settings.KEY_EXPIRATION):
        """
        Send an e-mail message to the user to verify her e-mail address.

        **Example

        .. code-block:: json

        {
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
        user = Contact.objects.filter(email__iexact=email).first()
        context = {
            'broker': get_broker(),
            'user': user,
            'back_url': back_url,
            'code': email_code,
            'nb_expiration_days': expiration_days
        }
        self.send_mail('notification/user_verification.eml',
            ExpireUserNotificationSerializer().to_representation(context),
            [email])
