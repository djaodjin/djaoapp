# Copyright (c) 2018, DjaoDjin inc.
# see LICENSE

"""
Functions used to inject edition tools within an HTML response.
"""
import logging

from django.conf import settings
from django.core.files.storage import get_storage_class
from multitier.thread_locals import get_current_site
from multitier.mixins import build_absolute_uri
from pages.views.pages import inject_edition_tools as pages_inject_edition_tools
from rules.utils import get_current_app
from saas.decorators import _valid_manager

from .compat import csrf, reverse
from .locals import is_streetside, is_testing


LOGGER = logging.getLogger(__name__)


def djaoapp_urls(request, account=None, base=None):
    if account is None:
        account = get_current_app().account
    urls = {
        'pricing': build_absolute_uri(request, location='/pricing/',
            site=settings.APP_NAME),
        'cart': build_absolute_uri(request,
            location='/billing/%s/cart/' % account,
            site=settings.APP_NAME)}
    if base:
        urls.update({'app':
            build_absolute_uri(request, location='/app/%s/' % base,
            site=settings.APP_NAME)})
    return urls


def fail_edit_perm(request, account=None):
    """
    Returns ``True`` if the request user does not have edit permissions.
    """
    result = True
    # The context processor will be called from the e-mail sender
    # which might not be associated to a request.
    if request is not None:
        if account is None:
            account = get_current_app().account
        result = not bool(_valid_manager(request, [account]))
    return result


def has_bank_account(broker):
    return (broker.slug == settings.APP_NAME
            or broker.has_bank_account)


def inject_edition_tools(response, request, context=None,
                         body_top_template_name=None,
                         body_bottom_template_name=None):
    """
    If the ``request.user`` has editable permissions, this method
    injects the edition tools into the html *content* and return
    a BeautifulSoup object of the resulting content + tools.

    If the response is editable according to the proxy rules, this
    method returns a BeautifulSoup object of the content such that
    ``PageMixin`` inserts the edited page elements.
    """
    #pylint:disable=too-many-locals
    if context is None:
        context = {}
    dj_urls = {}
    edit_urls = {}
    provider_urls = {}
    site = get_current_site()
    app = get_current_app()
    # ``app.account`` is guarenteed to be in the same database as ``app``.
    # ``site.account`` is always in the *default* database, which is not
    # the expected database ``Organization`` are typically queried from.
    provider = app.account
    enable_code_editor = False
    edit_urls = {
        'api_medias': reverse('uploaded_media_elements', kwargs={'path':''}),
        'api_sitecss': reverse('edit_sitecss'),
        'api_less_overrides': reverse('pages_api_less_overrides'),
        'api_sources': reverse('pages_api_sources'),
        'api_page_elements': reverse('page_elements'),
        'api_plans': reverse(
            'saas_api_plans', args=(provider,)),
        'plan_update_base': reverse(
            'saas_plan_base', args=(provider,))}

    if not fail_edit_perm(request, account=provider):
        if is_testing(site):
            if has_bank_account(provider):
                body_top_template_name = "pages/_body_top_testing_manager.html"
            else:
                provider_urls = {
                    'bank': reverse('saas_update_bank', args=(provider,))}
                body_top_template_name = \
                    "pages/_body_top_testing_no_processor_manager.html"
        elif not has_bank_account(provider) and (
                request and request.path.endswith('/cart/')):
            provider_urls = {
                'bank': reverse('saas_update_bank', args=(provider,))}
            body_top_template_name = "pages/_body_top_no_processor_manager.html"
        try:
            # The following statement will raise an Exception
            # when we are dealing with a ``FileSystemStorage``.
            _ = get_storage_class().bucket_name
            edit_urls.update({'media_upload': reverse('api_credentials')})
        except AttributeError:
            LOGGER.debug("doesn't look like we have a S3Storage.")
        # XXX ``is_streetside(site)`` shouldn't disable all edit functionality.
        # Just the edition of templates.
        enable_code_editor = is_streetside(site)
        if enable_code_editor:
            dj_urls = djaoapp_urls(
                request, account=provider, base=site.as_base())
            body_bottom_template_name = "pages/_body_bottom_edit_tools.html"
        else:
            dj_urls = djaoapp_urls(request, account=provider)
            body_bottom_template_name = "pages/_body_bottom.html"
    else:
        if is_testing(site):
            if has_bank_account(provider):
                body_top_template_name = "pages/_body_top_testing.html"
            else:
                body_top_template_name \
                    = "pages/_body_top_testing_no_processor.html"
        elif not has_bank_account(provider) and (
                request and request.path.endswith('/cart/')):
            body_top_template_name = "pages/_body_top_no_processor.html"
    if not (body_top_template_name or body_bottom_template_name):
        return None
    context.update({
        'ENABLE_CODE_EDITOR': enable_code_editor,
        'FEATURE_DEBUG': settings.FEATURES_DEBUG,
        'urls':{
            'provider': provider_urls,
            'djaodjin': dj_urls,
            'edit': edit_urls}})
    context.update(csrf(request))
    return pages_inject_edition_tools(response, request, context=context,
        body_top_template_name=body_top_template_name,
        body_bottom_template_name=body_bottom_template_name)
