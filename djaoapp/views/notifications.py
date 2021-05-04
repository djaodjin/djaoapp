# Copyright (c) 2021, DjaoDjin inc.
# see LICENSE

from django.views.generic import TemplateView
from rules.mixins import AppMixin

from ..api.notifications import get_test_email_context
from ..compat import reverse


class NotificationInnerFrameView(AppMixin, TemplateView):

    template_name = 'notification/detail.html'

    def get_template_names(self):
        template_name = self.kwargs.get('template', None)

        if template_name.endswith('_role_grant_created'):
            return ["notification/%s.eml" % template_name,
                "notification/role_grant_created.eml"]

        return ["notification/%s.eml" % template_name]

    def get_context_data(self, **kwargs):
        context = super(NotificationInnerFrameView, self).get_context_data(
            **kwargs)
        context.update(get_test_email_context())
        return context


class NotificationDetailView(AppMixin, TemplateView):

    template_name = 'notification/detail.html'

    def _get_template_names(self):
        # Not `get_template_names` because we do not had
        # a `get_test_email_context` context.
        template_name = self.kwargs.get('template', None)

        if template_name.endswith('_role_grant_created'):
            return ["notification/%s.eml" % template_name,
                "notification/role_grant_created.eml"]

        return ["notification/%s.eml" % template_name]

    def get_context_data(self, **kwargs):
        context = super(NotificationDetailView, self).get_context_data(**kwargs)
        base = 'notification/%s.eml'
        template_name = self.kwargs.get('template')
        templates = [{'name': base % 'base', 'index': 0},
            {'name': base % template_name, 'index': 1}]
        context.update({
            'show_edit_tools': self.app.show_edit_tools,
            'templates': templates,
            'api_sources': reverse('pages_api_sources'),
            'iframe_url': reverse('notification_inner_frame',
                args=(template_name,))})
        self.update_context_urls(context, {
            'send_test_email': reverse('api_notification_base')
        })
        return context
