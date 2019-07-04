# Copyright (c) 2019, DjaoDjin inc.
# see LICENSE

from django.conf import settings
from multitier.urlresolvers import site_patterns
from urldecorators import include, url

if settings.DEBUG:
    from django.views.defaults import server_error
    from ..views.errors import permission_denied, page_not_found
    urlpatterns = site_patterns(
        url(r'^403/$', permission_denied),
        url(r'^404/$', page_not_found),
        url(r'^500/$', server_error)
    )
else:
    urlpatterns = []

urlpatterns += site_patterns(
    url(r'^', include('djaoapp.urls.api')),
    url(r'^', include('djaoapp.urls.views')),
)
