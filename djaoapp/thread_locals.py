# Copyright (c) 2023, DjaoDjin inc.
# see LICENSE

import logging, os

from django.conf import settings
from django.db import DEFAULT_DB_ALIAS
from django.http import Http404
from extended_templates.utils import get_default_storage_base
from multitier.thread_locals import get_current_site
from multitier.mixins import build_absolute_uri
from multitier.utils import get_site_model
from rules.models import Rule
from rules.utils import get_app_model
from saas import settings as saas_settings
from saas.decorators import _valid_manager
from saas.utils import get_organization_model

from .compat import reverse


LOGGER = logging.getLogger(__name__)

def is_platformed_site():
    #pylint:disable=protected-access
    return not (get_current_broker()._state.db == DEFAULT_DB_ALIAS)

def is_testing(site):
    return site.tag and 'testing' in site.tag


def dynamic_processor_keys(provider, livemode=None):
    """
    Update the Stripe keys to use based on the database we are referring to.
    """
    #pylint:disable=unused-argument
    from saas.backends import load_backend
    processor_backend = load_backend(
        settings.SAAS.get('PROCESSOR', {
            'BACKEND': 'saas.backends.stripe_processor.StripeBackend'
        }).get('BACKEND', 'saas.backends.stripe_processor.StripeBackend'))
    site = get_current_site()
    if livemode is None:
        if provider.processor_pub_key:
            livemode = provider.processor_pub_key.startswith('pk_live_')
        else:
            livemode = bool(not is_testing(site))

    if livemode:
        try:
            if site.processor_client_key:
                processor_backend.pub_key = site.processor_pub_key
                processor_backend.priv_key = site.processor_priv_key
                processor_backend.client_id = site.processor_client_key
                processor_backend.connect_callback_url = \
                    site.connect_callback_url
            elif is_current_broker(provider) and is_platformed_site():
                # if we are using platform keys but the site is not
                # the platform, we override the Stripe Connect mode
                # to be REMOTE.
                processor_backend.mode = processor_backend.REMOTE
        except AttributeError:
            pass
    else:
        processor_backend.pub_key = settings.STRIPE_TEST_PUB_KEY
        processor_backend.priv_key = settings.STRIPE_TEST_PRIV_KEY
        processor_backend.client_id = settings.STRIPE_TEST_CLIENT_ID
        processor_backend.connect_callback_url = \
            settings.STRIPE_TEST_CONNECT_CALLBACK_URL
        try:
            if site.processor_test_client_key:
                processor_backend.pub_key = site.processor_test_pub_key
                processor_backend.priv_key = site.processor_test_priv_key
                processor_backend.client_id = site.processor_test_client_key
                processor_backend.connect_callback_url = \
                    site.processor_test_connect_callback_url
            elif is_current_broker(provider) and is_platformed_site():
                # if we are using platform keys but the site is not
                # the platform, we override the Stripe Connect mode
                # to be REMOTE.
                processor_backend.mode = processor_backend.REMOTE
        except AttributeError:
            pass

    return processor_backend


def enables_processor_test_keys(request=None):
    site = get_current_site()
    if hasattr(site, 'enables_processor_test_keys'):
        return site.enables_processor_test_keys
    return bool(settings.ENABLES_PROCESSOR_TEST_KEYS)


def get_current_broker():
    """
    Returns the provider ``Organization`` as read in the active database
    for the ``djaodjin-saas`` application.
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


def get_current_app(request=None):
    """
    Returns the provider ``rules.App`` as read in the active database
    for the ``rules`` and ``extended_templates`` application.
    """
    # If we don't write the code as such, we might end-up generating
    # an extra SQL query every time ``get_current_app`` is called.
    thread_local_site = get_current_site()
    app = getattr(thread_local_site, 'app', None)
    if thread_local_site and not app:
        app_model = get_app_model()
        try:
            thread_local_site.app = app_model.objects.get(
                slug=thread_local_site.slug)
        except app_model.DoesNotExist:
            #pylint:disable=protected-access
            msg = "No %s with slug '%s' can be found." % (
                app_model._meta.object_name, thread_local_site.slug)
            if request is not None:
                LOGGER.exception(
                    "get_current_app: %s", msg, extra={'request': request})
            else:
                LOGGER.exception("get_current_app: %s", msg)
            raise Http404(msg)
        app = thread_local_site.app
    return app


def get_current_assets_dirs():
    """
    Returns path to the root of static assets for an App.

    This function is used by premailer to inline applicable CSS.
    """
    assets_dirs = [os.path.join(settings.PUBLIC_ROOT, get_active_theme()),
        settings.HTDOCS]

    return assets_dirs


def get_picture_storage(request, account=None):
    if not account:
        # We use `account` to generate a `key_prefix`.
        account = get_current_app(request)
    # By default profile pictures are public so they can be fetched
    # directly from S3 and do not need any specific authentication.
    return get_default_storage_base(request, account=account, public=True)


def get_default_storage(request, account=None):
    if not account:
        # We use `account` to generate a `key_prefix`.
        account = get_current_app(request)
    return get_default_storage_base(request, account=account)


def get_active_theme():
    return get_current_site().slug


def get_disabled_authentication(request, user):
    app = get_current_app()
    return (app.authentication == app.AUTH_DISABLED
        and not _valid_manager(request, [get_current_broker()]))


def get_disabled_registration(request):#pylint:disable=unused-argument
    app = get_current_app()
    return app.authentication != app.AUTH_ENABLED


def is_current_broker(organization):
    return get_current_broker().slug == str(organization)


def _provider_as_site(provider):
    site = None
    if not provider or is_current_broker(provider):
        site = get_current_site()
    else:
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
    return site


def get_authorize_processor_state(processor, provider):
    """
    Returns site or site.provider as `state` query parameter for redirects.

    This function is executed in the context of the whitelabel's site.
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
    return build_absolute_uri(request, location=reverse('saas_update_bank',
        kwargs={saas_settings.PROFILE_URL_KWARG: provider}), site=site)


def product_url(subscriber=None, plan=None, request=None):
    location = None
    if plan:
        candidate_rule = Rule.objects.filter(
            app=get_current_app(request),
            kwargs__contains=str(plan)).order_by('-rank').first()
        if candidate_rule:
            location = candidate_rule.path.replace(
                '{profile}', str(subscriber)).replace(
                '{plan}',  str(plan))
    if not location:
        location = reverse('product_default_start')
        if subscriber:
            location += '%s/' % subscriber
        if plan:
            location += '%s/' % plan
    site = get_current_site()
    if request:
        return build_absolute_uri(request, location=location, site=site)
    # We don't have a request, so we return a URL path such that the host
    # is correctly inferred by the browser.
    if site.is_path_prefix:
        location = "/%s%s" % (site.slug, location)
    return location


def provider_absolute_url(request,
                          location='/', provider=None, with_scheme=True):
    site = _provider_as_site(provider)
    if site:
        try:
            # If `site == get_current_site()`, we have a full-proof way
            # to generate the absolute URL with either a domain name or
            # a path prefix depending on the request.
            return site.as_absolute_uri(location=location)
        except AttributeError:
            # OK, we'll use the default build_absolute_uri from multitier.
            pass
    return build_absolute_uri(request, location=location,
        site=site, with_scheme=with_scheme)
