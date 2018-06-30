# Copyright (c) 2018, DjaoDjin inc.
# see LICENSE

from pages.views.themes import (
    ThemePackageDownloadView as ThemePackageDownloadBaseView)


class ThemePackageDownloadView(ThemePackageDownloadBaseView):

    @property
    def theme(self):
        if not hasattr(self, '_theme'):
            self._theme = self.app.slug
        return self._theme
