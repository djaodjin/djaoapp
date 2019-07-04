# Copyright (c) 2019, DjaoDjin inc.
# see LICENSE

from django.conf.urls import url

from saas.settings import ACCT_REGEX
from signup import settings
from djaoapp.views.custom_signup import (ActivationView, PasswordResetView,
    PasswordResetConfirmView, SigninView, SignoutView, SignupView)


urlpatterns = [
    url(r'^register/((?P<path>%s)/)?' % ACCT_REGEX,
        SignupView.as_view(),
        name='registration_register'),
    url(r'^activate/(?P<verification_key>%s)/'
        % settings.EMAIL_VERIFICATION_PAT,
        ActivationView.as_view(), name='registration_activate'),
    url(r'^recover/',
        PasswordResetView.as_view(), name='password_reset'),
    url(r'^login/', SigninView.as_view(), name='login'),
    url(r'^logout/', SignoutView.as_view(), name='logout'),
    url(r'^reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/', #pylint: disable=line-too-long
        PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
]
