# Copyright (c) 2023, DjaoDjin inc.
# see LICENSE
import logging

from django.template.exceptions import (
    TemplateDoesNotExist as DjangoTemplateDoesNotExist)
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.generic import TemplateView
from extended_templates.models import get_show_edit_tools
from jinja2.exceptions import TemplateSyntaxError, UndefinedError
from rules.mixins import AppMixin

from ..api.notifications import get_test_notification_context
from ..compat import reverse

LOGGER = logging.getLogger(__name__)


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
        context.update(get_test_notification_context(self.kwargs.get('template'),
            originated_by=self.request.user))
        return context

    @xframe_options_sameorigin
    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        try:
            result = self.render_to_response(context)
            result.content = result.rendered_content
        except (AttributeError, TemplateSyntaxError, UndefinedError,
            DjangoTemplateDoesNotExist) as err:
            LOGGER.info("error '%s' rendering notification '%s'",
                err, self.kwargs.get('template'))
            messages = context.get('messages', [])
            messages += [str(err)]
            context.update({'messages': messages})
            result = self.response_class(
                request=self.request,
                template='400.html',
                context=context,
                using=self.template_engine,
                content_type=self.content_type)
        return result


class NotificationDetailView(AppMixin, TemplateView):

    template_name = 'notification/detail.html'

    def _get_template_names(self):
        # Not `get_template_names` because we do not had
        # a `get_test_notification_context` context.
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
            'show_edit_tools': get_show_edit_tools(self.request),
            'templates': templates,
            'api_sources': reverse('extended_templates_api_sources'),
            'iframe_url': reverse('notification_inner_frame',
                args=(template_name,))})
        self.update_context_urls(context, {
            'send_test_email': reverse('api_notification_base')
        })
        return context
