# Copyright (c) 2021, DjaoDjin inc.
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

from .. import __version__
from ..compat import reverse_lazy
from ..views.custom_saas import StripeProcessorRedirectView
from ..views.product import ProxyPageView
from ..urlbuilders import (url_authenticated, url_active, url_direct,
    url_provider, url_provider_only, url_self_provider,
    url_frictionless_self_provider)

# These handlers will only be used in production (DEBUG=0)
#pylint:disable=invalid-name
handler403 = 'djaoapp.views.errors.permission_denied'
handler404 = 'djaoapp.views.errors.page_not_found'

if settings.DEBUG:
    from django.contrib import admin
    import debug_toolbar
    from ..views.static import AssetView

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
        urlpatterns = []

    urlpatterns += [
        url(r'^__debug__/', include(debug_toolbar.urls)),

        url(r'(?P<path>favicon.ico)', django_static_serve),
        # You need to run `python manage.py --nostatic` to enable hotreload.
        url(r'(?P<path>%s/.*)' % settings.STATIC_URL.strip('/'),
            AssetView.as_view()),
        url(r'^media/(?P<path>.*)$',
            django_static_serve, {'document_root': settings.MEDIA_ROOT}),
        url(r'^csrf-error/',
            TemplateView.as_view(template_name='csrf-error.html'),
            name='csrf_error'),
    ]
else:
    urlpatterns = []

if settings.API_DEBUG:
    from rest_framework.schemas import get_schema_view
    from ..api_docs.views import APIDocView, NotificationDocView
    urlpatterns += [
        url(r'^docs/api/schema/$', get_schema_view(
            title="DjaoApp API",
            version=__version__,
            description="API to run a SaaS website deployed"\
            " on the djaodjin platform",
#            terms_of_service="https://djaodjin.com/legal/terms-of-use/",
#            contact=openapi.Contact(email=settings.DEFAULT_FROM_EMAIL),
#            license=openapi.License(name="BSD License"),
        ), name='openapi-schema'),
        url(r'^docs/api/notifications/', NotificationDocView.as_view()),
        url(r'^docs/api/', APIDocView.as_view()),
    ]

urlpatterns += [
    url(r'^api/', include('saas.backends.urls.api')),
    url(r'^stripe/billing/connected/',
        StripeProcessorRedirectView.as_view(
            pattern_name='saas_update_bank'),
        name='saas_processor_connected_hook'),

    # Proxy application firewall for all.
    url_sites(r'^', include('djaoapp.urls.proxy')),
    # When there are no `path_prefix` to reference static assets:
    url(r'^(?P<page>\S+)?', ProxyPageView.as_view()),
]
