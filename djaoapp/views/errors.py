# Copyright (c) 2018, DjaoDjin inc.
# see LICENSE

import logging

import django
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.views.decorators.csrf import requires_csrf_token
from django.views.defaults import page_not_found as base_page_not_found
from rest_framework.views import APIView, exception_handler
from rest_framework.renderers import JSONRenderer, StaticHTMLRenderer

LOGGER = logging.getLogger(__name__)


class PermissionDeniedView(APIView):

    def __init__(self, exc):
        #pylint:disable=super-init-not-called
        self.exception = exc

    def get_renderers(self):
        return [JSONRenderer(), StaticHTMLRenderer()]

    def dispatch(self, request, *args, **kwargs):
        request = self.initialize_request(request, *args, **kwargs)
        self.request = request
        self.headers = self.default_response_headers
        self.format_kwarg = self.get_format_suffix(**kwargs)
        response = self.handle_exception(self.exception)
        response = self.finalize_response(request, response, *args, **kwargs)
        return response


def drf_exception_handler(exc, context):
    """
    Handler to capture input parameters when a 500 exception occurs.
    """
    # XXX This is not ideal as it doesn't show the actual text - still better
    #     than nothing.
    response = exception_handler(exc, context)
    if response is None:
        request = context.get('request', None)
        if request and request.method not in ['GET', 'HEAD', 'OPTIONS']:
            #pylint:disable=protected-access
            request._request.POST = request.data
    return response


@requires_csrf_token
def permission_denied(request, exception=None, template_name='403.html'):
    #pylint:disable=unused-argument
    """
    This handler is used to convert ``PermissionDenied`` exceptions
    into either HTML or JSON content-type based on the request.
    """
    if exception is None:
        exception = PermissionDenied()
    response = PermissionDeniedView(exception).dispatch(request)
    response.render()
    return response

@requires_csrf_token
def page_not_found(request, exception=None, template_name='404.html'):
    if exception is None:
        exception = ObjectDoesNotExist()
    else:
        LOGGER.warning(
            "Not found: %s", exception, extra={'request': request})
    # prototype changed between Django versions
    if django.VERSION[0] <= 1 and django.VERSION[1] < 9:
        #pylint:disable=no-value-for-parameter
        return base_page_not_found(request, template_name=template_name)
    #pylint:disable=redundant-keyword-arg
    return base_page_not_found(request, exception, template_name=template_name)
