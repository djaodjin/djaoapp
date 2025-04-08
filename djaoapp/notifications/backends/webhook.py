# Copyright (c) 2025, DjaoDjin inc.
# see LICENSE
import json, logging

from urllib import request
from django.conf import settings

from ...compat import force_str

LOGGER = logging.getLogger(__name__)


class NotificationWebhookBackend(object):

    def send_notification(self, event_name,
                          context=None, request=None, **kwargs):
        webhook_url = force_str(settings.NOTIFICATION_WEBHOOK_URL)
        if not webhook_url:
            # Unless we have an actual Webhook URL, there is nothing to do.
            return

        # The site can be inferred from `context['back_url']`.
        recipients = kwargs.get('recipients', [])
        context.update({
            'event': event_name,
            'recipients': recipients
        })

        body = json.dumps(context).encode('utf8')

        req = request.Request(webhook_url, data=body, headers={
            'Content-Type': 'application/json'})
        try:
            with request.urlopen(req):
                pass
        except Exception as err:
            LOGGER.exception(err)
