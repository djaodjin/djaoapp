# Copyright (c) 2018, DjaoDjin inc.
# see LICENSE
from __future__ import unicode_literals

import logging

from django.contrib.auth import get_user_model
from django.db import transaction, IntegrityError
from django.template.defaultfilters import slugify
from django.utils import six
from pages.locals import get_edition_tools_context_data
from rules.utils import get_current_app
from saas import settings as saas_settings
from saas.decorators import fail_direct
from saas.models import Organization, Plan, Signature
from signup.helpers import full_name_natural_split
from signup.utils import handle_uniq_error

from .compat import reverse
from .edition_tools import fail_edit_perm, inject_edition_tools


LOGGER = logging.getLogger(__name__)


class DjaoAppMixin(object):
    """
    Adds URL for next step in the wizard.
    """

    def add_edition_tools(self, response, context=None):
        """
        If the ``request.user`` has editable permissions, this method
        injects the edition tools into the html *content* and return
        a BeautifulSoup object of the resulting content + tools.

        If the response is editable according to the proxy rules, this
        method returns a BeautifulSoup object of the content such that
        ``PageMixin`` inserts the edited page elements.
        """
        if context is None:
            context = {}
        context.update(get_edition_tools_context_data())
        return inject_edition_tools(
            response, request=self.request, context=context)

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
        if self.request.user.is_authenticated():
            urls = {'user': {
                'logout': reverse('logout'),
                'profile': reverse('users_profile', args=(self.request.user,)),
            }}
        else:
            urls = {'user': {
               'login': reverse('login'),
               'login_github': reverse('social:begin', args=('github',)),
               'login_google': reverse('social:begin', args=('google-oauth2',)),
               'login_twitter': reverse('social:begin', args=('twitter',)),
               'password_reset': reverse('password_reset'),
               'register': reverse('registration_register'),
            }}
        # URLs for provider
        app = get_current_app()
        # ``app.account`` is guarenteed to be in the same database as ``app``.
        # ``site.account`` is always in the *default* database, which is not
        # the expected database ``Organization`` are typically queried from.
        provider = app.account
        if not fail_direct(self.request, organization=provider):
            urls.update({'provider': {
                'dashboard': reverse('saas_dashboard', args=(provider,)),
            }})
        if 'urls' in context:
            for key, val in six.iteritems(urls):
                if key in context['urls']:
                    context['urls'][key].update(val)
                else:
                    context['urls'].update({key: val})
        else:
            context.update({'urls': urls})
        return context


class RegisterMixin(object):

    registration_fields = (
        'first_name',
        'last_name',
        'full_name',
        'organization_name',
        'username',
        'password',
        'new_password1',
        'new_password2',
        'email',
        'username',
        'phone',
        'street_address',
        'locality',
        'region',
        'postal_code',
        'country'
    )

    def register_personal(self, **cleaned_data):
        """
        Registers both a User and an Organization at the same time
        with the added constraint that username and organization slug
        are identical such that it creates a transparent user billing profile.
        """
        return self.register_together(organization_selector='full_name',
            **cleaned_data)

    def register_together(self,
                          user_selector='full_name',
                          organization_selector='organization_name',
                          **cleaned_data):
        """
        Registers both a User and an Organization at the same time.
        """
        #pylint:disable=too-many-arguments,too-many-locals
        first_name = cleaned_data.get('first_name', "")
        last_name = cleaned_data.get('last_name', "")
        full_name = cleaned_data.get(user_selector,
            cleaned_data.get('full_name', None))
        if not first_name:
            # If the form does not contain a first_name/last_name pair,
            # we assume a full_name was passed instead.
            first_name, _, last_name = full_name_natural_split(full_name)
        if not full_name:
            full_name = ("%s %s" % (first_name, last_name)).strip()
        organization_extra = {}
        role_extra = {}
        user_extra = {}
        for field_name, field_value in six.iteritems(cleaned_data):
            if field_name not in self.registration_fields:
                if field_name.startswith('organization_'):
                    organization_extra.update({field_name[13:]: field_value})
                if field_name.startswith('role_'):
                    role_extra.update({field_name[5:]: field_value})
                if field_name.startswith('user_'):
                    user_extra.update({field_name[5:]: field_value})
        if not organization_extra:
            organization_extra = None
        if not role_extra:
            role_extra = None
        if not user_extra:
            user_extra = None

        username = cleaned_data.get('username', None)
        password = cleaned_data.get('password',
            cleaned_data.get('new_password1', None))
        organization_name = cleaned_data.get(organization_selector, full_name)
        if user_selector == organization_selector:
            # We have a personal registration
            organization_slug = username
        else:
            organization_slug = slugify(organization_name)

        try:
            with transaction.atomic():
                # Create a ``User``
                user = get_user_model().objects.create_user(
                    username=username,
                    password=password,
                    email=cleaned_data.get('email', None),
                    first_name=first_name,
                    last_name=last_name)

                Signature.objects.create_signature(
                    saas_settings.TERMS_OF_USE, user)

                # Create an ``Organization`` and set the user as its manager.
                account = Organization.objects.create(
                    slug=organization_slug,
                    full_name=organization_name,
                    email=cleaned_data.get('email', None),
                    phone=cleaned_data.get('phone', ""),
                    street_address=cleaned_data.get('street_address', ""),
                    locality=cleaned_data.get('locality', ""),
                    region=cleaned_data.get('region', ""),
                    postal_code=cleaned_data.get('postal_code', ""),
                    country=cleaned_data.get('country', ""),
                    extra=organization_extra)
                account.add_manager(user, extra=role_extra)
                LOGGER.info("created organization '%s' with"\
                    " full name: '%s', email: '%s', phone: '%s',"\
                    " street_address: '%s', locality: '%s', region: '%s',"\
                    " postal_code: '%s', country: '%s'.", account.slug,
                    account.full_name, account.email, account.phone,
                    account.street_address, account.locality, account.region,
                    account.postal_code, account.country,
                    extra={'event': 'create',
                        'request': self.request, 'user': user,
                        'type': 'Organization', 'slug': account.slug,
                        'full_name': account.full_name, 'email': account.email,
                        'street_address': account.street_address,
                        'locality': account.locality, 'region': account.region,
                        'postal_code': account.postal_code,
                        'country': account.country})
        except IntegrityError as err:
            handle_uniq_error(err)

        # Sign-in the newly registered user, bypassing authentication here,
        # since we might have a frictionless registration.
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        return user
