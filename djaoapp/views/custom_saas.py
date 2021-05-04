# Copyright (c) 2021, DjaoDjin inc.
# see LICENSE
from __future__ import unicode_literals

import logging

from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.core.exceptions import ValidationError
from django.views.generic.base import ContextMixin, TemplateResponseMixin
from multitier.thread_locals import get_current_site
from saas import settings as saas_settings
from saas.backends import load_backend
from saas.backends.stripe_processor.views import (
    StripeProcessorRedirectView as BaseStripeProcessorRedirectView)
from saas.views.billing import (
    ProcessorAuthorizeView as BaseProcessorAuthorizeView)
from saas.views.profile import (DashboardView as BaseDashboardView,
    OrganizationProfileView as OrganizationProfileViewBase)
from saas.views.roles import (
    RoleImplicitGrantAcceptView as RoleImplicitGrantAcceptViewBase)
from saas.utils import update_context_urls, update_db_row
from signup.decorators import check_email_verified as check_email_verified_base
from signup.helpers import full_name_natural_split
from signup.models import get_user_contact

from ..compat import reverse
from ..forms.profile import PersonalProfileForm


LOGGER = logging.getLogger(__name__)


class DashboardView(BaseDashboardView):

    def get_context_data(self, **kwargs):
        context = super(DashboardView, self).get_context_data(**kwargs)
        if self.organization.is_broker:
            update_context_urls(context, {
                'recent_activity': reverse('api_recent_activity'),
                'api_todos': reverse('api_todos')
            })
        return context


class ProcessorAuthorizeView(BaseProcessorAuthorizeView):

    @property
    def processor_backend(self):
        if not hasattr(self, '_processor_backend'):
            self._processor_backend = load_backend(
                settings.SAAS.get('PROCESSOR', {
                    'BACKEND': 'saas.backends.stripe_processor.StripeBackend'
                }).get(
                    'BACKEND', 'saas.backends.stripe_processor.StripeBackend'))
        return self._processor_backend

    def connect_auth(self, auth_code):
        site = get_current_site()
        try:
            livemode = int(self.request.GET.get('livemode', 1))
        except ValueError:
            livemode = 1
        if livemode:
            site.remove_tags(['testing'])
        else:
            site.add_tags(['testing'])
            self.processor_backend.pub_key = settings.STRIPE_TEST_PUB_KEY
            self.processor_backend.priv_key = settings.STRIPE_TEST_PRIV_KEY
            self.processor_backend.client_id = settings.STRIPE_TEST_CLIENT_ID
        site.save()
        self.processor_backend.connect_auth(self.object, auth_code)

    def get_context_data(self, **kwargs):
        context = super(ProcessorAuthorizeView, self).get_context_data(**kwargs)
        provider = self.organization

        kwargs = {}
        if (hasattr(settings, 'STRIPE_CONNECT_CALLBACK_URL') and
            settings.STRIPE_CONNECT_CALLBACK_URL):
            kwargs = {
                'redirect_uri': settings.STRIPE_CONNECT_CALLBACK_URL,
            }
        authorize_url = self.processor_backend.get_authorize_url(
            provider, **kwargs)
        if authorize_url:
            update_context_urls(context, {
                'authorize_processor': authorize_url
            })
        if (hasattr(settings, 'STRIPE_TEST_CONNECT_CALLBACK_URL') and
            settings.STRIPE_TEST_CONNECT_CALLBACK_URL):
            authorize_url = self.processor_backend.get_authorize_url(
                provider, client_id=settings.STRIPE_TEST_CLIENT_ID,
                redirect_uri=settings.STRIPE_TEST_CONNECT_CALLBACK_URL)
            if authorize_url:
                update_context_urls(context, {
                    'authorize_processor_test': authorize_url
                })
        return context


class OrganizationProfileView(OrganizationProfileViewBase):

    def update_attached_user(self, form):
        validated_data = form.cleaned_data
        user = self.object.attached_user()
        if user:
            user.username = validated_data.get('slug', user.username)
            user.email = validated_data.get('email', user.email)
            full_name = validated_data.get('full_name')
            if full_name:
                #pylint:disable=unused-variable
                first_name, mid, last_name = full_name_natural_split(full_name)
                user.first_name = first_name
                user.last_name = last_name
            if update_db_row(user, form):
                raise ValidationError("update_attached_user (user)")
            contact = get_user_contact(self.object.attached_user())
            if contact:
                contact.slug = validated_data.get('slug', contact.slug)
                if full_name:
                    contact.full_name = full_name
                contact.email = validated_data.get('email', contact.email)
                contact.phone = validated_data.get('phone', contact.phone)
                contact.lang = validated_data.get('lang', contact.lang)
                if update_db_row(contact, form):
                    raise ValidationError("update_attached_user (contact)")
        return user

    def get_form_class(self):
        if self.object.attached_user():
            # There is only one user so we will add the User fields
            # to the form so they can be updated at the same time.
            return PersonalProfileForm
        return super(OrganizationProfileView, self).get_form_class()

    def get_initial(self):
        kwargs = super(OrganizationProfileView, self).get_initial()
        if self.object.attached_user():
            contact = get_user_contact(self.object.attached_user())
            if contact:
                kwargs.update({'lang': contact.lang})
        return kwargs


class RoleImplicitGrantAcceptView(ContextMixin, TemplateResponseMixin,
                                  RoleImplicitGrantAcceptViewBase):

    template_name = 'saas/users/roles/accept.html'

    def check_email_verified(self, request, user,
                             redirect_field_name=REDIRECT_FIELD_NAME,
                             next_url=None):
        return check_email_verified_base(request, user,
            redirect_field_name=redirect_field_name, next_url=next_url)

    def get_context_data(self, **kwargs):
        context = super(RoleImplicitGrantAcceptView, self).get_context_data(
            **kwargs)
        if self.role:
            context.update({
                'role': self.role,
                'contacts': ', '.join([user.get_full_name() for user
                    in self.role.organization.with_role(
                        saas_settings.MANAGER).exclude(
                            pk=self.request.user.pk)])
            })
        return context

    def get_implicit_grant_response(self, next_url, role, *args, **kwargs):
        self.role = role
        context = self.get_context_data(**kwargs)
        context.update({REDIRECT_FIELD_NAME: next_url})
        return self.render_to_response(context)


class StripeProcessorRedirectView(BaseStripeProcessorRedirectView):

    def get_redirect_url(self, *args, **kwargs):
        url = super(StripeProcessorRedirectView, self).get_redirect_url(
            *args, **kwargs)
        if self.request.path.endswith('/test/'):
            url += "&livemode=0"
        return url
