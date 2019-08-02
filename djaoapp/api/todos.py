# Copyright (c) 2019, DjaoDjin inc.
# see LICENSE
from __future__ import unicode_literals

import logging

from django.conf import settings
from rest_framework.generics import ListAPIView
from saas.mixins import ProviderMixin
from signup.serializers import ActivitySerializer

LOGGER = logging.getLogger(__name__)


def list_todos(request, provider=None):
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
