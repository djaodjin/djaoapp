# Copyright (c) 2019, DjaoDjin inc.
# see LICENSE

from multitier.mixins import build_absolute_uri
from multitier.thread_locals import get_current_site
from pages.views.themes import (
    ThemePackagesView as  ThemePackageBaseView,
    ThemePackageDownloadView as ThemePackageDownloadBaseView)


class ThemePackageView(ThemePackageBaseView):

    def get_context_data(self, **kwargs):
        context = super(ThemePackageView, self).get_context_data(**kwargs)
        context.update({ 'site_available_at_url': build_absolute_uri(
            self.request, site=get_current_site().db_object),
        })
        return context


class ThemePackageDownloadView(ThemePackageDownloadBaseView):

    @property
    def theme(self):
        if not hasattr(self, '_theme'):
            self._theme = self.app.slug
        return self._theme
