# Copyright (c) 2019, DjaoDjin inc.
# see LICENSE

from __future__ import unicode_literals

from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _
from multitier.models import BaseSite, SUBDOMAIN_SLUG
from rules.models import BaseApp

@python_2_unicode_compatible
class App(BaseSite, BaseApp):

    # Both slug for multitier.Site and rules.App. Since most DNS provider
    # limit subdomain length to 25 characters, we do here too.
    slug = models.SlugField(unique=True, max_length=25,
        validators=[SUBDOMAIN_SLUG], help_text=_(
            "unique identifier for the site (also serves as subdomain)"))
    account = models.ForeignKey('saas.Organization',
        null=True, on_delete=models.CASCADE, related_name='djaoapp_app')

    class Meta:
        db_table = 'rules_app'

    def __str__(self): #pylint: disable=super-on-old-class
        return self.slug

    @property
    def printable_name(self):
        return self.slug


@python_2_unicode_compatible
class Site(BaseSite, BaseApp):

    # Both slug for multitier.Site and rules.App. Since most DNS provider
    # limit subdomain length to 25 characters, we do here too.
    slug = models.SlugField(unique=True, max_length=25,
        validators=[SUBDOMAIN_SLUG], help_text=_(
            "unique identifier for the site (also serves as subdomain)"))
    account = models.ForeignKey('saas.Organization',
        null=True, on_delete=models.CASCADE, related_name='djaoapp_site')

    class Meta:
        db_table = 'multitier_site'

    def __str__(self): #pylint: disable=super-on-old-class
        return self.slug

    @property
    def printable_name(self):
        return self.slug
