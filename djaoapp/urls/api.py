# Copyright (c) 2019, DjaoDjin inc.
# see LICENSE

from saas.settings import ACCT_REGEX
from signup.settings import USERNAME_PAT
from urldecorators import include, url

from ..api.auth import DjaoAppJWTRegister, CredentialsAPIView
from ..api.custom_themes import ThemePackageListAPIView, AppUpdateAPIView
from ..api.notifications import NotificationAPIView, NotificationDetailAPIView
from ..api.organizations import (OrganizationDetailAPIView,
    OrganizationListAPIView)
from ..api.roles import RoleListAPIView
from ..api.todos import TodosAPIView
from ..api.users import UserProfileAPIView, RecentActivityAPIView
from ..urlbuilders import (url_authenticated, url_direct,
    url_frictionless_direct, url_frictionless_provider,
    url_frictionless_self_provider,
    url_provider, url_provider_only, url_self_provider)


urlpatterns = [
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
    url_direct(r'^api/proxy/recent/',
        RecentActivityAPIView.as_view(), name='api_recent_activity'),
    url_direct(r'^api/proxy/$',
        AppUpdateAPIView.as_view(), name='rules_api_app_detail'),
    url_direct(r'^api/', include('rules.urls.api.proxy')),
    url_direct(r'^api/themes/$',
        ThemePackageListAPIView.as_view(), name='pages_api_themes'),
    url_direct(r'^api/', include('pages.urls.api')),

    # Billing, Metrics, Profiles, Roles and Subscriptions
    url(r'^api/', include('saas.urls.api.cart')), # DELETE implements own policy
    url_authenticated(r'^api/', include('saas.urls.api.legal')),
    url_self_provider(r'^api/', include('saas.urls.api.users')),
    url_direct(r'^api/', include('saas.urls.api.broker')),
    # api/charges/:charge/refund must be before api/charges/
    url_provider_only(
        r'^api/', include('saas.urls.api.provider.charges')),
    url_direct(
        r'^api/', include('saas.urls.api.provider.billing')),
    url_direct(
        r'^api/', include('saas.urls.api.provider.roles')),
    url_direct(
        r'^api/', include('saas.urls.api.provider.subscribers')),
    url_frictionless_direct(
        r'^api/', include('saas.urls.api.provider.plans')),
    url_frictionless_direct(
        r'^api/', include('saas.urls.api.provider.metrics')),
    url_direct(r'^api/profile/$',
        OrganizationListAPIView.as_view(), name='saas_api_profile'),
    url_frictionless_provider(
        r'^api/profile/(?P<organization>%s)/?$' % ACCT_REGEX,
        OrganizationDetailAPIView.as_view(), name='saas_api_organization'),
    url_provider(
        r'^api/profile/(?P<organization>%s)/roles/(?P<role>%s)/?$' % (
            ACCT_REGEX, ACCT_REGEX),
        RoleListAPIView.as_view(), name='saas_api_roles_by_descr'),
    url_provider(
        r'^api/', include('saas.urls.api.subscriber.charges')),
    url_provider(
        r'^api/', include('saas.urls.api.subscriber.billing')),
    url_provider(
        r'^api/', include('saas.urls.api.subscriber.roles')),
    url_frictionless_provider(
        r'^api/', include('saas.urls.api.subscriber.profile')),
    url_authenticated(
        '^api/', include('saas.urls.api.search')),

    # Auth & credentials
    url_direct(r'api/', include('signup.urls.api.contacts')),
    url_self_provider(r'^api/', include('signup.urls.api.keys')),
    url_frictionless_self_provider(r'^api/',
        include('signup.urls.api.activate')),
    url_frictionless_self_provider(r'^api/users/(?P<user>%s)/$' % USERNAME_PAT,
        UserProfileAPIView.as_view(), name='api_user_profile'),
    url_self_provider(r'^api/', include('signup.urls.api.users')),
    # `{user}` is not a url parameter, hence we cannot use `url_self_provider`.
    # Furthermore we restrict verification and refresh of JWT
    # to the request.user itself.
    url_authenticated(r'^api/', include('signup.urls.api.tokens')),
    url(r'^api/auth/register/',
        DjaoAppJWTRegister.as_view(), name='api_register'),
    url(r'^api/', include('signup.urls.api.auth')),

    # DjaoApp-specific
    url_self_provider(r'^api/todos/', TodosAPIView.as_view(), 'api_todos'),
]
