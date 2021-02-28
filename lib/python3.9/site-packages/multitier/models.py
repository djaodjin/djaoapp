# Copyright (c) 2020, Djaodjin Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
# OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
# OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
# ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""
Models for the multi-tier application.
"""

import re, string

from django.core.mail import get_connection as get_connection_base
from django.core.validators import (_lazy_re_compile, RegexValidator,
    URLValidator)
from django.core.exceptions import ValidationError
from django.db import models
from django.utils._os import safe_join
from django.utils.translation import ugettext_lazy as _

from deployutils.crypt import decrypt, encrypt

from . import settings
from .compat import python_2_unicode_compatible
from .utils import get_site_model


SUBDOMAIN_RE = r'^[-a-zA-Z0-9_]+\Z'
SUBDOMAIN_SLUG = RegexValidator(
    SUBDOMAIN_RE,
    _("Enter a valid subdomain consisting of letters, digits or hyphens."),
    'invalid'
)
HOST_VALIDATOR = RegexValidator(
    _lazy_re_compile(
        r'(?:' + URLValidator.ipv4_re + '|' + URLValidator.ipv6_re + \
        '|' + URLValidator.host_re + ')' # host
        r'(?::\d{2,5})?'                                       # port
        r'(?:[/?#][^\s]*)?'                                    # resource path
        r'\Z', re.IGNORECASE),
    _("Enter a valid host, optionally followed by a port and resource path."),
    'invalid'
)

def domain_name_validator(value):
    """
    Validates that the given value contains no whitespaces to prevent common
    typos.
    """
    if not value:
        return
    checks = ((s in value) for s in string.whitespace)
    if any(checks):
        raise ValidationError(
            _("The domain name cannot contain any spaces or tabs."),
            code='invalid',
        )


@python_2_unicode_compatible
class BaseSite(models.Model):

    # Since most DNS provider limit subdomain length to 25 characters,
    # we do here too. `django.contrib.Site` limits the domain length
    # to 100 characters so we also do the same. Though 100 characters
    # is often not enough for 3rd part db/email host names (ex: AWS RDS,
    # AWS SES) so we bumped the limit to 255 for those.
    slug = models.SlugField(unique=True, max_length=25,
        validators=[SUBDOMAIN_SLUG], help_text=_(
            "unique identifier for the site (also serves as subdomain)"))

    domain = models.CharField(max_length=100, null=True, blank=True,
        validators=[domain_name_validator, RegexValidator(
            URLValidator.host_re,
            _("Enter a valid 'domain', ex: example.com"), 'invalid')],
        help_text=_(
            _("fully qualified domain name at which the site is available")))
    is_path_prefix = models.BooleanField(default=False, help_text=_(
        "use slug as a prefix for URL paths instead of domain field."))
    cert_location = models.CharField(max_length=1024, null=True,
        help_text=_("Location of the TLS certificate for HTTPS connections"))

    account = models.ForeignKey(
        settings.ACCOUNT_MODEL, null=True, on_delete=models.CASCADE,
        related_name='sites')
    is_active = models.BooleanField(default=False,
        help_text=_("The Site is active or not"))
    tag = models.CharField(null=True, max_length=255,
        help_text=_("Tags can be used by the project to filter sites"))
    base = models.ForeignKey('self',
        null=True, on_delete=models.CASCADE,
        help_text=_("The site is a derivative of this parent."))

    # Database connection
    db_name = models.SlugField(max_length=255, null=True,
        help_text=_("name of database to connect to for the site"))
    db_host = models.CharField(max_length=255, null=True, blank=True,
        validators=[HOST_VALIDATOR],
        help_text=_("host to connect to the database"))
    db_port = models.IntegerField(null=True, blank=True,
        help_text=_("port to connect to the database host"))
    db_host_user = models.CharField(max_length=128, null=True, blank=True,
        help_text=_("username authorized to connect to the database"))
    db_host_password = models.CharField(_('Password'), max_length=128,
        null=True, blank=True,
        help_text=_("password to authenticate user connecting to the database"))

    # SMTP connection
    email_default_from = models.EmailField(null=True, blank=True)
    email_host = models.CharField(max_length=255, null=True, blank=True,
        validators=[HOST_VALIDATOR],
        help_text=_("host to connect to the SMTP server"))
    email_port = models.IntegerField(null=True, blank=True,
        help_text=_("port to connect to the SMTP server"))
    email_host_user = models.CharField(max_length=128, null=True, blank=True,
        help_text=_("username authorized to send e-mails on the SMTP server"))
    email_host_password = models.CharField(_('Password'), max_length=128,
        null=True, blank=True,
        help_text=_("password to authenticate the user with the SMTP server"))

    class Meta:
        swappable = 'MULTITIER_SITE_MODEL'
        abstract = True

    def __str__(self): #pylint: disable=super-on-old-class
        return self.slug

    def as_base(self):
        """
        Returns either the base site or ``self`` if no base exists.
        """
        if self.base_id:
            return self.base
        return self

    def as_subdomain(self):
        return self.slug

    @property
    def printable_name(self):
        return self.slug

    def get_templates(self):
        """
        Returns a list of candidate themes.
        """
        return [self.slug]

    def get_template_dirs(self):
        """
        Returns a list of candidate search paths for templates.
        """
        return [safe_join(theme_dir, theme, 'templates')
                for theme_dir in settings.THEMES_DIRS
                    for theme in self.get_templates()]

    def add_tags(self, tags):
        tags = [''] + tags # make a clone since we are going to be destructive.
                           # also add the extra coma prefix needed later on.
        if self.tag:
            for tag in self.tag.split(','):
                if tag in tags:
                    tags = [rec for rec in tags if rec != tag]
        else:
            self.tag = ""
        self.tag += ','.join(tags)

    def remove_tags(self, tags):
        if self.tag:
            self.tag = ','.join([
                tag for tag in self.tag.split(',') if tag not in tags])

    @property
    def has_custom_connection(self):
        return (self.email_host_user or self.email_host_password or
            self.email_host or self.email_port)

    def get_email_connection(self):
        kwargs = {}
        if self.email_host:
            kwargs['host'] = self.email_host
        if self.email_port:
            kwargs['port'] = self.email_port
        if self.email_host_user:
            kwargs['username'] = self.email_host_user
        if self.email_host_password:
            kwargs['password'] = self.get_email_host_password()
        return get_connection_base(**kwargs)

    def get_from_email(self):
        if self.email_default_from:
            return self.email_default_from
        if self.email_host_user and '@' in self.email_host_user:
            return self.email_host_user
        return settings.DEFAULT_FROM_EMAIL

    def set_email_host_password(self, raw_password, passphrase=None):
        if not passphrase:
            passphrase = settings.SECRET_KEY
        self.email_host_password = encrypt(raw_password, passphrase=passphrase)

    def get_email_host_password(self, passphrase=None):
        if not passphrase:
            passphrase = settings.SECRET_KEY
        return decrypt(self.email_host_password, passphrase=passphrase)


@python_2_unicode_compatible
class Site(BaseSite):

    def __str__(self): #pylint: disable=super-on-old-class
        return self.slug


def get_site_or_none(subdomain):
    """
    Returns a ``Site`` instance based on its subdomain while prefering
    ``Site`` with an explicit domain.
    If no Site could be found, then returns ``None``.
    """
    return get_site_model().objects.filter(
        slug=subdomain).order_by('domain', '-pk').first()
