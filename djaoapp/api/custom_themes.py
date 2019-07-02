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
    """
    Returns the URL endpoint to which requests passing the access rules
    are forwarded to, and the format in which the session information
    is encoded.

    When running tests, you can retrieve the actual session information
    for a specific user through the `/proxy/sessions/{user}/` API call.

    **Tags: rbac

    **Examples

    .. code-block:: http

        GET /api/proxy/ HTTP/1.1

    responds

    .. code-block:: json

        {
          "slug": "cowork",
          "entry_point": "http://localhost:8001/",
          "session_backend": 1
        }
    """
    serializer_class = AppSerializer
