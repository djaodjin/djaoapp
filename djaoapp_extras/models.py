# Copyright (c) 2023, DjaoDjin inc.
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
from saas.utils import get_organization_model
from signup.models import Contact

from .compat import python_2_unicode_compatible, gettext_lazy as _
from .recipients import notified_recipients

LOGGER = logging.getLogger(__name__)
SEND_EMAIL = settings.SEND_EMAIL


@python_2_unicode_compatible
class App(BaseApp):

    show_edit_tools = models.BooleanField(null=True, default=True,
        help_text=_("Show the online editor tools"))

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

        recipients, bcc, reply_to = notified_recipients(
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
                notified_on_errors, unused1, unused2 = notified_recipients(
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
