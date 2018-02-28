# Copyright (c) 2018, DjaoDjin inc.
# see LICENSE

import os

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse_lazy
from django.http import HttpResponseRedirect
from django.views.generic import TemplateView, RedirectView
from django.contrib.staticfiles.views import serve as django_static_serve

from urldecorators import include, url

from multitier.settings import SLUG_RE

from ..urlbuilders import (url_authenticated, url_active, url_direct,
    url_provider, url_provider_only, url_self_provider,
    url_frictionless_self_provider)

import djaoapp.signals

# These handlers will only be used in production (DEBUG=0)
#pylint:disable=invalid-name
handler403 = 'djaoapp.views.errors.permission_denied'
handler404 = 'djaoapp.views.errors.page_not_found'

if settings.DEBUG:
    from django.contrib import admin
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns
    from django.conf.urls.static import static
    import debug_toolbar

    admin.autodiscover()
    urlpatterns = staticfiles_urlpatterns() \
        + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += [
        url(r'^__debug__/', include(debug_toolbar.urls)),
        url(r'^csrf-error/',
            TemplateView.as_view(template_name='csrf-error.html'),
            name='csrf_error'),
        url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
        url(r'^admin/', include(admin.site.urls)),
        url(r'^favicon.ico$', django_static_serve,
            {'path': 'favicon.ico'})
    ]
else:
    urlpatterns = [
        url(r'^static/(?P<path>.*)$', django_static_serve,
            {'document_root': settings.STATIC_ROOT, 'show_indexes':True}),
        url(r'^media/(?P<path>.*)$', django_static_serve,
            {'document_root': settings.MEDIA_ROOT, 'show_indexes':True}),
    ]

urlpatterns += [
    url(r'^', include('saas.backends.urls')),
    url('', include('social_django.urls', namespace='social')),

    # Proxy application firewall for all.
    url(r'^', include('djaoapp.urls.proxy')),
]
