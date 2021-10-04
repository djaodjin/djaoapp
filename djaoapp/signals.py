# Copyright (c) 2021, DjaoDjin inc.
# see LICENSE
from __future__ import unicode_literals

from django.dispatch import Signal


contact_requested = Signal( #pylint:disable=invalid-name
    providing_args=["provider", "user", "reason"])
