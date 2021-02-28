# Copyright (c) 2017, DjaoDjin inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED
# TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
# OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
# OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
# ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import datetime, json, logging

from django.apps import apps as django_apps
from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import import_string
from django.utils.timezone import utc
from pytz import timezone, UnknownTimeZoneError
from pytz.tzinfo import DstTzInfo


LOGGER = logging.getLogger(__name__)


class JSONEncoder(json.JSONEncoder):

    def default(self, obj): #pylint: disable=method-hidden
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        return super(JSONEncoder, self).default(obj)


def datetime_or_now(dtime_at=None):
    if not dtime_at:
        return datetime.datetime.utcnow().replace(tzinfo=utc)
    if dtime_at.tzinfo is None:
        dtime_at = dtime_at.replace(tzinfo=utc)
    return dtime_at


def get_app_model():
    """
    Returns the Site model that is active in this project.
    """
    from . import settings
    try:
        return django_apps.get_model(settings.RULES_APP_MODEL)
    except ValueError:
        raise ImproperlyConfigured(
            "RULES_APP_MODEL must be of the form 'app_label.model_name'")
    except LookupError:
        raise ImproperlyConfigured("RULES_APP_MODEL refers to model '%s'"\
" that has not been installed" % settings.RULES_APP_MODEL)


def get_current_app(request=None):
    """
    Returns the default app for a site.
    """
    from . import settings
    if settings.DEFAULT_APP_CALLABLE:
        app = import_string(settings.DEFAULT_APP_CALLABLE)(request=request)
        LOGGER.debug("rules.get_current_app: '%s'", app)
    else:
        app = get_app_model().objects.get(pk=settings.DEFAULT_APP_ID)
    return app


def parse_tz(tzone):
    if issubclass(type(tzone), DstTzInfo):
        return tzone
    if tzone:
        try:
            return timezone(tzone)
        except UnknownTimeZoneError:
            pass
    return None
