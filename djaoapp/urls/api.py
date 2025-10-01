# Copyright (c) 2024, DjaoDjin inc.
# see LICENSE

from rules.urldecorators import include
from saas.settings import PROFILE_URL_KWARG, SLUG_RE
from signup.settings import USERNAME_PAT, EMAIL_VERIFICATION_PAT

from ..api.auth import (CredentialsAPIView, DjaoAppJWTActivate,
    DjaoAppJWTRefresh, DjaoAppJWTRegister)
from ..api.contact import (ContactUsAPIView, PlacesSuggestionsAPIView,
    PlacesDetailAPIView)
from ..api.custom_themes import DjaoAppThemePackageListAPIView
from ..api.notifications import NotificationAPIView, NotificationDetailAPIView
from ..api.organizations import (DjaoAppProfileDetailAPIView,
    DjaoAppProfileListAPIView, DjaoAppProfilePictureAPIView)
from ..api.roles import DjaoAppRoleByDescrListAPIView
from ..api.todos import DjaoAppAPIVersion, TodosAPIView, GenerateErrorAPIView
from ..api.users import (RecentActivityAPIView, DjaoAppUserDetailAPIView,
    DjaoAppUserNotificationsAPIView, DjaoAppUserOTPAPIView)
from ..urlbuilders import (url_authenticated, url_direct,
    url_frictionless_direct, url_frictionless_provider,
    url_frictionless_self_provider, url_prefixed,
    url_provider, url_provider_only, url_self_provider)


urlpatterns = [
    # HTTP request pipeline and visual appearence.
    url_direct(r'^api/auth/tokens/realms/(?P<%s>%s)?' % (
        PROFILE_URL_KWARG, SLUG_RE), # site/subdomain
        CredentialsAPIView.as_view(), name='api_credentials_organization'),
    url_direct(r'^api/notifications/(?P<template>%s)' % SLUG_RE,
        NotificationDetailAPIView.as_view(),
        name='api_notification_send_test_email'),
    url_direct(r'^api/notifications',
        NotificationAPIView.as_view(), name='api_notification_base'),
    url_direct(r'^api/proxy/recent',
        RecentActivityAPIView.as_view(), name='api_recent_activity'),
    url_direct(r'^api/proxy/generate-error',
        GenerateErrorAPIView.as_view(), name='api_generate_error'),
    url_direct(r'^api/', include('rules.urls.api.proxy')),
    url_direct(r'^api/themes$',
        DjaoAppThemePackageListAPIView.as_view(),
        name='extended_templates_api_themes'),
    url_direct(r'^api/', include('extended_templates.urls.api')),

    # Billing, Metrics, Profiles, Roles and Subscriptions
    url_prefixed(r'^api/', include('saas.urls.api.cart')),
        # `saas.urls.api.cart`: DELETE implements its own policy
    url_prefixed(r'api/', include('saas.urls.api.payments')),
    url_authenticated(r'^api/', include('saas.urls.api.legal')),
    url_self_provider(r'^api/', include('saas.urls.api.users')),
    url_direct(r'^api/profile$',
        DjaoAppProfileListAPIView.as_view(), name='saas_api_profile'),
    url_direct(r'^api/', include('saas.urls.api.headbroker')),
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
        r'^api/profile/(?P<%s>%s)/picture$' % (
        PROFILE_URL_KWARG, SLUG_RE),
        DjaoAppProfilePictureAPIView.as_view(),
        name='saas_api_organization_picture'),
    url_frictionless_provider(
        r'^api/profile/(?P<%s>%s)$' % (
        PROFILE_URL_KWARG, SLUG_RE),
        DjaoAppProfileDetailAPIView.as_view(), name='saas_api_organization'),
    url_provider(
        r'^api/profile/(?P<%s>%s)/roles/(?P<role>%s)$' % (
            PROFILE_URL_KWARG, SLUG_RE, SLUG_RE),
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
    url_direct(r'^api/', include('saas.urls.api.tailbroker')),
    url_authenticated(
        '^api/', include('saas.urls.api.search')),

    # Auth & credentials
    url_provider_only(r'api/', include('signup.urls.api.activities')),
    url_direct(r'api/', include('signup.urls.api.contacts')),
    url_self_provider(r'^api/', include('signup.urls.api.keys')),
    url_frictionless_self_provider(r'^api/',
        include('signup.urls.api.activate')),
    url_frictionless_self_provider(r'^api/users/(?P<user>%s)$' % USERNAME_PAT,
        DjaoAppUserDetailAPIView.as_view(), name='api_user_profile'),
    url_frictionless_self_provider(r'^api/users/(?P<user>%s)/notifications$' %
        USERNAME_PAT, DjaoAppUserNotificationsAPIView.as_view(),
        name='api_user_notifications'),
    url_frictionless_self_provider(r'^api/users/(?P<user>%s)/otp$' %
        USERNAME_PAT,
        DjaoAppUserOTPAPIView.as_view(), name='api_user_otp_change'),
    url_self_provider(r'^api/', include('signup.urls.api.users')),
    # `{user}` is not a url parameter, hence we cannot use `url_self_provider`.
    # Furthermore we restrict verification and refresh of JWT
    # to the request.user itself.
    url_authenticated(r'^api/auth/tokens',
        DjaoAppJWTRefresh.as_view(), name='api_refresh_token'),
    url_authenticated(r'^api/', include('signup.urls.api.tokens')),
    url_prefixed(r'^api/auth/activate/(?P<verification_key>%s)$'
        % EMAIL_VERIFICATION_PAT,
        DjaoAppJWTActivate.as_view(), name='api_activate'),
    url_prefixed(r'^api/auth/register',
        DjaoAppJWTRegister.as_view(), name='api_register'),
    url_prefixed(r'^api/', include('signup.urls.api.auth')),

    # DjaoApp-specific
    url_self_provider(r'^api/todos', TodosAPIView.as_view(), 'api_todos'),
    url_prefixed(r'^api/contact',
        ContactUsAPIView.as_view(), name='api_contact_us'),
    url_authenticated(r'^api/accounts/places/(?P<place_id>.*)',
        PlacesDetailAPIView.as_view(), name='api_places_detail'),
    url_authenticated(r'^api/accounts/places',
        PlacesSuggestionsAPIView.as_view(), name='api_places_suggestions'),
    url_prefixed(r'^api$', DjaoAppAPIVersion.as_view())
]
