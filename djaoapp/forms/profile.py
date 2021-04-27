# Copyright (c) 2021, DjaoDjin inc.
# see LICENSE
from __future__ import unicode_literals

from django import forms
from django.conf import locale
from django.utils.translation import ugettext_lazy as _
from saas.forms import OrganizationForm

from ..compat import six


class PersonalProfileForm(OrganizationForm):

    lang = forms.CharField(
        label=_("Language"),
        widget=forms.Select(
            choices=[(lang['code'], lang['name_local'])
            for lang in six.itervalues(locale.LANG_INFO)
            if 'code' in lang]))

    def __init__(self, *args, **kwargs):
        super(PersonalProfileForm, self).__init__(*args, **kwargs)
        self.fields['full_name'].label = _('Full name')
        # XXX define other fields dynamically (username, etc.):
        # Unless it is not necessary?
