# Copyright (c) 2026, DjaoDjin inc.
# see LICENSE
from __future__ import unicode_literals

import logging

from django.conf import settings
from rules.mixins import AppMixin
from saas.models import Agreement, get_broker
from saas import settings as saas_settings
from signup.views.auth import (
    VerifyCompleteView as VerifyCompleteBaseView,
    SigninView as SigninBaseView,
    SignoutView as SignoutBaseView,
    SignupView as SignupBaseView)

from ..forms.custom_signup import (ActivationForm, CodeActivationForm,
    PasswordResetConfirmForm, SigninForm, SignupForm)
from ..mixins import AuthMixin as AuthBaseMixin
from ..utils import PERSONAL_REGISTRATION, TOGETHER_REGISTRATION


LOGGER = logging.getLogger(__name__)


class AuthMixin(AuthBaseMixin):

    def get_initial(self):
        kwargs = super(AuthMixin, self).get_initial()
        broker = get_broker()
        kwargs.update({
            'country': broker.country,
            'region': broker.region
        })
        kwargs.update({
            'extra_fields': [(agreement.slug, agreement.title,
                              agreement.slug == saas_settings.TERMS_OF_USE)
                for agreement in Agreement.objects.all()]
        })
        return kwargs

    def get_form_kwargs(self):
        # XXX Only for registration forms
        #if settings.REGISTRATION_STYLE == PERSONAL_REGISTRATION:
        #    kwargs.update({'force_required': True})
        initial = self.get_initial()
        kwargs = {
            "initial": initial,
            "prefix": self.get_prefix(),
        }

        if self.request.method in ("POST", "PUT"):
            # If we don't do that, 'country' and 'region' won't be set
            # to the default value.
            data = self.request.POST.copy()
            if 'country' not in data:
                data.update({'country': initial['country']})
            if 'region' not in data:
                data.update({'region': initial['region']})
            kwargs.update({
                    "data": data,
                    "files": self.request.FILES,
                })
        return kwargs


    def get_landing(self):
        register_path = super(AuthMixin, self).get_landing()
        if not register_path and self.app:
            if settings.REGISTRATION_STYLE == PERSONAL_REGISTRATION:
                register_path = 'personal'
            elif settings.REGISTRATION_STYLE == TOGETHER_REGISTRATION:
                register_path = 'organization'
        return register_path


class VerifyCompleteView(AuthMixin, AppMixin, VerifyCompleteBaseView):

    form_class = ActivationForm


class SigninView(AuthMixin, AppMixin, SigninBaseView):

    set_password_form_class = CodeActivationForm


class SignoutView(SignoutBaseView):

    pass


class SignupView(AuthMixin, AppMixin, SignupBaseView):

    form_class = SignupForm
    set_password_form_class = CodeActivationForm
