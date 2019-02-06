# Copyright (c) 2019, DjaoDjin inc.
# see LICENSE

from django.utils.encoding import python_2_unicode_compatible
from multitier.models import BaseSite
from rules.models import BaseApp

@python_2_unicode_compatible
class App(BaseSite, BaseApp):

    class Meta:
        db_table = 'djaoapp_app'
