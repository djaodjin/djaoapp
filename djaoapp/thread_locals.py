# Copyright (c) 2025, DjaoDjin inc.
# see LICENSE

import logging, os

from django.conf import settings
from django.db import DEFAULT_DB_ALIAS
from django.db.models import Q
from django.http import Http404
from extended_templates.utils import get_default_storage_base
from multitier.thread_locals import get_current_site
from multitier.mixins import build_absolute_uri as build_absolute_uri_base
from multitier.utils import get_site_model
from rules.utils import get_app_model, get_current_app
from saas import settings as saas_settings
from saas.utils import get_organization_model

from .compat import import_string, reverse, urljoin


LOGGER = logging.getLogger(__name__)


def is_platformed_site():
    #pylint:disable=protected-access
    return not get_current_broker()._state.db == DEFAULT_DB_ALIAS


def dynamic_processor_keys(provider, testmode=None):
    """
    Update the Stripe keys to use based on the database we are referring to.
    """
    #pylint:disable=unused-argument
    from saas.backends import load_backend
    processor_backend = load_backend(saas_settings.PROCESSOR['BACKEND'])

    if testmode is None:
        if provider.processor_pub_key:
            testmode = provider.processor_pub_key.startswith('pk_test_')

    if testmode:
        processor_backend.pub_key = settings.STRIPE_TEST_PUB_KEY
        processor_backend.priv_key = settings.STRIPE_TEST_PRIV_KEY
        processor_backend.client_id = settings.STRIPE_TEST_CLIENT_ID
        processor_backend.connect_callback_url = \
            settings.STRIPE_TEST_CONNECT_CALLBACK_URL

    return processor_backend


# same prototype as djaodjin-multitier.mixins.build_absolute_uri
def build_absolute_uri(location='/', request=None, site=None,
                       with_scheme=True, force_subdomain=False):
    """
    Returns an absolute URL for `location` on the site.

    Used to override SAAS['BROKER']['BUILD_ABSOLUTE_URI_CALLABLE']
    """
    # djaodjin-saas will pass the provider (of type Organization)
    # as the site argument, because that's the only clue it has.
    if site and isinstance(site, get_organization_model()):
        provider = site
        site_model = get_site_model()
        candidates = list(site_model.objects.filter(
            account=provider, domain__isnull=False))
        if candidates:
            site = candidates[0] # XXX works as long as domain
                                 #     is explicitely set.
        else:
            candidates = list(site_model.objects.filter(account=provider))
            if candidates:
                site = candidates[0] # XXX Testing on local systems
        LOGGER.debug("_provider_as_site(%s): %s", provider, site)

    if settings.BUILD_ABSOLUTE_URI_CALLABLE:
        return import_string(settings.BUILD_ABSOLUTE_URI_CALLABLE)(
            location=location, request=request, site=site,
            with_scheme=with_scheme, force_subdomain=force_subdomain)

    if request:
        return request.build_absolute_uri(location)

    return urljoin(settings.BASE_URL, location)


def djaoapp_get_current_app(request=None):
    """
    Used to override RULES['DEFAULT_APP_CALLABLE']
    """
    site = get_current_site()
    app = get_app_model().objects.filter(slug=site.slug).order_by(
        'path_prefix', '-pk').first()
    if not app:
        flt = Q(path_prefix__isnull=True)
        if request:
            request_path_parts = request.path.lstrip('/').split('/')
            if request_path_parts:
                flt = flt | Q(path_prefix='/%s' % request_path_parts[0])
        app = get_app_model().objects.filter(flt).order_by(
            'path_prefix', '-pk').first()
    return app



def get_current_broker():
    """
    Returns the provider ``Organization`` as read in the active database
    for the ``djaodjin-saas`` application.

    Used to override SAAS['BROKER']['GET_INSTANCE'] and
    EXTENDED_TEMPLATES['DEFAULT_ACCOUNT_CALLABLE']
    """
    # If we don't write the code as such, we might end-up generating
    # an extra SQL query every time ``get_current_broker`` is called.
    thread_local_site = get_current_site()
    if not thread_local_site:
        LOGGER.warning(
            "bypassing multitier and returning '%s' as broker, most likely"
            " because the execution environment is not bound to an HTTP"\
            " request.", settings.APP_NAME)
        return get_organization_model().objects.get(slug=settings.APP_NAME)
    broker = getattr(thread_local_site, 'broker', None)
    if not broker:
        # rules.App and saas.Organization are in the same database.
        thread_local_site.broker = get_current_app().account
        broker = thread_local_site.broker
    return broker


def get_current_assets_dirs():
    """
    Returns path to the root of static assets for an App.

    This function is used by premailer to inline applicable CSS.

    Used to override EXTENDED_TEMPLATES['ASSETS_DIRS_CALLABLE']
    """
    assets_dirs = [os.path.join(settings.PUBLIC_ROOT, get_current_theme()),
        settings.HTDOCS]

    return assets_dirs


def get_picture_storage(request, account=None):
    """
    Used to override SAAS['PICTURE_STORAGE_CALLABLE'] and
    SIGNUP['PICTURE_STORAGE_CALLABLE']
    """
    if not account:
        # We use `account` to generate a `key_prefix`.
        account = get_current_app(request)
    # By default profile pictures are public so they can be fetched
    # directly from S3 and do not need any specific authentication.
    return get_default_storage_base(request, account=account, public=True)


def get_default_storage(request, account=None):
    """
    Used to override EXTENDED_TEMPLATES['DEFAULT_STORAGE_CALLABLE']
    """
    if not account:
        # We use `account` to generate a `key_prefix`.
        account = get_current_app(request)
    return get_default_storage_base(request, account=account)


def get_current_theme():
    """
    Used to override EXTENDED_TEMPLATES['ACTIVE_THEME_CALLABLE']
    """
    return get_current_site().slug


def is_current_broker(organization):
    """
    Used to override SAAS['BROKER']['IS_INSTANCE_CALLABLE']
    """
    return get_current_broker().slug == str(organization)


def get_authorize_processor_state(processor, provider):
    """
    Returns site or site.provider as `state` query parameter for redirects.

    This function is executed in the context of the whitelabel's site.

    Used to override SAAS['PROCESSOR']['CONNECT_STATE_CALLABLE']
    """
    site = get_current_site()
    if not is_current_broker(provider):
        # Implementation note: '.' is neither part of a slug, nor url encoded
        # in query parameters. It is a good candidate for a separator between
        # a site's slug and a provider's slug.
        return "%s.%s" % (site, provider)
    return str(site)


def processor_redirect(request, site=None):
    """
    Full URL redirect after the processor connected the organization
    account with our system.

    This function is executed in the context of the callback's site.
    """
    # The `site` parameter is either a site's slug, or a site's slug and
    # provider's slug separated by a '.' (see `get_authorize_processor_state`).
    if site:
        parts = site.split('.')
        if len(parts) >= 2:
            site = parts[0]
            provider = parts[1]
        else:
            site_model = get_site_model()
            try:
                site = site_model.objects.get(slug=site)
                provider = site.account
            except site_model.DoesNotExist:
                #pylint:disable=protected-access
                raise Http404("No %s with slug '%s' can be found."
                    % (site_model._meta.object_name, site))
    else:
        provider = get_current_broker()
    return build_absolute_uri_base(location=reverse('saas_update_bank',
        kwargs={saas_settings.PROFILE_URL_KWARG: provider}),
        request=request, site=site)
