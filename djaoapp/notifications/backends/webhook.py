# Copyright (c) 2024, DjaoDjin inc.
# see LICENSE
import json, logging

from urllib import request
from django.conf import settings
from multitier.thread_locals import get_current_site

from ...compat import force_str

LOGGER = logging.getLogger(__name__)


class NotificationWebhookBackend(object):

    def send_notification(self, event_name,
                          context=None, site=None, request=None, **kwargs):
        webhook_url = force_str(settings.NOTIFICATION_WEBHOOK_URL)
        if not webhook_url:
            # Unless we have an actual Webhook URL, there is nothing to do.
            return
        if not site:
            if request and hasattr(request, 'site'):
                site = request.site
        if not site:
            site = get_current_site()
        recipients = kwargs.get('recipients', [])
        context.update({'event': event_name, 'site': site.slug,
            'recipients': recipients})

        body = json.dumps(context).encode('utf8')

        req = request.Request(webhook_url, data=body, headers={
            'Content-Type': 'application/json'})
        try:
            with request.urlopen(req):
                pass
        except Exception as err:
            LOGGER.exception(err)
