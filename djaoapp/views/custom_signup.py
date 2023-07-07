# Copyright (c) 2023, DjaoDjin inc.
# see LICENSE
from __future__ import unicode_literals

import logging

from deployutils.apps.django.compat import is_authenticated
from rules.mixins import AppMixin
from saas.models import Agreement
from signup.helpers import update_context_urls
from signup.views.auth import (
    ActivationView as ActivationBaseView,
    PasswordResetConfirmView as PasswordResetConfirmBaseView,
    RecoverView as RecoverBaseView,
    SigninView as SigninBaseView,
    SignoutView as SignoutBaseView,
    SignupView as SignupBaseView)

from ..compat import reverse
from ..forms.custom_signup import (ActivationForm, PasswordResetConfirmForm,
    SigninForm, SignupForm)
from ..thread_locals import get_current_broker
from ..mixins import (PasswordResetConfirmMixin, RegisterMixin,
    VerifyCompleteMixin, social_login_urls)


LOGGER = logging.getLogger(__name__)


class AuthMixin(object):

    def get_context_data(self, **kwargs):
        context = super(AuthMixin, self).get_context_data(**kwargs)
        # URLs for user
        if not is_authenticated(self.request):
            user_urls = social_login_urls()
            update_context_urls(context, {'user': user_urls})
        update_context_urls(context, {
            'pricing': reverse('saas_cart_plan_list')})
        return context


class ActivationView(AuthMixin, AppMixin, VerifyCompleteMixin,
                     ActivationBaseView):

    form_class = ActivationForm

    def get_initial(self):
        kwargs = super(ActivationView, self).get_initial()
        kwargs.update({
            'extra_fields': [(agreement.slug, agreement.title, False)
                for agreement in Agreement.objects.all()]
        })
        return kwargs


class PasswordResetConfirmView(PasswordResetConfirmMixin,
                               PasswordResetConfirmBaseView):

    form_class = PasswordResetConfirmForm


class RecoverView(AuthMixin, AppMixin, RecoverBaseView):

    pass


class SigninView(AuthMixin, AppMixin, SigninBaseView):

    form_class = SigninForm


class SignoutView(SignoutBaseView):

    pass


class SignupView(AuthMixin, AppMixin, RegisterMixin, SignupBaseView):

    form_class = SignupForm

    def get_context_data(self, **kwargs):
        context = super(SignupView, self).get_context_data(**kwargs)
        if hasattr(self, 'already_present_candidate'):
            context.update({
                'already_present_candidate': self.already_present_candidate})
        return context

    def get_initial(self):
        kwargs = super(SignupView, self).get_initial()
        broker = get_current_broker()
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
        if self.app and self.app.registration == self.app.PERSONAL_REGISTRATION:
            kwargs.update({'force_required': True})
        return kwargs

    def get_template_names(self):
        candidates = []
        register_path = self.kwargs.get('path', None)
        if not register_path and self.app:
            if self.app.registration == self.app.PERSONAL_REGISTRATION:
                register_path = 'personal'
            elif self.app.registration == self.app.TOGETHER_REGISTRATION:
                register_path = 'organization'
        if register_path:
            candidates = ['accounts/register/%s.html' % register_path]
        return candidates + list(super(SignupView, self).get_template_names())
