# Copyright (c) 2018, DjaoDjin inc.
# see LICENSE

import logging, os

from django.conf import settings
from django.http import Http404
from django.utils import six
from multitier.thread_locals import get_current_site
from multitier.mixins import  build_absolute_uri
from multitier.utils import get_site_model
from rules.utils import get_app_model
from saas.models import Subscription
from saas.utils import datetime_or_now

from .compat import reverse


LOGGER = logging.getLogger(__name__)


def is_streetside(site):
    if site.tag:
        return 'streetside' in site.tag
    return False


def is_testing(site):
    if site.slug in [settings.APP_NAME, '%s-master' % settings.APP_NAME]:
        return False
    if site.db_name == settings.DB_TEST:
        return True
    # We only want to automatically switch to testing if a subscription isn't
    # paid for mallspace. It is necessary for the on-boarding business logic.
    # In streetside, we prefer to avoid an extra query.
    # Implementation note:
    # We use ``organization_id=site.account_id`` such that Django does not
    # start generating queries with our djaodjin-master organization ids
    # into the streetside database.
    if not is_streetside(site):
        subscriptions = Subscription.objects.db_manager(using='default').filter(
            organization_id=site.account_id,
            ends_at__gt=datetime_or_now()).exclude(plan__slug='streetside')
        return not subscriptions.exists()
    return False


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
    if is_streetside(site):
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
    if not app:
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

    static_root = assets_dirs[0].split(os.sep)
    static_url = settings.STATIC_URL.split('/')
    if not static_root[-1]:
        static_root.pop()
    if not static_url[-1]:
        static_url.pop()
    nb_ident_parts = 0
    for root_part, url_part in six.moves.zip(
            reversed(static_root), reversed(static_url)):
        if root_part != url_part:
            break
        nb_ident_parts += 1
    parts = (static_root[:-nb_ident_parts] + [get_active_theme()])
    theme_dir = os.sep + os.path.join(*parts)

    assets_dirs = [
        theme_dir + settings.STATIC_URL[:-1], theme_dir] + list(assets_dirs)
    return assets_dirs


def get_active_theme():
    return get_current_site().slug


def is_current_broker(organization_slug):
    return (get_current_broker().slug == organization_slug
            and not is_testing(get_current_site()))


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
