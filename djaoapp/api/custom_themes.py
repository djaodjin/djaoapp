# Copyright (c) 2021, DjaoDjin inc.
# see LICENSE

from pages.api.themes import (
    ThemePackageListAPIView as ThemePackageListAPIBaseView)


class DjaoAppThemePackageListAPIView(ThemePackageListAPIBaseView):

    @property
    def theme(self):
        if not hasattr(self, '_theme'):
            self._theme = self.app.slug
        return self._theme
