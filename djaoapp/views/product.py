# Copyright (c) 2018, DjaoDjin inc.
# see LICENSE

"""
Default start page for a djaodjin-hosted product.
"""

import logging

from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from django.contrib import messages
from django.contrib.staticfiles.views import serve as debug_serve
from django.http import Http404
from django.template import TemplateDoesNotExist
from django.template.loader import get_template
from django.template.response import TemplateResponse
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from django.views.static import serve

from multitier.mixins import build_absolute_uri
from multitier.thread_locals import get_current_site
from pages.views.pages import PageMixin
from saas.decorators import fail_direct
from saas.mixins import UserMixin
from saas.models import ChargeItem, Plan, get_broker
from saas.utils import get_organization_model
from saas.views.profile import OrganizationCreateView
from saas.views.plans import CartPlanListView
from rules.views.app import (AppMixin, SessionProxyMixin,
    AppDashboardView as AppDashboardViewBase)

from ..locals import get_current_broker
from ..mixins import DjaoAppMixin
from .redirects import OrganizationRedirectView

LOGGER = logging.getLogger(__name__)


def raise_404_on_does_not_exist(method):
    """Raise a 404 error when an object cannot be found in the database."""
    def wrap(*args, **kwargs):
        try:
            return method(*args, **kwargs)
        except ObjectDoesNotExist as err:
            raise Http404(err)
    return wrap


class ProxyPageMixin(DjaoAppMixin, PageMixin, SessionProxyMixin, AppMixin):
    """
    Display or Edit a ``Page`` of a ``rules.App``.

    By default shows DjaoApp homepage.
    """

    # XXX ``page_name``.html will contain default message from the proxyed app.
    page_name = None

    def forward_error(self, err):
        #pylint:disable=unused-argument
        context = super(ProxyPageMixin, self).get_context_data()
        context.update({'err': str(err)})
        template_name = 'rules/forward_error.html'
        if not fail_direct(self.request, organization=get_broker()):
            template_name = 'rules/forward_error_manager_help.html'
        return TemplateResponse(
            request=self.request,
            template=template_name,
            context=context,
            content_type='text/html',
            status=503)

    def get_template_names(self):
        candidates = super(ProxyPageMixin, self).get_template_names()
        page_name = self.kwargs.get('page', self.page_name)
        optional_template_names = []
        if not page_name:
            page_name = 'index'
        if page_name.startswith('/'):
            page_name = page_name[1:]
        if page_name.endswith('/'):
            optional_template_names += ["%s/index.html" % page_name]
            page_name = page_name[:-1]
        if not page_name:
            page_name = 'index'
        candidates += ["%s.html" % page_name] + optional_template_names
        for template_name in candidates:
            try:
                get_template(template_name)
                return [template_name]
            except TemplateDoesNotExist:
                pass
        raise Http404('TemplateDoesNotExist: %s' % ', '.join(candidates))

    @method_decorator(raise_404_on_does_not_exist)
    def get_context_data(self, **kwargs):
        context = super(ProxyPageMixin, self).get_context_data(**kwargs)
        # Need to be set to be able to use djaoapp-pages PageView
        self.template_name = self.get_template_names()[0]
        return context

    def translate_response(self, response):
        if response.status_code == 200:
            # We passed the invoice_keys into the session. When the remote
            # service returns HTTP 200 OK, we assume it synchronizes whichever
            # state necessary. We clear invoice_key/sync_on here so we won't
            # generate another notification.
            invoice_keys = self.session.get('invoice_keys', None)
            if invoice_keys:
                ChargeItem.objects.filter(invoice_key__in=invoice_keys).update(
                    invoice_key=None, sync_on="")
        return super(ProxyPageMixin, self).translate_response(response)

    def get(self, request, *args, **kwargs):
        try:
            response = super(ProxyPageMixin, self).get(request, *args, **kwargs)
        # XXX cannot use 404 exception because it will catch errors
        # in get_context_data.
        except Http404 as err:
            LOGGER.debug("we will be looking for assets because of '%s'", err)
            response = None
            if settings.DEBUG:
                # If we do not execute after the forward we will return
                # local versions of bootstrap.js for example.
                try:
                    page = self.kwargs.get('page')
                    if page is None:
                        page = ''
                    response = debug_serve(request, page)
                except Http404:
                    pass
            if response is None:
                # Mostly for automated tests.
                response = serve(
                    request, request.path, document_root=settings.HTDOCS)
        return response


class DjaoAppProxyPageView(TemplateView):

    def get_template_names(self):
        # This will discard the ``ImproperlyConfigured`` exception
        # from ``TemplateView``.
        return []


class ProxyPageView(ProxyPageMixin, DjaoAppProxyPageView):

    # Without a template_name on the class, pages will not call
    # TemplateResponse.render() and thus turn a 503 into 500 error.
    template_name = 'app.html'


class DjaoAppPageRedirectView(UserMixin, OrganizationRedirectView):
    """
    Implements /app/ URL.
    """
    template_name = 'accesible_apps.html'
    pattern_name = 'organization_app'
    explicit_create_on_none = True

    def get_context_data(self, **kwargs):
        context = super(
            DjaoAppPageRedirectView, self).get_context_data(**kwargs)
        # Add URLs needed for generic_navbar.html and sidebar
        broker = get_current_broker()
        context.update({'provider': broker})
        return context


class PricingView(DjaoAppMixin, PageMixin, CartPlanListView):
    """
    WYSIWYG editable pricing page for a ``rules.App``.

    By default shows DjaoApp pricing page.
    """
    def get_organization(self):
        slug = self.kwargs.get(self.organization_url_kwarg, None)
        if slug is not None:
            queryset = get_organization_model().objects.filter(slug=slug)
            if queryset.exists():
                return queryset.get()
        return get_current_broker()

    def get_context_data(self, **kwargs):
        context = super(PricingView, self).get_context_data(**kwargs)
        if self.edit_perm:
            context.update({'plan': Plan()})
            if not self.object_list.exists():
                messages.info(self.request,
                    "No Plans yet. Click the 'Add Plan' button to create one.")
        return context


class AppDashboardView(AppDashboardViewBase):

    def get_context_data(self, **kwargs):
        context = super(AppDashboardView, self).get_context_data(**kwargs)
        context.update({'site_available_at_url': build_absolute_uri(
            self.request, site=get_current_site().db_object)})
        return context


class AppCreateView(ProxyPageMixin, OrganizationCreateView):
    """
    By default we redirect to the application unless there is a ``Rule``
    that tells us to do otherwise.
    """
    pass

# XXX Because we haven't separated djaoapp into its own process.
class DjaoAppPageView(TemplateView):

    template_name = 'app.html'

    def get_template_names(self):
        if not fail_direct(self.request, organization=get_broker()):
            return ['app_proxy_help.html']
        return super(DjaoAppPageView, self).get_template_names()

    def get_context_data(self, **kwargs):
        # Add URLs needed for generic_navbar.html and sidebar
        context = super(DjaoAppPageView, self).get_context_data(**kwargs)
        broker = get_current_broker()
        context.update({'provider': broker})
        return context


class AppPageView(ProxyPageMixin, DjaoAppPageView):

    page_name = 'app' # Override ProxyPageMixin.page_name


class AppPageRedirectView(ProxyPageMixin, DjaoAppPageRedirectView):
    pass
