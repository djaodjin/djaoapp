# Copyright (c) 2019, DjaoDjin inc.
# see LICENSE
from __future__ import unicode_literals

from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from rules.models import BaseApp


@python_2_unicode_compatible
class App(BaseApp):

    show_edit_tools = models.NullBooleanField(default=True)

    class Meta:
        db_table = 'rules_app'

    def __str__(self): #pylint: disable=super-on-old-class
        return self.slug

