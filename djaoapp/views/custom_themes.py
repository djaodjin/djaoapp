# Copyright (c) 2021, DjaoDjin inc.
# see LICENSE

from multitier.mixins import build_absolute_uri
from multitier.thread_locals import get_current_site
from pages.views.themes import (
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
        context.update({'site_available_at_url': build_absolute_uri(
            self.request, site=get_current_site().db_object)})
        return context


class ThemePackageDownloadView(ThemePackageDownloadBaseView):

    @property
    def theme(self):
        if not hasattr(self, '_theme'):
            self._theme = self.app.slug
        return self._theme
