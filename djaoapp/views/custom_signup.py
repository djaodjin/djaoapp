# Copyright (c) 2025, DjaoDjin inc.
# see LICENSE
from __future__ import unicode_literals

import logging

from django.conf import settings
from rules.mixins import AppMixin
from saas.models import Agreement, get_broker
from signup.views.auth import (
    ActivationView as ActivationBaseView,
    PasswordResetConfirmView as PasswordResetConfirmBaseView,
    RecoverView as RecoverBaseView,
    SigninView as SigninBaseView,
    SignoutView as SignoutBaseView,
    SignupView as SignupBaseView)

from ..forms.custom_signup import (ActivationForm, CodeActivationForm,
    PasswordResetConfirmForm, SigninForm, SignupForm)
from ..mixins import AuthMixin
from ..utils import PERSONAL_REGISTRATION, TOGETHER_REGISTRATION


LOGGER = logging.getLogger(__name__)


class ActivationView(AuthMixin, AppMixin, ActivationBaseView):

    form_class = ActivationForm

    def get_initial(self):
        kwargs = super(ActivationView, self).get_initial()
        kwargs.update({
            'extra_fields': [(agreement.slug, agreement.title, False)
                for agreement in Agreement.objects.all()]
        })
        return kwargs


class PasswordResetConfirmView(AuthMixin, AppMixin,
                               PasswordResetConfirmBaseView):

    form_class = ActivationForm
    password_form_class = PasswordResetConfirmForm


class RecoverView(AuthMixin, AppMixin, RecoverBaseView):

    pass


class SigninView(AuthMixin, AppMixin, SigninBaseView):

    form_class = SigninForm
    set_password_form_class = CodeActivationForm

    def get_initial(self):
        kwargs = super(SigninView, self).get_initial()
        broker = get_broker()
        kwargs.update({
            'country': broker.country,
            'region': broker.region
        })
        kwargs.update({
            'extra_fields': [(agreement.slug, agreement.title, False)
                for agreement in Agreement.objects.all()]
        })
        return kwargs


class SignoutView(SignoutBaseView):

    pass


class SignupView(AuthMixin, AppMixin, SignupBaseView):

    form_class = SignupForm

    def get_context_data(self, **kwargs):
        context = super(SignupView, self).get_context_data(**kwargs)
        if hasattr(self, 'already_present_candidate'):
            context.update({
                'already_present_candidate': self.already_present_candidate})
        return context

    def get_initial(self):
        kwargs = super(SignupView, self).get_initial()
        broker = get_broker()
        kwargs.update({
            'country': broker.country,
            'region': broker.region
        })
        kwargs.update({
            'extra_fields': [(agreement.slug, agreement.title, False)
                for agreement in Agreement.objects.all()]
        })
        return kwargs

    def get_form_kwargs(self):
        kwargs = super(SignupView, self).get_form_kwargs()
        if settings.REGISTRATION_STYLE == PERSONAL_REGISTRATION:
            kwargs.update({'force_required': True})
        return kwargs

    def get_template_names(self):
        candidates = []
        register_path = self.kwargs.get('path', None)
        if not register_path and self.app:
            if settings.REGISTRATION_STYLE == PERSONAL_REGISTRATION:
                register_path = 'personal'
            elif settings.REGISTRATION_STYLE == TOGETHER_REGISTRATION:
                register_path = 'organization'
        if register_path:
            candidates = ['accounts/register/%s.html' % register_path]
        return candidates + list(super(SignupView, self).get_template_names())
