# Copyright (c) 2025, DjaoDjin inc.
# see LICENSE
from __future__ import unicode_literals

import logging

from deployutils.apps.django_deployutils.compat import is_authenticated
from django.contrib.auth import get_backends, get_user_model
from django.db import router, transaction
from django.template.defaultfilters import slugify
from rest_framework.exceptions import ValidationError
from rules import signals as rules_signals
from rules.utils import get_current_app
from saas import settings as saas_settings
from saas.helpers import update_context_urls
from saas.models import Agreement, Organization, Plan, Signature, get_broker
from saas.utils import get_organization_model
from signup.models import Notification

from .compat import gettext_lazy as _, reverse, six
from .edition_tools import fail_edit_perm
from .utils import (PERSONAL_REGISTRATION, TOGETHER_REGISTRATION,
    USER_REGISTRATION)


LOGGER = logging.getLogger(__name__)

def _clean_field(cleaned_data, field_name):
    """
    This insures that `NOT NULL` fields have a value of "" instead of `None`.
    """
    field = cleaned_data.get(field_name, "")
    if field is None:
        field = ""
    return field


def social_login_urls():
    urls = {}
    for backend in get_backends():
        name = getattr(backend, 'name', None)
        if name:
            urls.update({'login_%s' % name.replace('-', '_'): reverse(
                'social:begin', args=(name,))})
    return urls


class AuthMixin(object):

    registration_fields = (
        'country',
        'email',
        'first_name',
        'full_name',
        'lang',
        'last_name',
        'locality',
        'postal_code',
        'new_password',
        'new_password2',
        'organization_name',
        'password',
        'phone',
        'region',
        'street_address',
        'username',
    )

    organization_model = get_organization_model()

    def register_check_data(self, **cleaned_data):
        errors = {}
        try:
            super(AuthMixin, self).register_check_data(**cleaned_data)
        except ValidationError as err:
            errors = err.detail

        self.agreements = list(Agreement.objects.filter(
            slug__in=six.iterkeys(cleaned_data)))
        for agreement in self.agreements:
            try:
                # In case we have a string instead of a bool.
                not_signed = cleaned_data.get(agreement.slug, "").lower() in [
                    'false', 'f', '0']
            except AttributeError:
                not_signed = not cleaned_data.get(agreement.slug, False)
            if not_signed:
                errors.update({agreement.slug:
                    _("You must read and agree to the %(agreement)s.") % {
                    'agreement': agreement.title}})

        if errors:
            raise ValidationError(errors)

    def register_finalize(self, user, **cleaned_data):
        #pylint:disable=unused-argument
        for agreement in self.agreements:
            Signature.objects.create_signature(agreement, user)


    def create_models(self, *args, **cleaned_data):
        #pylint:disable=too-many-locals
        # We use the following line to understand better what kind of data
        # bad bots post to a registration form.
        LOGGER.debug("calling djaoapp.AuthMixin.create_models(**%s)",
            str({field_name: ('*****' if field_name.startswith('password')
            else val) for field_name, val in six.iteritems(cleaned_data)}))
        registration = USER_REGISTRATION
        user_selector = 'full_name'
        organization_selector = 'organization_name'
        full_name = cleaned_data.get('full_name', None)
        if 'organization_name' in cleaned_data:
            # We have a registration of a user and organization together.
            registration = TOGETHER_REGISTRATION
            organization_name = cleaned_data.get('organization_name', None)
            if full_name and full_name == organization_name:
                # No we have a personal registration after all
                registration = PERSONAL_REGISTRATION
                organization_selector = 'full_name'
        elif (cleaned_data.get('street_address', None) or
            cleaned_data.get('locality', None) or
            cleaned_data.get('region', None) or
            cleaned_data.get('postal_code', None) or
            cleaned_data.get('country', None)):
            # XXX We have enough information for a billing profile but it might
            # not be a good idea to force it here. Maybe using a registration
            # 'type' field is more appropriate.
            registration = PERSONAL_REGISTRATION
            organization_selector = 'full_name'

        self.renames = {'slug': organization_selector}
        with transaction.atomic(using=router.db_for_write(get_user_model())):
            # Create a ``User``
            username = args[0]
            organization = self.organization_model.objects.filter(
                slug__iexact=username)
            if organization.exists():
                # If an `Organization` with slug == username exists,
                # it is bound to create problems later on.
                raise ValidationError({'username':
                    _("A profile with that %(username)s already exists.") % {
                        'username': 'username'}})
            user = super(AuthMixin, self).create_models(*args, **cleaned_data)

            if registration in (PERSONAL_REGISTRATION,
                                TOGETHER_REGISTRATION):
                # Registers both a User and an Organization at the same time
                # with the added constraint that username and organization
                # slug are identical such that it creates a transparent
                # user billing profile.
                first_name = cleaned_data.get('first_name', "")
                last_name = cleaned_data.get('last_name', "")
                full_name = cleaned_data.get(user_selector,
                    cleaned_data.get('full_name', None))
                if not full_name:
                    full_name = ' '.join([
                        first_name if first_name else "",
                        last_name if last_name else ""]).strip()
                organization_name = cleaned_data.get(
                    organization_selector, full_name)
                organization_extra = {}
                role_extra = {}
                for field_name, field_value in six.iteritems(cleaned_data):
                    if field_name not in self.registration_fields:
                        if field_name.startswith('organization_'):
                            organization_extra.update({
                                field_name[13:]: field_value})
                        if field_name.startswith('role_'):
                            role_extra.update({field_name[5:]: field_value})
                if not organization_extra:
                    organization_extra = None
                if not role_extra:
                    role_extra = None
                if user_selector == organization_selector:
                    # We have a personal registration
                    organization_slug = user.username
                else:
                    organization_slug = slugify(organization_name)
                if not organization_slug:
                    raise ValidationError({organization_selector:
                        _("The organization name must contain"\
                        " some alphabetical characters.")})

                # Create an ``Organization`` and set the user
                # as its manager.
                organization_kwargs = {}
                if ('type' in cleaned_data and
                    cleaned_data['type'] == Organization.ACCOUNT_PROVIDER):
                    organization_kwargs = {'is_provider': True}
                account = self.organization_model.objects.create(
                    slug=organization_slug,
                    full_name=organization_name,
                    email=_clean_field(cleaned_data, 'email'),
                    phone=_clean_field(cleaned_data, 'phone'),
                    street_address=_clean_field(
                        cleaned_data, 'street_address'),
                    locality=_clean_field(cleaned_data, 'locality'),
                    region=_clean_field(cleaned_data, 'region'),
                    postal_code=_clean_field(cleaned_data, 'postal_code'),
                    country=_clean_field(cleaned_data, 'country'),
                    extra=organization_extra,
                    **organization_kwargs)
                account.add_manager(user, extra=role_extra)
                LOGGER.info("created organization '%s' with"\
                    " full name: '%s', email: '%s', phone: '%s',"\
                    " street_address: '%s', locality: '%s', region: '%s',"\
                    " postal_code: '%s', country: '%s'.", account.slug,
                    account.full_name, account.email, account.phone,
                    account.street_address, account.locality,
                    account.region, account.postal_code, account.country,
                    extra={'event': 'create',
                        'request': self.request, 'user': user,
                        'type': 'organization', 'slug': account.slug,
                        'full_name': account.full_name,
                        'email': account.email,
                        'street_address': account.street_address,
                        'locality': account.locality,
                        'region': account.region,
                        'postal_code': account.postal_code,
                        'country': account.country})

        app = get_current_app()
        if app.welcome_email:
            rules_signals.user_welcome.send(sender=__name__, user=user,
                request=self.request)

        return user

    def get_context_data(self, **kwargs):
        context = super(AuthMixin, self).get_context_data(**kwargs)
        # URLs for user
        if not is_authenticated(self.request):
            user_urls = social_login_urls()
            update_context_urls(context, {'user': user_urls})
        update_context_urls(context, {
            'pricing': reverse('saas_cart_plan_list')})
        return context


class DjaoAppMixin(object):
    """
    Adds URL for next step in the wizard.
    """

    def add_edition_tools(self, response, context=None):
        # The edition tools will already be injected through
        # the url decorator (`inject_edition_tools` defined in decorators.py)
        # as it is added to `url_prefixed` in urlbuilders.py
        #pylint:disable=unused-argument
        return None

    @property
    def edit_perm(self):
        if not hasattr(self, '_edit_perm'):
            self._edit_perm = not fail_edit_perm(self.request)
        return self._edit_perm

    def get_context_data(self, **kwargs):
        context = super(DjaoAppMixin, self).get_context_data(**kwargs)
        context.update({'edit_perm': self.edit_perm}) # XXX _appmenu.html
        if self.organization:
            if not Plan.objects.filter(
                    organization=self.organization).exists():
                context.update({'next_url': reverse('saas_cart_plan_list')})
        # URLs for user
        if is_authenticated(self.request):
            update_context_urls(context, {'user': {
                'logout': reverse('logout'),
                'profile': reverse('users_profile', args=(self.request.user,)),
            }})
        else:
            login_urls = social_login_urls()
            login_urls.update({
                'login': reverse('login'),
            })
            update_context_urls(context, {'user': login_urls})
        return context


class NotificationsMixin(object):

    def get_notifications(self, user=None):
        from .api_docs.views import NotificationDocGenerator
        notifications = {obj.slug: {
            'summary': obj.title,
            'description': obj.description}
                for obj in Notification.objects.all()}

        generator = NotificationDocGenerator()
        schema = generator.get_schema(request=self.request)
        notifications.update({notification_slug: {
            'summary': notification.get('GET').get('summary'),
            'description': notification.get('GET').get('description')}
            for notification_slug, notification in schema.get('paths').items()})
        # user with profile manager of broker (or theme editor), we do not
        # filter notifications.
        broker = get_broker()
        if user and not broker.with_role(
                saas_settings.MANAGER).filter(pk=user.pk).exists():
            # regular subscriber
            notifications = {key: notifications[key]
                for key in notifications if key not in [
                    'user_contact', 'user_registered', 'user_activated',
                    'period_sales_report_created', 'processor_setup_error']}

        return notifications
