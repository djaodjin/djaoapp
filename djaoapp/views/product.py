# Copyright (c) 2022, DjaoDjin inc.
# see LICENSE

"""
Default start page for a djaodjin-hosted product.
"""
from __future__ import unicode_literals

import logging

from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from django.contrib import messages
from django.contrib.staticfiles.views import serve as debug_serve
from django.http import Http404
from django.template import TemplateDoesNotExist
from django.template.loader import get_template
from django.template.response import TemplateResponse
from django.utils._os import safe_join
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from django.views.static import serve
from extended_templates import settings as themes_settings
from extended_templates.views.pages import PageMixin
from rules.utils import get_current_app
from rules.views.app import (AppMixin, SessionProxyMixin,
    AppDashboardView as AppDashboardViewBase)
from saas.decorators import fail_direct
from saas.mixins import UserMixin
from saas.models import ChargeItem, Plan, get_broker
from saas.utils import get_organization_model
from saas.views.plans import CartPlanListView

from ..compat import gettext_lazy as _
from ..thread_locals import (get_active_theme, get_current_app,
    get_current_broker, is_current_broker)
from ..mixins import DjaoAppMixin
from .redirects import OrganizationRedirectView

LOGGER = logging.getLogger(__name__)


class ProxyPageMixin(DjaoAppMixin, PageMixin, SessionProxyMixin, AppMixin):
    """
    Display or Edit a ``Page`` of a ``rules.App``.

    By default shows DjaoApp homepage.
    """

    # XXX ``page_name``.html will contain default message from the proxyed app.
    page_name = None

    def check_permissions(self, request):
        # XXX This will be executed for all forward requests, even ones
        # to load static assets. As long as we don't have a reliable
        # way to identify forwarded request to "main" page.
        #if is_authenticated(request):
        #    redirect_url = fail_active_roles(request)
        #    if redirect_url:
        #        return redirect_url, False
        return super(ProxyPageMixin, self).check_permissions(request)

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
            page_name = page_name[:-1]
            optional_template_names += ["%s/index.html" % page_name]
        if not page_name:
            page_name = 'index'
        candidates += ["%s.html" % page_name] + optional_template_names
        LOGGER.info('candidate page templates: %s', ','.join(candidates))
        return candidates


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
        resp = super(ProxyPageMixin, self).translate_response(response)
        # 500 errors in the service the request was forwarded to will have
        # logged errors there.
        resp._has_been_logged = True #pylint:disable=protected-access
        return resp

    def get(self, request, *args, **kwargs):
        try:
            response = super(ProxyPageMixin, self).get(request, *args, **kwargs)
        # XXX cannot use 404 exception because it will catch errors
        # in get_context_data.
        except Http404 as err:
            LOGGER.info("we will be looking for assets because of '%s'", err)
            # static and media assets will have been served through
            # different rules in debug mode. In production, they
            # will have been served by the front-end webserver (nginx)
            # directly. So we only have to deal with the buildbot (DEBUG=0,
            # USE_FIXTURES=1).
            if not settings.USE_FIXTURES:
                raise
            rel_path = self.kwargs.get('page')
            if rel_path is None:
                rel_path = ''
            response = None
            if settings.DEBUG:
                # If we do not execute after the forward we will return
                # local versions of bootstrap.js for example.
                try:
                    response = debug_serve(request, rel_path)
                except Http404:
                    pass
            if response is None:
                app = get_current_app(request)
                if is_current_broker(app.account):
                    asset_dir = themes_settings.PUBLIC_ROOT
                else:
                    theme_name = get_active_theme()
                    asset_dir = safe_join(
                        themes_settings.PUBLIC_ROOT, theme_name)
                LOGGER.info("looking for '%s' in '%s'", rel_path, asset_dir)
                response = serve(
                    request, rel_path, document_root=asset_dir)
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

    By default redirects to the profile App page.
    """
    template_name = 'accesible_apps.html'
    pattern_name = 'organization_app'

    def get_context_data(self, **kwargs):
        context = super(
            DjaoAppPageRedirectView, self).get_context_data(**kwargs)
        # Add URLs needed for _appmenu.html and sidebar
        broker = get_current_broker()
        context.update({'provider': broker})
        return context


class PricingView(DjaoAppMixin, PageMixin, SessionProxyMixin, CartPlanListView):
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
            app = get_current_app()
            if app.show_edit_tools:
                context.update({
                    'show_show_edit_tools': app.show_edit_tools,
                    'plan': Plan()
                })
                if not self.object_list.exists():
                    messages.info(self.request, _("No Plans yet."\
                        " Click the 'Add Plan' button to create one."))
        return context


class AppDashboardView(AppDashboardViewBase):
    """
    Application dashboard
    """


class AppPageView(ProxyPageView):

    page_name = 'app' # Override ProxyPageMixin.page_name
    template_name = 'app.html'

    def get_template_names(self):
        candidates = []
        profile = self.kwargs.get('organization')
        original_candidates = super(AppPageView, self).get_template_names()
        if profile:
            for candidate in original_candidates:
                candidates += ['app/%s/%s' % (profile, candidate)]
        for candidate in original_candidates:
            candidates += ['app/%s' % (candidate)]

        if profile:
            candidates += [
                'app/%s/index.html' % profile, 'app/%s.html' % profile]

        if not fail_direct(self.request, organization=get_broker()):
            # XXX testing exception catcher
            if self.kwargs.get('organization') == '500':
                raise ValueError("Testing 500 exception catcher")
            candidates += ['app_proxy_help.html']

        candidates += ['app/index.html', 'app.html']

        return candidates

    def get_context_data(self, **kwargs):
        # Add URLs needed for _appmenu.html and sidebar
        context = super(AppPageView, self).get_context_data(**kwargs)
        broker = get_current_broker()
        context.update({'provider': broker})
        return context



class AppPageRedirectView(ProxyPageMixin, DjaoAppPageRedirectView):
    pass
