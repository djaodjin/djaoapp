# Copyright (c) 2019, DjaoDjin inc.
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

import datetime, logging

from dateutil.tz import tzlocal
from pytz import utc
import six

LOGGER = logging.getLogger(__name__)


def as_timestamp(dtime_at=None):
    if not dtime_at:
        dtime_at = datetime_or_now()
    return int((
        dtime_at - datetime.datetime(1970, 1, 1, tzinfo=utc)).total_seconds())


def datetime_or_now(dtime_at=None):
    if not isinstance(dtime_at, datetime.datetime):
        # `datetime.datetime` is a subclass of `datetime.date`.
        if isinstance(dtime_at, six.string_types):
            try:
                # XXX `parse_datetime`
                dtime_at = datetime.datetime.strptime(
                    dtime_at, "%Y-%m-%dT%H:%M:%S.%fZ")
            except ValueError as err:
                try:
                    dtime_at = datetime.datetime.strptime(dtime_at, "%Y-%m-%d")
                except ValueError as err:
                    LOGGER.warning(err)
                    dtime_at = None
        elif isinstance(dtime_at, datetime.date):
            dtime_at = datetime.datetime(
                dtime_at.year, dtime_at.month, dtime_at.day)
    if not dtime_at:
        dtime_at = datetime.datetime.utcnow().replace(tzinfo=utc)
    if dtime_at.tzinfo is None:
        dtime_at = dtime_at.replace(tzinfo=utc)
    return dtime_at


def full_name_natural_split(full_name):
    """
    This function splits a full name into a natural first name, last name
    and middle initials.
    """
    parts = full_name.strip().split(' ')
    first_name = ""
    if parts:
        first_name = parts.pop(0)
    if first_name.lower() == "el" and parts:
        first_name += " " + parts.pop(0)
    last_name = ""
    if parts:
        last_name = parts.pop()
    if (last_name.lower() == 'i' or last_name.lower() == 'ii'
        or last_name.lower() == 'iii' and parts):
        last_name = parts.pop() + " " + last_name
    middle_initials = ""
    for middle_name in parts:
        if middle_name:
            middle_initials += middle_name[0]
    return first_name, middle_initials, last_name


def start_of_day(dtime_at=None):
    """
    Returns the local (user timezone) start of day, that's,
    time 00:00:00 for a given datetime
    """
    dtime_at = datetime_or_now(dtime_at)
    return datetime.datetime(dtime_at.year, dtime_at.month,
        dtime_at.day, tzinfo=tzlocal())


def update_context_urls(context, urls):
    if 'urls' in context:
        for key, val in six.iteritems(urls):
            if key in context['urls']:
                if isinstance(val, dict):
                    context['urls'][key].update(val)
                else:
                    # Because organization_create url is added in this mixin
                    # and in ``OrganizationRedirectView``.
                    context['urls'][key] = val
            else:
                context['urls'].update({key: val})
    else:
        context.update({'urls': urls})
    return context
