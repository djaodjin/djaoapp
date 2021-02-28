# Copyright (c) 2020, DjaoDjin inc.
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

from django.shortcuts import get_object_or_404

from .compat import reverse, six
from .utils import get_app_model, get_current_app


class AppMixinBase(object):
    """
    Returns a ``App`` from a URL.
    """
    app_url_kwarg = 'app'

    @property
    def app(self):
        if not hasattr(self, '_app'):
            if self.app_url_kwarg in self.kwargs:
                self._app = get_object_or_404(get_app_model(),
                    slug=self.kwargs.get(self.app_url_kwarg))
            else:
                self._app = get_current_app()
        return self._app

    def get_context_data(self, **kwargs):
        context = super(AppMixinBase, self).get_context_data(**kwargs)
        from . import settings
        account_url_kwarg = settings.ACCOUNT_URL_KWARG
        url_kwargs = {}
        if account_url_kwarg in self.kwargs:
            url_kwargs.update({
                account_url_kwarg: self.kwargs[account_url_kwarg]})
        urls = {
            'rules':{
               'api_rules': reverse('rules_api_rule_list', kwargs=url_kwargs),
               'api_detail': reverse('rules_api_app_detail', kwargs=url_kwargs),
               'api_generate_key': reverse(
                   'rules_api_generate_key', kwargs=url_kwargs),
               'api_session_data': reverse(
                   'rules_api_session_data_base', kwargs=url_kwargs),
               'api_engagement': reverse('rules_api_engagement',
                    kwargs=url_kwargs),
               'api_user_engagement': reverse('rules_api_user_engagement',
                    kwargs=url_kwargs),
               'view_user_engagement': reverse('rules_user_engagement',
                    kwargs=url_kwargs),
               'app': reverse('rules_update', kwargs=url_kwargs)}}
        if 'urls' in context:
            for key, val in six.iteritems(urls):
                if key in context['urls']:
                    context['urls'][key].update(val)
                else:
                    context['urls'].update({key: val})
        else:
            context.update({'urls': urls})
        context.update({'app': self.app})
        return context
