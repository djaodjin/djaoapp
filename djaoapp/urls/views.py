# Copyright (c) 2023, DjaoDjin inc.
# see LICENSE

from deployutils.apps.django.compat import is_authenticated
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.views.generic import RedirectView
from rules.urldecorators import include
from saas.settings import PROFILE_URL_KWARG, SLUG_RE
from saas.views import UserRedirectView
from signup.forms import StartAuthenticationForm
from signup.settings import EMAIL_VERIFICATION_PAT, USERNAME_PAT
from signup.views.saml import saml_metadata_view

from ..urlbuilders import (url_active, url_agreement, url_authenticated,
    url_dashboard, url_direct, url_frictionless_direct,
    url_frictionless_self_provider, url_provider, url_self_provider,
    url_prefixed, url_dashboard_iframe)
from ..views.contact import ContactView
from ..views.custom_saas import (DashboardView, RoleImplicitGrantAcceptView,
    ProcessorAuthorizeView, OrganizationProfileView)
from ..views.custom_signup import (ActivationView, PasswordResetConfirmView,
    RecoverView, SigninView, SignoutView, SignupView)
from ..views.custom_themes import ThemePackageView, ThemePackageDownloadView
from ..views.notifications import (NotificationDetailView,
    NotificationInnerFrameView)
from ..views.users import (UserProfileView, UserNotificationsView,
    UserAccessiblesView, UserPasswordUpdateView, UserPublicKeyUpdateView)
from ..views.product import (AppPageView, AppPageRedirectView,
    ProxyPageView, PricingView, AppDashboardView)
from ..views.redirects import OrganizationCreateView, OrganizationRedirectView


def is_anonymous(func, next_url):
    def wrapped(request, *args, **kwargs):
        if is_authenticated(request):
            return HttpResponseRedirect(next_url)
        return func(request, *args, **kwargs)
    return wrapped

urlpatterns = [
    # Authentication (login, registration, etc.)
    url_prefixed(r'^reset/(?P<verification_key>%s)/'
        % EMAIL_VERIFICATION_PAT,
        PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    url_prefixed(r'^activate/(?P<verification_key>%s)/'
        % EMAIL_VERIFICATION_PAT,
        ActivationView.as_view(), name='registration_activate'),
    url_prefixed(r'^activate/',
        SigninView.as_view(
            form_class=StartAuthenticationForm,
            template_name='accounts/activate/index.html'),
        name='registration_activate_start'),
    url_prefixed('', include('social_django.urls', namespace='social')),
    url_prefixed(r'^login/', SigninView.as_view(), name='login'),
    url_prefixed(r'^logout/', SignoutView.as_view(), name='logout'),
    url_prefixed(r'^recover/', RecoverView.as_view(), name='password_reset'),
    # We want to give the opportunity to have multiple registration page
    # (ex: frictionless).`
    url_prefixed(r'^register/((?P<path>\w+)/)?',
        SignupView.as_view(),
        name='registration_register'),
    url_prefixed(r'^saml/', saml_metadata_view),

    # Redirects
    url_prefixed(r'^billing/cart/',
        # XXX override because we want a login_required in front.
        login_required(OrganizationRedirectView.as_view(
                pattern_name='saas_organization_cart'),
                       login_url='registration_register'),
        name='saas_cart'),
    url_authenticated(r'^profile/new/',
        # We want to use `get_implicit_create_on_none` override.
        OrganizationCreateView.as_view(),
        name='saas_organization_create'),
    url_authenticated(r'^profile/$',
        # We want to use `get_implicit_create_on_none` override.
        OrganizationRedirectView.as_view(
        pattern_name='saas_organization_profile'),
        name='saas_profile'),
    url_authenticated(r'^', include('saas.urls.views.headredirects')),

    # Profiles
    url_agreement(r'users/roles/accept/$',
        RoleImplicitGrantAcceptView.as_view(),
        name='saas_role_implicit_grant_accept'),
    url_authenticated(r'^', include('saas.urls.views.request')),
    url_active(r'^users/$',
        UserRedirectView.as_view(), name='accounts_profile'),
    url_self_provider(r'^users/(?P<user>%s)/roles/$' % USERNAME_PAT,
        UserAccessiblesView.as_view(), name='saas_user_product_list'),
    url_self_provider(r'^users/(?P<user>%s)/password/' % USERNAME_PAT,
        UserPasswordUpdateView.as_view(), name='password_change'),
    url_self_provider(r'^users/(?P<user>%s)/pubkey/' % USERNAME_PAT,
        UserPublicKeyUpdateView.as_view(), name='pubkey_update'),
    url_self_provider(r'^users/(?P<user>%s)/notifications/$' % USERNAME_PAT,
        UserNotificationsView.as_view(), name='users_notifications'),
    url_frictionless_self_provider(r'^users/(?P<user>%s)/$' % USERNAME_PAT,
        UserProfileView.as_view(), name='users_profile'),
    url_direct(r'contacts/', include('signup.urls.views.contacts')),

    url_prefixed(r'^pricing/$',
        PricingView.as_view(), name='saas_cart_plan_list'),
    url_prefixed(r'^', include('saas.urls.views.noauth')),
    url_direct(r'^', include('saas.urls.views.broker')),
    url_direct(r'^metrics/(?P<%s>%s)/dashboard/$' % (
        PROFILE_URL_KWARG, SLUG_RE),
        DashboardView.as_view(), name='saas_dashboard'),
    url_direct(r'^billing/(?P<%s>%s)/bank/$' % (PROFILE_URL_KWARG, SLUG_RE),
        ProcessorAuthorizeView.as_view(), name='saas_update_bank'),
    url_direct(r'^', include('saas.urls.views.provider')),
    url_provider(r'^', include('saas.urls.views.subscriber.billing')),
    url_provider(r'^profile/(?P<%s>%s)/contact/$' % (
        PROFILE_URL_KWARG, SLUG_RE),
        OrganizationProfileView.as_view(),
            name='saas_organization_profile'),
    url_provider(r'^', include('saas.urls.views.subscriber.profile')),
    url_authenticated(r'^', include('saas.urls.views.tailredirects')),

    url_dashboard_iframe(r'^proxy/notifications/(?P<template>%s)/iframe/' %
        SLUG_RE, NotificationInnerFrameView.as_view(),
        name='notification_inner_frame'),
    url_dashboard(r'^proxy/notifications/(?P<template>%s)/' % SLUG_RE,
        NotificationDetailView.as_view(), name='notification_detail'),
    url_dashboard(r'^proxy/notifications/',
        RedirectView.as_view(pattern_name='extended_templates_theme_update'),
        name='notification_base'),
    url_dashboard(r'^proxy/rules/',
        AppDashboardView.as_view(), name='rules_update'),
    url_dashboard(r'^', include('rules.urls.configure')),
    url_dashboard(r'^themes/download/',
        ThemePackageDownloadView.as_view(),
        name='extended_templates_theme_download'),
    url_dashboard(r'^themes/',
        ThemePackageView.as_view(), name='extended_templates_theme_update'),

    # Various pages on the djaoapp site itself.
    url_prefixed(r'^contact/', ContactView.as_view(), name='contact'),
# This is a good idea once we figure out how to edit the homepage.
#    url(r'^$', is_anonymous(
#            ProxyPageView.as_view(),
#            reverse_lazy('product_default_start'))),

    # Magic! redirects to the product webapp.
    url_frictionless_direct(r'^app/(?P<%s>%s)/(?P<page>\S+)?' % (
        PROFILE_URL_KWARG, SLUG_RE),
        AppPageView.as_view(), name='organization_app'),
    url_authenticated(r'^app/',
        AppPageRedirectView.as_view(), name='product_default_start'),
    url_prefixed(r'^app',
        RedirectView.as_view(pattern_name='product_default_start')),
    url_prefixed(r'^(?P<page>\S+)?',
        ProxyPageView.as_view(), name='rules_page'),
]
