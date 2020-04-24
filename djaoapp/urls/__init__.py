# Copyright (c) 2020, DjaoDjin inc.
# see LICENSE

import os

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponseRedirect
from django.views.generic import TemplateView, RedirectView
from django.contrib.staticfiles.views import serve as django_static_serve

from rules.urldecorators import include, url

from multitier.settings import SLUG_RE
from multitier.urlresolvers import url_sites

from ..compat import reverse_lazy
from ..views.custom_saas import StripeProcessorRedirectView
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
    try:
        # We cannot include admin panels because a `check` for DjangoTemplates
        # will fail when we are using Jinja2 templates.
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
    except LookupError:
        pass

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
    from rest_framework.schemas import get_schema_view
    from ..views.docs import APIDocView
    urlpatterns += [
        url(r'^docs/api/schema/$', get_schema_view(
            title="DjaoApp API",
#            default_version='v1',
            description="API to deploy apps on the djaodjin platform",
#            terms_of_service="https://djaodjin.com/legal/terms-of-use/",
#            contact=openapi.Contact(email=settings.DEFAULT_FROM_EMAIL),
#            license=openapi.License(name="BSD License"),
        ), name='openapi-schema'),
        url(r'^docs/api/', APIDocView.as_view()),
    ]

urlpatterns += [
    url(r'^api/', include('saas.backends.urls.api')),
    url(r'^stripe/billing/connected/',
        StripeProcessorRedirectView.as_view(
            pattern_name='saas_update_bank'),
        name='saas_processor_connected_hook'),
    url('', include('social_django.urls', namespace='social')),

    # Proxy application firewall for all.
    url_sites(r'^', include('djaoapp.urls.proxy')),
]
