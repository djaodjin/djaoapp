# Copyright (c) 2019, DjaoDjin inc.
# see LICENSE
from __future__ import unicode_literals

import logging

from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import serializers
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response
from saas.mixins import ProviderMixin
from signup.serializers import ActivitySerializer, NoModelSerializer

from .. import __version__
from ..compat import import_string


LOGGER = logging.getLogger(__name__)


class VersionSerializer(NoModelSerializer):

    version = serializers.SerializerMethodField(read_only=True)

    @staticmethod
    def get_version(obj):
        #pylint:disable=unused-argument
        return __version__


class DjaoAppAPIVersion(RetrieveAPIView):
    """
    Retrieves version of the API
    """
    serializer_class = VersionSerializer

    @method_decorator(ensure_csrf_cookie)
    def get(self, request, *args, **kwargs):
        """
        Retrieves version of the API

        **Example

        .. code-block:: http

            GET /api HTTP/1.1

        responds

        .. code-block:: json

            {
              "version": "2019-11-23"
            }
        """
        return VersionSerializer({'version': __version__})


def list_todos(request, provider=None):
    #pylint:disable=unused-argument
    return []


class TodosAPIView(ProviderMixin, ListAPIView):
    """
    Retrieves news and items to take care of.

    **Tags: metrics

    **Example

    .. code-block:: http

        GET /api/todos/ HTTP/1.1

    responds

    .. code-block:: json

        {
          "count": 1,
          "next": null,
          "previous": null,
          "results": [
            {
              "created_at": "20200530T00:00:00Z",
              "created_by": "djaoapp",
              "text": "connect processor",
              "account": null
            }
          ]
        }
    """
    serializer_class = ActivitySerializer

    def get_queryset(self):
        if (hasattr(settings, 'LIST_TODOS_CALLABLE') and
            settings.LIST_TODOS_CALLABLE):
            try:
                return import_string(
                    settings.LIST_TODOS_CALLABLE)(self.request,
                        provider=self.provider)
            except ImportError:
                pass
        return list_todos(self.request, provider=self.provider)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
