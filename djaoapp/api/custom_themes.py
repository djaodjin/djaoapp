# Copyright (c) 2018, DjaoDjin inc.
# see LICENSE

from pages.api.themes import (
    ThemePackageListAPIView as ThemePackageListAPIBaseView)
from rules.api.keys import (
    AppUpdateAPIView as RulesAppUpdateAPIView)

from .serializers import AppSerializer


class ThemePackageListAPIView(ThemePackageListAPIBaseView):

    @property
    def theme(self):
        if not hasattr(self, '_theme'):
            self._theme = self.app.slug
        return self._theme


class AppUpdateAPIView(RulesAppUpdateAPIView):
    serializer_class = AppSerializer
