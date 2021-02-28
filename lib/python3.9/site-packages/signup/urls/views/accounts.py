# Copyright (c) 2020, Djaodjin Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
# OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
# OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
# ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from django.conf.urls import url

from ... import settings
from ...views.auth import (ActivationView, PasswordResetView,
    PasswordResetConfirmView, SigninView, SignoutView, SignupView)

urlpatterns = [
    # When the key and/or token are wrong we don't want to give any clue
    # as to why that is so. Less information communicated to an attacker,
    # the better.
    url(r'^activate/(?P<verification_key>%s)/$'
        % settings.EMAIL_VERIFICATION_PAT,
        ActivationView.as_view(), name='registration_activate'),
    url(r'^activate/',
        SigninView.as_view(template_name='accounts/activate/index.html'),
        name='registration_activate_start'),
    url(r'^register/$',
        SignupView.as_view(), name='registration_register'),
    url(r'^recover/',
        PasswordResetView.as_view(), name='password_reset'),
    url(r'^login/',
        SigninView.as_view(), name='login'),
    url(r'^logout/',
        SignoutView.as_view(), name='logout'),
    url(r'^reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$', #pylint: disable=line-too-long
        PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
]
