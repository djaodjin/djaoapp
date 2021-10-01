# Copyright (c) 2021, DjaoDjin inc.
# see LICENSE

from rules.urldecorators import include
from saas.settings import ACCT_REGEX
from signup.settings import USERNAME_PAT

from ..api.auth import DjaoAppJWTRegister, CredentialsAPIView
from ..api.contact import ContactUsAPIView
from ..api.custom_themes import DjaoAppThemePackageListAPIView
from ..api.notifications import NotificationAPIView, NotificationDetailAPIView
from ..api.organizations import (DjaoAppProfileDetailAPIView,
    DjaoAppProfileListAPIView)
from ..api.roles import DjaoAppRoleByDescrListAPIView
from ..api.todos import DjaoAppAPIVersion, TodosAPIView
from ..api.users import (RecentActivityAPIView, DjaoAppUserDetailAPIView,
    DjaoAppUserNotificationsAPIView)
from ..urlbuilders import (url_authenticated, url_direct,
    url_frictionless_direct, url_frictionless_provider,
    url_frictionless_self_provider, url_prefixed,
    url_provider, url_provider_only, url_self_provider)


urlpatterns = [
    # HTTP request pipeline and visual appearence.
    url_direct(r'^api/auth/tokens/realms/(?P<organization>%s)?/?' % ACCT_REGEX,
                                          # site/subdomain
        CredentialsAPIView.as_view(), name='api_credentials_organization'),
    url_direct(r'^api/notifications/(?P<template>%s)/' % ACCT_REGEX,
        NotificationDetailAPIView.as_view(),
        name='api_notification_send_test_email'),
    url_direct(r'^api/notifications/',
        NotificationAPIView.as_view(), name='api_notification_base'),
    url_direct(r'^api/proxy/recent/',
        RecentActivityAPIView.as_view(), name='api_recent_activity'),
    url_direct(r'^api/', include('rules.urls.api.proxy')),
    url_direct(r'^api/themes/$',
        DjaoAppThemePackageListAPIView.as_view(), name='pages_api_themes'),
    url_direct(r'^api/themes/', include('pages.urls.api.assets')),
    url_direct(r'^api/themes/', include('pages.urls.api.templates')),
    url_direct(r'^api/themes/', include('pages.urls.api.themes')),

    # Billing, Metrics, Profiles, Roles and Subscriptions
    url_prefixed(r'^api/', include('saas.urls.api.cart')),
        # `saas.urls.api.cart`: DELETE implements its own policy
    url_authenticated(r'^api/', include('saas.urls.api.legal')),
    url_self_provider(r'^api/', include('saas.urls.api.users')),
    url_direct(r'^api/profile/$',
        DjaoAppProfileListAPIView.as_view(), name='saas_api_profile'),
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
    url_frictionless_provider(
        r'^api/profile/(?P<organization>%s)/?$' % ACCT_REGEX,
        DjaoAppProfileDetailAPIView.as_view(), name='saas_api_organization'),
    url_provider(
        r'^api/profile/(?P<organization>%s)/roles/(?P<role>%s)/?$' % (
            ACCT_REGEX, ACCT_REGEX),
        DjaoAppRoleByDescrListAPIView.as_view(),
        name='saas_api_roles_by_descr'),
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
        DjaoAppUserDetailAPIView.as_view(), name='api_user_profile'),
    url_frictionless_self_provider(r'^api/users/(?P<user>%s)/notifications/$' %
        USERNAME_PAT, DjaoAppUserNotificationsAPIView.as_view(),
        name='api_user_notifications'),
    url_self_provider(r'^api/', include('signup.urls.api.users')),
    # `{user}` is not a url parameter, hence we cannot use `url_self_provider`.
    # Furthermore we restrict verification and refresh of JWT
    # to the request.user itself.
    url_authenticated(r'^api/', include('signup.urls.api.tokens')),
    url_prefixed(r'^api/auth/register/',
        DjaoAppJWTRegister.as_view(), name='api_register'),
    url_prefixed(r'^api/', include('signup.urls.api.auth')),

    # DjaoApp-specific
    url_self_provider(r'^api/todos/', TodosAPIView.as_view(), 'api_todos'),
    url_prefixed(r'^api/contact/',
        ContactUsAPIView.as_view(), name='api_contact_us'),
    url_prefixed(r'^api$', DjaoAppAPIVersion.as_view())
]
