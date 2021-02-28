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

"""
Models for the rules application.
"""
from __future__ import unicode_literals

import datetime, json, logging, re
try:
    # Python 2
    from itertools import izip
except ImportError:
    # Python 3
    izip = zip # pylint:disable=invalid-name

from django.core.mail import get_connection as get_connection_base
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q
from django.utils.timezone import utc
from django.utils.module_loading import import_string
from django.utils.translation import ugettext_lazy as _

from . import settings
from .compat import python_2_unicode_compatible


LOGGER = logging.getLogger(__name__)


SUBDOMAIN_RE = r'^[-a-zA-Z0-9_]+\Z'
SUBDOMAIN_SLUG = RegexValidator(
    SUBDOMAIN_RE,
    _("Enter a valid subdomain consisting of letters, digits or hyphens."),
    'invalid'
)


@python_2_unicode_compatible
class Engagement(models.Model):
    """
    This model tracks engagement of a user with the website in order
    to answer questions such as:
        - Has a user either edited a page?
    """
    slug = models.SlugField()
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='engagements')
    last_visited = models.DateTimeField(
        default=datetime.datetime(1971, 1, 1).replace(tzinfo=utc))
    # 1971 instead of 1970 to avoid Overflow exception in South.

    class Meta:
        unique_together = ('slug', 'user')

    def __str__(self):
        return "%s-%s" % (self.slug, self.user)


class AppManager(models.Manager):

    def get_or_create(self, defaults=None, **kwargs):
        app, created = super(AppManager, self).get_or_create(
            defaults=defaults, **kwargs)
        if created:
            for rank_min_one, (path, rule_op, is_forward) \
                in enumerate(settings.DEFAULT_RULES):
                #pylint:disable=no-member
                Rule.objects.db_manager(using=self._db).get_or_create(
                    app=app, rank=rank_min_one + 1,
                    defaults={'path':path, 'rule_op':rule_op,
                        'is_forward': is_forward})
        return app, created


@python_2_unicode_compatible
class BaseApp(models.Model):
    """
    A ``App`` is used to select a database and a firewall profile.

    Implementation Note:
    Because we use separate databases, ``App`` and ``Organization``
    have no direct relationship (inheritance, foreign key, etc.).
    The same ``slug`` will though indistincly pickup a ``App`` and/or
    the matching ``Organization``.
    """
    NO_SESSION = 0
    COOKIE_SESSION_BACKEND = 1
    JWT_SESSION_BACKEND = 2

    SESSION_BACKEND_TYPE = (
        (NO_SESSION, "No session forwarded"),
        (COOKIE_SESSION_BACKEND, "Cookie based session backend"),
        (JWT_SESSION_BACKEND, "JWT based session backend"),
    )

    USER_REGISTRATION = 0
    PERSONAL_REGISTRATION = 1
    TOGETHER_REGISTRATION = 2
    IMPLICIT_REGISTRATION = 3

    REGISTRATION_TYPE = (
        (USER_REGISTRATION, "User registration"),
        (PERSONAL_REGISTRATION, "Personal registration"),
        (TOGETHER_REGISTRATION, "User and organization registration"),
        (IMPLICIT_REGISTRATION, "User registration wth implicit billing"),
    )

    AUTH_ENABLED = 0
    AUTH_LOGIN_ONLY = 1
    AUTH_DISABLED = 2

    AUTH_TYPE = (
        (AUTH_ENABLED, "enabled"),
        (AUTH_LOGIN_ONLY, "login-only"),
        (AUTH_DISABLED, "disabled"),
    )

    objects = AppManager()

    # Since most DNS provider limit subdomain length to 25 characters,
    # we do here too.
    slug = models.SlugField(unique=True, max_length=25,
        validators=[SUBDOMAIN_SLUG], help_text=_(
            "unique identifier for the site (also serves as subdomain)"))

    account = models.ForeignKey(settings.ACCOUNT_MODEL,
        null=True, on_delete=models.CASCADE)

    # Fields for proxy features
    entry_point = models.URLField(max_length=100, null=True,
        help_text=_("Entry point to which requests will be redirected to"))
    enc_key = models.TextField(max_length=480, default="",
        verbose_name='Encryption Key',
        help_text=_("Encryption key used to sign proxyed requests"))
    session_backend = models.PositiveSmallIntegerField(
        choices=SESSION_BACKEND_TYPE, default=COOKIE_SESSION_BACKEND,
        help_text=_("Format to encode session in the forwarded HTTP request"))

    # XXX Fields used to custom signup form
    registration = models.PositiveSmallIntegerField(
        choices=REGISTRATION_TYPE, default=USER_REGISTRATION)

    authentication = models.PositiveSmallIntegerField(
        choices=AUTH_TYPE, default=AUTH_LOGIN_ONLY)
    welcome_email = models.BooleanField(default=True,
        help_text=_("Send a welcome e-mail to newly registered users"))

    class Meta:
        swappable = 'RULES_APP_MODEL'
        abstract = True

    def __str__(self):
        return self.slug

    @property
    def printable_name(self): # XXX Organization full_name
        return str(self)

    def get_changes(self, update_fields):
        changes = {}
        for field_name in ('entry_point', 'enc_key',
                           'session_backend', 'registration',
                           'authentication', 'welcome_email'):
            pre_value = getattr(self, field_name, None)
            post_value = update_fields.get(field_name, None)
            if post_value is not None and pre_value != post_value:
                changes[field_name] = {'pre': pre_value, 'post': post_value}
        return changes

    def get_connection(self):
        #pylint:disable=no-self-use
        kwargs = {}
        return get_connection_base(**kwargs)

    def get_implicit_create_on_none(self):
        return self.registration in (
            self.PERSONAL_REGISTRATION, self.IMPLICIT_REGISTRATION)

    def get_from_email(self):
        #pylint:disable=no-self-use
        return settings.DEFAULT_FROM_EMAIL


@python_2_unicode_compatible
class App(BaseApp):

    def __str__(self):
        return self.slug


class RuleManager(models.Manager):

    def get_rules(self, app, prefixes=None):
        """
        Get a list of access rules ordered by rank. When the optional
        *prefixes* parameter is specified, the list will be filtered
        such that any access rules returned start with one prefix present
        in the *prefixes* list.
        """
        args = []
        if prefixes is not None:
            for prefix in prefixes:
                if not args:
                    args = [Q(path__startswith=prefix)]
                else:
                    args[0] |= Q(path__startswith=prefix)
#            kwargs = {'path__startswith': prefixes}
        #pylint:disable=protected-access
        return self.db_manager(using=app._state.db).filter(
            *args, app=app).order_by('rank')


@python_2_unicode_compatible
class Rule(models.Model):
    """
    Rule to check in order to forward request, serve it locally
    and editing the content coming back through the proxy.
    """
    #pylint:disable=no-init

    HOME = 'index'
    ANY = 0

    objects = RuleManager()

    app = models.ForeignKey(settings.RULES_APP_MODEL,
        on_delete=models.CASCADE)
    # XXX At first I wanted to use a URLField for validation but this only
    #     works for URLs starting with a http/ftp protocol. What we really
    #     want here is a Path validator (including /).
    path = models.CharField(max_length=255,
        help_text=_("OpenAPI path against which requests are matched"))
    rule_op = models.PositiveSmallIntegerField(
        choices=settings.DB_RULE_OPERATORS, default=ANY,
        help_text=_("Method applied to grant or deny access"))
    kwargs = models.CharField(max_length=255, default="",
        help_text=_("Arguments to pass to the method to grant or deny access"))
    is_forward = models.BooleanField(default=True,
        help_text=_("When access is granted, should the request be forwarded"))
    engaged = models.CharField(max_length=50,
        help_text=_("Tags to check if it is the first time a user engages"))
    rank = models.IntegerField(
        help_text=_("Determines the order in which rules are considered"))
    moved = models.BooleanField(default=False)

    class Meta:
        unique_together = (('app', 'rank', 'moved'), ('app', 'path'))

    def __str__(self):
        return "%s/%s" % (self.app, self.path)

    def get_allow(self):
        if self.kwargs:
            return '%d/%s' % (self.rule_op, self.kwargs)
        return '%d' % self.rule_op

    def get_full_page_path(self):
        page_path = self.path
        path_prefix = ""
        if not page_path.startswith("/"):
            page_path = "/" + page_path
        if settings.PATH_PREFIX_CALLABLE:
            path_prefix = import_string(settings.PATH_PREFIX_CALLABLE)()
            if path_prefix and not path_prefix.startswith("/"):
                path_prefix = "/" + path_prefix
        return "%s%s" % (path_prefix, page_path)

    def match(self, request_path_parts):
        """
        Returns the dictionnary with paramaters in the request path
        or ``None`` if the Rule pattern does not match the request path.

        Example::

           Request path /profile/xia/ matched with /profile/:organization/
           will return {"organization": "xia"}.

           Request path /profile/xia/ matched with /billing/:organization/
           will return ``None``.
        """
        params = None
        page_path = self.get_full_page_path()
        # Normalize to avoid issues with path starting or ending with '/':
        pat_parts = [part for part in page_path.split('/') if part]
        if len(request_path_parts) >= len(pat_parts):
            # Only worth matching if the URL is longer than the pattern.
            try:
                params = json.loads(self.kwargs)
            except ValueError:
                params = {}
            for part, pat_part in izip(request_path_parts, pat_parts):
                look = re.match(r'^:(\S+)|\{\S+\}$', pat_part)
                if look:
                    slug = look.group(1)
                    if slug in params:
                        params.update({slug: part})
                elif part != pat_part:
                    return None
        return params
