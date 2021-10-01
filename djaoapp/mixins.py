# Copyright (c) 2021, DjaoDjin inc.
# see LICENSE
from __future__ import unicode_literals

import logging

from deployutils.apps.django.compat import is_authenticated
from django.db import transaction, IntegrityError
from django.template.defaultfilters import slugify
from django.utils.translation import ugettext_lazy as _
from rest_framework.exceptions import ValidationError
from rules.utils import get_current_app
from saas import settings as saas_settings
from saas.decorators import fail_direct
from saas.models import Agreement, Organization, Plan, Signature, get_broker
from signup.helpers import full_name_natural_split
from signup.utils import handle_uniq_error

from .compat import reverse, six
from .edition_tools import fail_edit_perm


LOGGER = logging.getLogger(__name__)

def _clean_field(cleaned_data, field_name):
    """
    This insures that `NOT NULL` fields have a value of "" instead of `None`.
    """
    field = cleaned_data.get(field_name, "")
    if field is None:
        field = ""
    return field


class DjaoAppMixin(object):
    """
    Adds URL for next step in the wizard.
    """

    def add_edition_tools(self, response, context=None):
        # The edition tools will already be injected through
        # the url decorator (`inject_edition_tools` defined in decorators.py)
        # as it is added to `url_prefixed` in urlbuilders.py
        #pylint:disable=unused-argument,no-self-use
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
            #pylint:disable=unused-variable
            first_name, mid, last_name = full_name_natural_split(full_name)
        if not full_name:
            full_name = ("%s %s" % (first_name, last_name)).strip()

        organization_name = cleaned_data.get(organization_selector, full_name)

        organization_extra = {}
        role_extra = {}
        for field_name, field_value in six.iteritems(cleaned_data):
            if field_name not in self.registration_fields:
                if field_name.startswith('organization_'):
                    organization_extra.update({field_name[13:]: field_value})
                if field_name.startswith('role_'):
                    role_extra.update({field_name[5:]: field_value})
        if not organization_extra:
            organization_extra = None
        if not role_extra:
            role_extra = None

        try:
            with transaction.atomic():
                # Create a ``User``
                user = self.register_user(**cleaned_data)
                if user_selector == organization_selector:
                    # We have a personal registration
                    organization_slug = user.username
                else:
                    organization_slug = slugify(organization_name)
                if not organization_slug:
                    raise ValidationError({organization_selector:
                        _("The organization name must contain"\
                        " some alphabetical characters.")})

                # Create an ``Organization`` and set the user as its manager.
                organization_kwargs = {}
                if ('type' in cleaned_data and
                    cleaned_data['type'] == Organization.ACCOUNT_PROVIDER):
                    organization_kwargs = {'is_provider': True}
                account = Organization.objects.create(
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
                        'type': 'Organization', 'slug': account.slug,
                        'full_name': account.full_name,
                        'email': account.email,
                        'street_address': account.street_address,
                        'locality': account.locality,
                        'region': account.region,
                        'postal_code': account.postal_code,
                        'country': account.country})
        except IntegrityError as err:
            handle_uniq_error(err, renames={'slug': organization_selector})

        return user

    def register_user(self, **cleaned_data):
        agreements = list(Agreement.objects.filter(
            slug__in=six.iterkeys(cleaned_data)))
        for agreement in agreements:
            not_signed = cleaned_data.get(agreement.slug, "").lower() in [
                'false', 'f', '0']
            if not_signed:
                raise ValidationError({agreement.slug:
                    _("You must read and agree to the %(agreement)s.") % {
                    'agreement': agreement.title}})

        user = super(RegisterMixin, self).register_user(**cleaned_data)
        if user:
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            for agreement in agreements:
                Signature.objects.create_signature(agreement.slug, user)

        return user


class NotificationsMixin(object):

    @staticmethod
    def get_notifications(user=None):
        broker = get_broker()
        notifications = {
            'card_updated': {
                'title': _("Card updated"),
                'descr': _("This notification is sent when a credit card"\
" on file is updated.")
            },
            'charge_receipt': {
                'title': _("Charge receipt"),
                'descr': _("This notification is sent when a charge is"\
" created on a credit card. It is also sent when the charge is refunded.")
            },
            'claim_code_generated': {
                'title': _("Claim code"),
                'descr': _("This notification is sent to the user invited"\
" through a groupBuy.")
            },
            'expires_soon': {
                'title': _("Expires soon"),
                'descr': _("This notification is sent when a subscription"\
" is about to expire.")
            },
            'order_executed': {
                'title': _("Order confirmation"),
                'descr': _("This notification is sent when an order has"\
" been confirmed but a charge has not been successfully processed yet.")
            },
            'organization_updated': {
                'title': _("Profile updated"),
                'descr': _("This notification is sent when a profile"\
" is updated.")
            },
            'password_reset': {
                'title': _("Password reset"),
                'descr': _("This notification is sent to a user that has"\
" requested to reset their password through a \"forgot password?\" link.")
            },
            'user_activated': {
                'title': _("User activated"),
                'descr': _("This notification is sent to profile managers"\
" of a domain when a user has activated his/her account.")
                },
            'user_contact': {
                'title': _("User contact"),
                'descr': _("This notification is sent to profile managers"\
" of a domain when a user submits an inquiry on the contact-us page.")
            },
            'user_registered': {
                'title': _("User registered"),
                'descr': _("This notification is sent to profile managers"\
" of a domain when a user has registered.")
            },
            'user_welcome': {
                'title': _("Welcome e-mail"),
                'descr': _("This notification is sent to a user after they"\
" register an account with the site."),
            },
            'role_request_created': {
                'title': _("Role requested"),
                'descr': _("This notification is sent to profile managers"\
" of an organization when a user has requested a role on that organization.")
                },
            'verification': {
                'title': _("Verification"),
                'descr': _("This notification is sent to verify an e-mail"\
" address of a user.")
            },
            'sales_report': {
                'title': _("Weekly sales report"),
                'descr': _("This notification is sent to profile managers."\
" It contains the weekly sales results.")
            },
        }
        for role_descr in broker.get_role_descriptions():
            notifications.update({"%s_role_grant_created" % role_descr.slug: {
                'title': _("%(role_title)s Added") % {
                    'role_title': role_descr.title},
                'descr': ""
            }})

        # user with profile manager of broker (or theme editor)
        if not user or broker.with_role(
                saas_settings.MANAGER).filter(pk=user.pk).exists():
            return notifications

        # regular subscriber
        return {key: notifications[key] for key in [
            'charge_receipt', 'card_updated', 'order_executed',
            'organization_updated', 'expires_soon']}
