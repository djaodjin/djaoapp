# Copyright (c) 2019, DjaoDjin inc.
# see LICENSE

from django.http import HttpResponseRedirect
from multitier.mixins import build_absolute_uri
from multitier.thread_locals import get_current_site
from pages.views.themes import (
    ThemePackagesView as  ThemePackageBaseView,
    ThemePackageDownloadView as ThemePackageDownloadBaseView)

from ..compat import reverse


class ThemePackageView(ThemePackageBaseView):

    def get_context_data(self, **kwargs):
        context = super(ThemePackageView, self).get_context_data(**kwargs)
        context.update({
            'site_available_at_url': build_absolute_uri(
                self.request, site=get_current_site().db_object),
            'show_edit_tools': self.app.show_edit_tools,
        })
        return context

    def post(self, request, *args, **kwargs):
        show = request.POST.get('show_edit_tools') == 'on'
        self.app.show_edit_tools = show
        self.app.save()
        return HttpResponseRedirect(reverse('theme_update'))


class ThemePackageDownloadView(ThemePackageDownloadBaseView):

    @property
    def theme(self):
        if not hasattr(self, '_theme'):
            self._theme = self.app.slug
        return self._theme
