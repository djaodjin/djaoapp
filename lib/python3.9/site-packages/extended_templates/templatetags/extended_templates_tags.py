# Copyright (c) 2017, DjaoDjin inc.
#   All rights reserved.

from django import template
from django.forms import widgets


register = template.Library()


@register.filter()
def is_checkbox(field):
    return isinstance(field.widget, widgets.CheckboxInput)


@register.filter()
def is_radio(field):
    return isinstance(field.widget, widgets.RadioSelect)


@register.filter()
def is_textarea(field):
    return isinstance(field.widget, widgets.Textarea)


@register.filter()
def get_bounded_field(form, key):
    bounded_field = form[key]
    if bounded_field is None:
        raise KeyError("%s not found in form" % key)
    return bounded_field
