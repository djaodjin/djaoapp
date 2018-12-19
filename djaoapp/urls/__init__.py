# Copyright (c) 2018, DjaoDjin inc.
# see LICENSE

import os

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponseRedirect
from django.views.generic import TemplateView, RedirectView
from django.contrib.staticfiles.views import serve as django_static_serve

from urldecorators import include, url

from multitier.settings import SLUG_RE
from multitier.urlresolvers import url_sites

from ..compat import reverse_lazy
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

    # admin doc and panel
    admin.autodiscover()
    try:
        urlpatterns = [
            url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
            url(r'^admin/', admin.site.urls),
        ]
    except ImproperlyConfigured: # Django <= 1.9
        urlpatterns = [
            url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
            url(r'^admin/', include(admin.site.urls)),
        ]

    urlpatterns = staticfiles_urlpatterns() \
        + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += [
        url(r'^__debug__/', include(debug_toolbar.urls)),
        url(r'^csrf-error/',
            TemplateView.as_view(template_name='csrf-error.html'),
            name='csrf_error'),
        url(r'^favicon.ico$', django_static_serve,
            {'path': 'favicon.ico'}),
    ]
else:
    urlpatterns = []

if settings.API_DEBUG:
    from ..views.docs import APIDocView, schema_view
    urlpatterns += [
        url(r'^docs/api/redoc/$', schema_view.with_ui('redoc',
            cache_timeout=None), name='schema-redoc'),
        url(r'^docs/api/swagger(?P<format>\.json|\.yaml)$',
            schema_view.without_ui(cache_timeout=None), name='schema-json'),
        url(r'^docs/api/', APIDocView.as_view()),
    ]

urlpatterns += [
    url(r'^api/', include('saas.backends.urls.api')),
    url(r'^', include('saas.backends.urls.views')),
    url('', include('social_django.urls', namespace='social')),

    # Proxy application firewall for all.
    url_sites(r'^', include('djaoapp.urls.proxy')),
]
