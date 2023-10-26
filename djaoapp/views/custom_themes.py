# Copyright (c) 2023, DjaoDjin inc.
# see LICENSE

from extended_templates.views.themes import (
    ThemePackagesView as  ThemePackageBaseView,
    ThemePackageDownloadView as ThemePackageDownloadBaseView)

from ..compat import reverse
from ..mixins import NotificationsMixin

class ThemePackageView(NotificationsMixin, ThemePackageBaseView):

    def add_edition_tools(self, response, context=None):
        # Overrides `ThemePackageBaseView.add_edition_tools` implementation
        # in version 0.4.5 because it is looking for a _body_top.html
        # template that does not exist. In djaoapp, we inject the tools
        # through a decorator, not the `View` class itself.
        return None

    def get_context_data(self, **kwargs):
        context = super(ThemePackageView, self).get_context_data(**kwargs)
        context.update({'notifications': self.get_notifications()})
        self.update_context_urls(context, {
            'send_test_email': reverse('api_notification_base')
        })
        return context


class ThemePackageDownloadView(ThemePackageDownloadBaseView):

    @property
    def theme(self):
        if not hasattr(self, '_theme'):
            self._theme = self.app.slug
        return self._theme
