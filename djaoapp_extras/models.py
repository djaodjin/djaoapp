# Copyright (c) 2023, DjaoDjin inc.
# see LICENSE
from __future__ import unicode_literals

from django.db import models
from rules.models import BaseApp

from .compat import python_2_unicode_compatible, gettext_lazy as _


@python_2_unicode_compatible
class App(BaseApp):

    show_edit_tools = models.BooleanField(null=True, default=True,
        help_text=_("Show the online editor tools"))

    class Meta:
        db_table = 'rules_app'

    def __str__(self):
        return str(self.slug)
