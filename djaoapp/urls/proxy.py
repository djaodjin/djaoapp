# Copyright (c) 2019, DjaoDjin inc.
# see LICENSE

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.views.generic import RedirectView
from multitier.urlresolvers import site_patterns
from saas.settings import ACCT_REGEX
from saas.views import UserRedirectView
from signup.urls.users import USERNAME_PAT
from urldecorators import include, url

from ..api.auth import DjaoAppJWTRegister, CredentialsAPIView
from ..api.custom_themes import ThemePackageListAPIView, AppUpdateAPIView
from ..api.notifications import NotificationAPIView, NotificationDetailAPIView
from ..api.organizations import (OrganizationDetailAPIView,
    OrganizationListAPIView)
from ..api.roles import RoleListAPIView
from ..api.users import UserProfileAPIView
from ..urlbuilders import (url_authenticated, url_active, url_dashboard,
     url_direct, url_provider, url_provider_only, url_self_provider,
     url_frictionless_self_provider, url_prefixed, url_dashboard_iframe)
from ..views.contact import ContactView
from ..views.custom_themes import ThemePackageView, ThemePackageDownloadView
from ..views.notifications import (NotificationDetailView,
    NotificationInnerFrameView)
from ..views.users import (UserProfileView, UserNotificationsView,
    UserAccessiblesView, UserPasswordUpdateView, UserPublicKeyUpdateView)
from ..views.product import (AppPageView, AppPageRedirectView,
    ProxyPageView, PricingView, AppDashboardView)
from ..views.redirects import OrganizationRedirectView


def is_anonymous(func, next_url):
    def wrapped(request, *args, **kwargs):
        if request.user.is_authenticated():
            return HttpResponseRedirect(next_url)
        return func(request, *args, **kwargs)
    return wrapped

if settings.DEBUG:
    from django.views.defaults import server_error
    from ..views.errors import permission_denied, page_not_found
    urlpatterns = site_patterns(
        url(r'^403/$', permission_denied),
        url(r'^404/$', page_not_found),
        url(r'^500/$', server_error)
    )
else:
    urlpatterns = []

urlpatterns += site_patterns(
    # HTTP request pipeline and visual appearence.
    url_direct(r'^api/auth/tokens/realms/%(organization)s/', # site/subdomain
        CredentialsAPIView.as_view(), name='api_credentials_organization'),
    url_direct(r'^api/auth/tokens/realms/$', # site/subdomain
        CredentialsAPIView.as_view(), name='api_credentials'),
    url_direct(r'^api/notifications/(?P<template>%s)/' % ACCT_REGEX,
        NotificationDetailAPIView.as_view(),
        name='api_notification_send_test_email'),
    url_direct(r'^api/notifications/',
        NotificationAPIView.as_view(), name='api_notification_base'),
    url_direct(r'^api/proxy/$',
        AppUpdateAPIView.as_view(), name='api_app_detail'),
    url_direct(r'^api/', include('rules.urls.api.proxy')),
    url_direct(r'^api/themes/$',
        ThemePackageListAPIView.as_view(), name='pages_api_themes'),
    url_direct(r'^api/', include('pages.urls.api')),

    # Proxy subscription firewall
    url(r'^api/', include('saas.urls.api.cart')), # DELETE implements own policy
    url_self_provider(r'^api/', include('saas.urls.api.users')),
    url_provider_only(r'^api/', include('saas.urls.api.broker')),
    # api/charges/:charge/refund must be before api/charges/
    url_provider_only(r'^api/', include('saas.urls.api.provider.charges')),
    url_direct(r'^api/', include('saas.urls.api.provider.billing')),
    url_direct(r'^api/', include('saas.urls.api.provider.profile')),
    url_direct(r'^api/', include('saas.urls.api.provider.metrics')),
    url_provider(r'^api/profile/(?P<organization>%s)/?$' % ACCT_REGEX,
        OrganizationDetailAPIView.as_view(), name='saas_api_organization'),
    url_provider(r'^api/profile/$',
        OrganizationListAPIView.as_view(), name='saas_api_profile'),
    url_provider(r'^api/profile/(?P<organization>%s)/roles/(?P<role>%s)/?'
        % (ACCT_REGEX, ACCT_REGEX),
        RoleListAPIView.as_view(), name='saas_api_roles_by_descr'),
    url_provider(r'^api/', include('saas.urls.api.subscriber')),
    url_authenticated('^api/', include('saas.urls.api.search')),
    url_self_provider(r'^api/', include('signup.urls.api.keys')),
    url_self_provider(r'^api/', include('signup.urls.api.tokens')),
    url_self_provider(r'^api/users/(?P<user>%s)/$' % USERNAME_PAT,
        UserProfileAPIView.as_view(), name='api_user_profile'),
    url_self_provider(r'^api/', include('signup.urls.api.users')),
    url_direct(r'api/', include('signup.urls.api.contacts')),
    url(r'^api/auth/register/',
        DjaoAppJWTRegister.as_view(), name='api_register'),
    url(r'^api/', include('signup.urls.api.auth')),

    # Login, registration, and user profiles
    url_prefixed(r'^', include('djaoapp.urls.accounts')),
    url_authenticated(r'^', include('saas.urls.request')),
    url_active(r'^users/$',
        UserRedirectView.as_view(), name='accounts_profile'),
    url_self_provider(r'^users/(?P<user>%s)/roles/$' % USERNAME_PAT,
        UserAccessiblesView.as_view(), name='saas_user_product_list'),
    url_self_provider(r'^(?P<user>%s)/password/' % USERNAME_PAT,
        UserPasswordUpdateView.as_view(), name='password_change'),
    url_self_provider(r'^(?P<user>%s)/pubkey/' % USERNAME_PAT,
        UserPublicKeyUpdateView.as_view(), name='pubkey_update'),
    url_self_provider(r'^users/(?P<user>%s)/notifications/$' % USERNAME_PAT,
        UserNotificationsView.as_view(), name='users_notifications'),
    url_frictionless_self_provider(r'^users/(?P<user>%s)/$' % USERNAME_PAT,
        UserProfileView.as_view(), name='users_profile'),
    url_direct(r'contacts/', include('signup.urls.contacts')),

    url(r'^pricing/$', PricingView.as_view(), name='saas_cart_plan_list'),
    url(r'^billing/cart/',
        # XXX override because we want a login_required in front.
        login_required(OrganizationRedirectView.as_view(
                pattern_name='saas_organization_cart'),
                       login_url='registration_register'),
        name='saas_cart'),
    url(r'^', include('saas.urls.noauth')),
    url_direct(r'^', include('saas.urls.broker')),
    url_authenticated(r'^', include('saas.urls.redirects')),
    url_direct(r'^', include('saas.urls.provider')),
    url_provider(r'^', include('saas.urls.subscriber.billing')),
    url_provider(r'^', include('saas.urls.subscriber.profile')),
    url_dashboard_iframe(r'^proxy/notifications/(?P<template>%s)/iframe/' %
        ACCT_REGEX, NotificationInnerFrameView.as_view(),
        name='notification_inner_frame'),
    url_dashboard(r'^proxy/notifications/(?P<template>%s)/' % ACCT_REGEX,
        NotificationDetailView.as_view(), name='notification_detail'),
    url_dashboard(r'^proxy/notifications/',
        RedirectView.as_view(pattern_name='theme_update'), name='notification_base'),
    url_dashboard(r'^proxy/rules/',
        AppDashboardView.as_view(), name='rules_update'),
    url_dashboard(r'^', include('rules.urls.configure')),
    url_dashboard(r'^themes/download/',
        ThemePackageDownloadView.as_view(), name='theme_download'),
    url_dashboard(r'^themes/',
        ThemePackageView.as_view(), name='theme_update'),

    # Various pages on the djaoapp site itself.
    url_prefixed(r'^contact/', ContactView.as_view(), name='contact'),
# This is a good idea once we figure out how to edit the homepage.
#    url(r'^$', is_anonymous(
#            ProxyPageView.as_view(),
#            reverse_lazy('product_default_start'))),

    # Magic! redirects to the product webapp.
    url(r'^app/(?P<organization>%s)/' % ACCT_REGEX,
        AppPageView.as_view(), name='organization_app'),
    url(r'^app/',
        AppPageRedirectView.as_view(), name='product_default_start'),
    url(r'^app',
        RedirectView.as_view(pattern_name='product_default_start')),
    url(r'^(?P<page>\S+)?',
        ProxyPageView.as_view(), name='rules_page'),
)
