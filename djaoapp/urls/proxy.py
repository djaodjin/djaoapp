# Copyright (c) 2020, DjaoDjin inc.
# see LICENSE

from django.conf import settings
from django.views.generic import TemplateView
from multitier.urlresolvers import site_patterns
from rules.urldecorators import include, url

if settings.DEBUG:
    from django.views.defaults import server_error
    from ..views.errors import permission_denied, page_not_found
    urlpatterns = site_patterns(
        url(r'^403/$', permission_denied),
        url(r'^404/$', page_not_found),
        url(r'^500/$', server_error),
        url(r'^register/disabled/$', TemplateView.as_view(
            template_name='accounts/disabled.html')))
else:
    urlpatterns = []

urlpatterns += site_patterns(
    url(r'^', include('djaoapp.urls.api')),
    url(r'^', include('djaoapp.urls.views')),
)
