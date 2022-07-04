# Copyright (c) 2022, DjaoDjin inc.
# see LICENSE

from extended_templates.views.themes import (
    ThemePackagesView as  ThemePackageBaseView,
    ThemePackageDownloadView as ThemePackageDownloadBaseView)

from ..compat import reverse
from ..mixins import NotificationsMixin

class ThemePackageView(NotificationsMixin, ThemePackageBaseView):

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
