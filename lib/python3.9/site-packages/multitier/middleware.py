# Copyright (c) 2020, Djaodjin Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
# OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
# OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
# ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


import logging, re

from django.conf import settings as django_settings
from django.db.models import Q
from django.http import Http404

from . import settings
from .utils import get_site_model
from .thread_locals import clear_cache, set_current_site
from .compat import MiddlewareMixin


LOGGER = logging.getLogger(__name__)


class SiteMiddleware(MiddlewareMixin):

    @staticmethod
    def as_candidate_site(request):
        """
        Returns a ``Site`` based on the request host.
        """
        site = None
        candidate = None
        path_prefix = ''
        all_host_allowed = False
        app_domain = 'localhost'
        host = request.get_host().split(':')[0].lower()
        if django_settings.ALLOWED_HOSTS:
            first_allowed_host = django_settings.ALLOWED_HOSTS[0]
            if first_allowed_host == '*':
                all_host_allowed = True
            else:
                app_domain = django_settings.ALLOWED_HOSTS[0]
                if app_domain.startswith('.'):
                    app_domain = app_domain[1:]
            look = re.match(r'^((?P<subdomain>\S+)\.)?%s(?::.*)?$' % app_domain,
                host)
            if look and look.group('subdomain'):
                candidate = look.group('subdomain')
            if host == app_domain and not candidate:
                look = re.match(r'^/(?P<path_prefix>[a-zA-Z0-9\-]+).*',
                    request.path)
                # no trailing '/' is OK here.
                if look:
                    path_prefix = look.group('path_prefix')
                    # It is either a subdomain or a path_prefix. Trying both
                    # match one after the other will override the candidate.
                    if path_prefix:
                        candidate = path_prefix
        try:
            flt = Q(domain=host)
            if candidate:
                flt = flt | Q(slug=candidate)
            if all_host_allowed or host == app_domain:
                flt = flt | Q(slug=settings.DEFAULT_SITE)
            queryset = get_site_model().objects.filter(flt).order_by(
                '-domain', '-pk')
            site = queryset.first()
            if site is None:
                #pylint: disable=raising-bad-type
                raise get_site_model().DoesNotExist
            if not site.is_path_prefix or site.slug != path_prefix:
                path_prefix = ''
        except get_site_model().DoesNotExist:
            if candidate is not None:
                msg = "'%s' nor subdomain '%s%s' could be found." % (
                    host, candidate, django_settings.ALLOWED_HOSTS[0])
            else:
                msg = "'%s' could not be found." % str(host)
            LOGGER.debug(msg, extra={'request': request})
            raise Http404(msg)
        return site, path_prefix

    def process_request(self, request):
        """
        Adds a ``client`` attribute to the ``request`` parameter.
        """
        clear_cache()
        site, path_prefix = self.as_candidate_site(request)

        # This is where you would typically override ``request.urlconf``
        # based on the ``Site``.

        # Set thread locals.
        # 1. First the site such that the we route requests for ``Site``
        # instances to the correct database.
        # 2. Then we hack into the translation module to get
        # django.core.urlresolvers to play nicely with our url scheme
        # with regards to the active site.
        set_current_site(site, path_prefix,
            default_scheme=request.scheme, default_host=request.get_host(),
            request=request)
        return None


class SetRemoteAddrFromForwardedFor(MiddlewareMixin):
    """
    set REMOTE_ADDR based on HTTP_X_FORWARDED_FOR.
    """

    @staticmethod
    def process_request(request):
        if request.META.get('REMOTE_ADDR', '127.0.0.1') == '127.0.0.1':
            request.META.update({'REMOTE_ADDR':
                request.META.get('HTTP_X_FORWARDED_FOR', '127.0.0.1')})
        return None
