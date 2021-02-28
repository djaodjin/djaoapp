# Copyright (c) 2019, DjaoDjin inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED
# TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
# OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
# OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
# ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""
URLs for the resources API of rules.
"""

from django.conf.urls import url

from ... import settings
from ...api.keys import (AppUpdateAPIView, GenerateKeyAPIView)
from ...api.rules import (RuleListAPIView, RuleDetailAPIView,
    UserEngagementAPIView, EngagementAPIView)
from ...api.sessions import GetSessionAPIView, GetSessionDetailAPIView

urlpatterns = [
    url(r'^proxy/sessions/(?P<user>%s)/?' % settings.USERNAME_PAT,
        GetSessionDetailAPIView.as_view(), name='rules_api_session_data'),
    url(r'^proxy/sessions/?',
        GetSessionAPIView.as_view(), name='rules_api_session_data_base'),
    url(r'^proxy/key/',
        GenerateKeyAPIView.as_view(), name='rules_api_generate_key'),
    url(r'^proxy/engagement/users/',
        UserEngagementAPIView.as_view(), name='rules_api_user_engagement'),
    url(r'^proxy/engagement/',
        EngagementAPIView.as_view(), name='rules_api_engagement'),
    url(r'^proxy/rules(?P<rule>\S+)$',
        RuleDetailAPIView.as_view(), name='rules_api_rule_detail'),
    url(r'^proxy/rules',
        RuleListAPIView.as_view(), name='rules_api_rule_list'),
    url(r'^proxy/$',
        AppUpdateAPIView.as_view(), name='rules_api_app_detail'),
]
