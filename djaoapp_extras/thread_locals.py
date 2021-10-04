# Copyright (c) 2021, DjaoDjin inc.
#   All rights reserved.

import logging

from django.http import Http404
from multitier.thread_locals import get_current_site
from rules.utils import get_app_model


LOGGER = logging.getLogger(__name__)


def get_current_app(request=None):
    """
    Returns the provider ``rules.App`` as read in the active database
    for the ``rules`` and ``pages`` application.
    """
    # If we don't write the code as such, we might end-up generating
    # an extra SQL query every time ``get_current_app`` is called.
    thread_local_site = get_current_site()
    app = getattr(thread_local_site, 'app', None)
    if thread_local_site and not app:
        app_model = get_app_model()
        try:
            thread_local_site.app = app_model.objects.get(
                slug=thread_local_site.slug)
        except app_model.DoesNotExist:
            #pylint:disable=protected-access
            msg = "No %s with slug '%s' can be found." % (
                app_model._meta.object_name, thread_local_site.slug)
            if request is not None:
                LOGGER.exception(
                    "get_current_app: %s", msg, extra={'request': request})
            else:
                LOGGER.exception("get_current_app: %s", msg)
            raise Http404(msg)
        app = thread_local_site.app
    return app
