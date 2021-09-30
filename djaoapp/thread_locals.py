# Copyright (c) 2021, DjaoDjin inc.
# see LICENSE

import logging

from django.conf import settings
from django.http import Http404
from multitier.thread_locals import get_current_site
from multitier.mixins import build_absolute_uri
from multitier.utils import get_site_model
from multitier.finders import get_current_theme_assets_dirs
from pages.utils import get_default_storage_base
from rules.utils import get_app_model
from saas.decorators import _valid_manager
from saas.utils import get_organization_model

from .compat import reverse


LOGGER = logging.getLogger(__name__)

def is_domain_site(site):
    return site.tag and 'streetside' in site.tag
                                    # XXX should be not site.is_path_prefix
                                    # but we are using is_path_prefix for local
                                    # dev.

def is_testing(site):
    return site.tag and 'testing' in site.tag


def dynamic_processor_keys(provider):#pylint:disable=unused-argument
    """
    Update the Stripe keys to use based on the database we are referring to.
    """
    from saas.backends import load_backend
    processor_backend = load_backend(
        settings.SAAS.get('PROCESSOR', {
            'BACKEND': 'saas.backends.stripe_processor.StripeBackend'
        }).get('BACKEND', 'saas.backends.stripe_processor.StripeBackend'))
    site = get_current_site()
    if is_domain_site(site):
        processor_backend.mode = processor_backend.REMOTE
    if is_testing(site):
        processor_backend.pub_key = settings.STRIPE_TEST_PUB_KEY
        processor_backend.priv_key = settings.STRIPE_TEST_PRIV_KEY
        processor_backend.client_id = settings.STRIPE_TEST_CLIENT_ID
    return processor_backend


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
    for the ``rules`` and ``pages`` application.
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
    assets_dirs = getattr(settings, 'STATICFILES_DIRS', None)
    if not assets_dirs:
        static_root_path = getattr(settings, 'STATIC_ROOT', None)
        if static_root_path:
            assets_dirs = [static_root_path]

    assets_dirs = get_current_theme_assets_dirs() + list(assets_dirs)

    return assets_dirs


def get_default_storage(request, account=None):
    # pylint:disable=unused-argument
    # XXX use `account` to generate `key_prefix`.
    return get_default_storage_base(request, account=get_current_app(request))


def get_active_theme():
    return get_current_site().slug


def get_disabled_authentication(request):
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
    # returns site slug as `state` for redirects.
    site = _provider_as_site(provider)
    if not site:
        # We force a valid state instead of `None`.
        site = provider
    return str(site)


def processor_redirect(request, site=None):
    """
    Full URL redirect after the processor connected the organization
    account with our system.
    """
    site_model = get_site_model()
    if site is None:
        site = get_current_site()
    elif not isinstance(site, site_model):
        try:
            site = site_model.objects.get(slug=site)
        except site_model.DoesNotExist:
            #pylint:disable=protected-access
            raise Http404("No %s with slug '%s' can be found."
                % (site_model._meta.object_name, site))
    return build_absolute_uri(request, location=reverse('saas_update_bank',
        kwargs={'organization': site.account}), site=site)


def provider_absolute_url(request,
                          location='/', provider=None, with_scheme=True):
    site = _provider_as_site(provider)
    if site:
        try:
            # If `site == get_current_site()`, we have a full-proof way
            # to generate the absolute URL with either a domain name or
            # a path prefix depending on the request.
            return site.as_absolute_uri(path=location)
        except AttributeError:
            # OK, we'll use the default build_absolute_uri from multitier.
            pass
    return build_absolute_uri(request, site=site,
        location=location, with_scheme=with_scheme)
