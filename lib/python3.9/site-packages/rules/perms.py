# Copyright (c) 2020, DjaoDjin inc.
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

from __future__ import unicode_literals

import logging

from django.conf import settings as django_settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.core.exceptions import PermissionDenied

from . import settings
from .compat import is_authenticated, six
from .models import Engagement, Rule
from .utils import datetime_or_now


LOGGER = logging.getLogger(__name__)


class NoRuleMatch(RuntimeError):

    def __init__(self, path):
        super(NoRuleMatch, self).__init__(
            "No access rules triggered by path '%s'" % path)


def _insert_url(request, redirect_field_name=REDIRECT_FIELD_NAME,
                inserted_url=django_settings.LOGIN_URL):
    '''Redirects to the *inserted_url* before going to the orginal
    request path.'''
    # This code is pretty much straightforward
    # from contrib.auth.user_passes_test
    path = request.build_absolute_uri()
    # If the login url is the same scheme and net location then just
    # use the path as the "next" url.
    login_scheme, login_netloc = six.moves.urllib.parse.urlparse(
        str(inserted_url))[:2]
    current_scheme, current_netloc = six.moves.urllib.parse.urlparse(path)[:2]
    if ((not login_scheme or login_scheme == current_scheme) and
        (not login_netloc or login_netloc == current_netloc)):
        path = request.get_full_path()
    # As long as *inserted_url* is not None, this call will redirect
    # anything (i.e. inserted_url), not just the login.
    from django.contrib.auth.views import redirect_to_login
    return redirect_to_login(path, inserted_url, redirect_field_name)


def _get_accept_list(request):
    http_accept = request.META.get('HTTP_ACCEPT', '*/*')
    return [item.strip() for item in http_accept.split(',')]


def find_rule(request, app, prefixes=None):
    """
    Returns a tuple mad of the rule that was matched and a dictionnary
    of parameters that where extracted from the URL (i.e. :slug).
    """
    matched_rule = getattr(request, 'matched_rule', None)
    matched_params = getattr(request, 'matched_params', {})
    if matched_rule:
        # Use cached tuple.
        return (matched_rule, matched_params)
    params = {}
    request_path = request.path
    request_path_parts = [part for part in request_path.split('/') if part]
    for rule in Rule.objects.get_rules(app, prefixes=prefixes):
        LOGGER.debug("Match %s with %s ...",
            '/'.join(request_path_parts), rule.get_full_page_path())
        params = rule.match(request_path_parts)
        if params is not None:
            LOGGER.debug(
                "matched %s with %s (rule=%d, forward=%s, params=%s)",
                request_path, rule.get_full_page_path(),
                rule.rule_op, rule.is_forward, params)
            return (rule, params)
    return (None, {})


def redirect_or_denied(request, inserted_url,
                       redirect_field_name=REDIRECT_FIELD_NAME, descr=None):
    http_accepts = _get_accept_list(request)
    if ('text/html' in http_accepts
        and isinstance(inserted_url, six.string_types)):
        return _insert_url(request,
            redirect_field_name=redirect_field_name, inserted_url=inserted_url)
    LOGGER.debug("Looks like an API call or no inserted url"\
        " (Accept: %s contains 'text/html' (%s),"\
        " inserted_url=%s is a string (%s)) => %s",
        request.META.get('HTTP_ACCEPT', '*/*'), 'text/html' in http_accepts,
        inserted_url, isinstance(inserted_url, six.string_types),
      ('PermissionDenied("%s")' % str(descr)) if descr else "PermissionDenied")
    if descr is None:
        descr = ""
    raise PermissionDenied(descr)


def engaged(rule, request=None):
    """
    Returns the last time the page was visited
    """
    last_visited = None
    if rule.engaged:
        last_tags = []
        datetime_stored = datetime_or_now()
        for tag in rule.engaged.split(','):
            obj, created = Engagement.objects.get_or_create(
                slug=tag, user=request.user,
                defaults={'last_visited': datetime_stored})
            if created:
                LOGGER.info(
                    "initial '%s' engagement%s", tag,
                    (" on %s" % request.path) if request is not None else "",
                    extra={'event': 'initial-engagement', 'request': request})
            elif last_visited:
                last_tags += [tag]
                last_visited = max(obj.last_visited, last_visited)
            else:
                last_tags += [tag]
                last_visited = obj.last_visited
        last_visited_tags = ','.join(last_tags)
        if last_tags and last_visited_tags != rule.engaged:
            last_visited = last_visited_tags
    return last_visited


def check_matched(request, app, prefixes=None,
                  redirect_field_name=REDIRECT_FIELD_NAME, login_url=None):
    """
    Returns a tuple (response, forward, session) if the *request.path* can
    be matched otherwise raises a NoRuleMatch exception.
    """
    session = {}
    matched, params = find_rule(request, app, prefixes=prefixes)
    if matched:
        if matched.rule_op == Rule.ANY:
            if is_authenticated(request):
                last_visited = engaged(matched, request=request)
                session.update({'last_visited': last_visited})
            return (None, matched, session)

        redirect_url = None
        if not is_authenticated(request):
            LOGGER.debug("user is not authenticated")
            redirect_url = _insert_url(request, redirect_field_name,
                login_url or django_settings.LOGIN_URL)
        else:
            _, fail_func, defaults = settings.RULE_OPERATORS[matched.rule_op]
            kwargs = defaults.copy()
            if isinstance(params, dict):
                kwargs.update(params)
            LOGGER.debug("calling %s(user=%s, kwargs=%s) ...",
                fail_func.__name__, request.user, kwargs)
            redirect_url = fail_func(request, **kwargs)
            LOGGER.debug("calling %s(user=%s, kwargs=%s) => %s",
                fail_func.__name__, request.user, kwargs, redirect_url)
            if not redirect_url:
                redirect_url = None

        if not redirect_url:
            last_visited = engaged(matched, request=request)
            session.update({'last_visited': last_visited})
        return (redirect_url, matched if redirect_url is None else None,
            session)
    LOGGER.debug("unmatched %s", request.path)
    raise NoRuleMatch(request.path)


def check_permissions(request, app, redirect_field_name=REDIRECT_FIELD_NAME,
                      login_url=None):
    """
    Returns a tuple (response, forward, session) if the *request.path* can
    be matched otherwise raises a PermissionDenied exception.
    """
    try:
        return check_matched(request, app,
            redirect_field_name=redirect_field_name, login_url=login_url)
    except NoRuleMatch as err:
        raise PermissionDenied(str(err))
