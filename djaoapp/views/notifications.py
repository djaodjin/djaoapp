# Copyright (c) 2018, DjaoDjin inc.
# see LICENSE

from django.views.generic import TemplateView
from rules.mixins import AppMixin
from saas.models import get_broker

from ..api.notifications import get_test_email_context
from ..compat import reverse


class NotificationInnerFrameView(AppMixin, TemplateView):

    template_name = 'notification/detail.html'

    def get_template_names(self):
        template_name = self.kwargs.get('template', None)
        if template_name.endswith('_role_added'):
            return ["notification/%s.eml" % template_name,
                "notification/role_added.eml"]
        return ["notification/%s.eml" % template_name]

    def get_context_data(self, **kwargs):
        context = super(NotificationInnerFrameView, self).get_context_data(
            **kwargs)
        context.update(get_test_email_context())
        return context


class NotificationDetailView(AppMixin, TemplateView):

    template_name = 'notification/detail.html'

    def get_context_data(self, **kwargs):
        context = super(NotificationDetailView, self).get_context_data(**kwargs)
        context.update({
            'iframe_url': reverse('notification_inner_frame',
                args=(self.kwargs.get('template'),))})
        return context


class NotificationListView(AppMixin, TemplateView):

    template_name = 'notification/index.html'

    def get_object(self, queryset=None): #pylint:disable=unused-argument
        return self.app

    def get_context_data(self, **kwargs):
        context = super(NotificationListView, self).get_context_data(**kwargs)
        broker = get_broker()
        context.update({'role_descriptions': broker.get_role_descriptions()})
        self.update_context_urls(context, {
            'send_test_email': reverse('api_notification_base')
        })
        return context
