# Copyright (c) 2023, DjaoDjin inc.
# see LICENSE
from __future__ import unicode_literals

from django.dispatch import Signal


user_contact = Signal( #pylint:disable=invalid-name
#    providing_args=["provider", "user", "reason"]
)
