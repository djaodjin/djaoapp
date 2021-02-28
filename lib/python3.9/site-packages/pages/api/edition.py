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
import logging

from django.http import Http404
from django.core.exceptions import ValidationError
from django.db.models import Q
from rest_framework.mixins import CreateModelMixin
from rest_framework import generics, response as api_response

from ..models import PageElement, build_content_tree
from ..serializers import (NodeElementSerializer, PageElementSerializer,
    PageElementTagSerializer)
from ..mixins import AccountMixin, PageElementMixin, TrailMixin
from ..utils import validate_title


LOGGER = logging.getLogger(__name__)


class PageElementSearchAPIView(AccountMixin, generics.ListAPIView):
    """
    Search through editable page elements

    **Tags: content

    **Example

    .. code-block:: http

        GET /api/content/search HTTP/1.1

    responds

    .. code-block:: json

        {
          "count": 1,
          "next": null,
          "previous": null,
          "results": [{
            "slug": "hello",
            "path": "/hello",
            "title": "Hello"
          }]
        }
    """
    serializer_class = PageElementSerializer

    def get_queryset(self):
        try:
            queryset = PageElement.objects.filter(account=self.account)
            search_string = self.request.query_params.get('q', None)
            if search_string is not None:
                validate_title(search_string)
                queryset = queryset.filter(
                    Q(tag__icontains=search_string)
                    | Q(title__icontains=search_string))
                return queryset
        except ValidationError:
            pass
        return []


class PageElementTreeAPIView(TrailMixin, generics.RetrieveAPIView):
    """
    Retrieves a content tree

    **Tags: content

    **Example

    .. code-block:: http

        GET /api/content HTTP/1.1

    responds

    .. code-block:: json

        {
            "slug": "boxes-enclosures",
            "path": "/boxes-enclosures",
            "title": "Content root",
            "picture": null,
            "extra": null,
            "children": []
        }
    """
    serializer_class = NodeElementSerializer
    queryset = PageElement.objects.all()

    def retrieve(self, request, *args, **kwargs):
        prefix = self.kwargs.get('path')
        path_parts = self.get_full_element_path(prefix)
        roots = path_parts[-1] if path_parts else None
        content_tree = build_content_tree(roots=roots, prefix=prefix)
        self.attach_picture(content_tree, self.get_pictures())
        return api_response.Response(content_tree)

    def get_roots(self):
        # XXX return self.get_queryset().get_roots()
        # XXX exception `AttributeError: 'QuerySet' object has no attribute
        # XXX 'get_roots'`
        return PageElement.objects.get_roots()

    def get_pictures(self):
        results = {}
        for item in self.get_queryset().filter(
            text__endswith='.png').values('slug', 'text'):
            results.update({item['slug']: item['text']})
        return results

    def attach_picture(self, content_tree, pictures, prefix_picture=None):
        for path, node in content_tree.items():
            slug = path.split('/')[-1]
            prefix_picture = pictures.get(slug, prefix_picture)
            node[0].update({'picture': prefix_picture})
            self.attach_picture(
                node[1], pictures, prefix_picture=prefix_picture)


class PageElementDetail(PageElementMixin, CreateModelMixin,
                        generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieves details on an editable page element

    **Tags: content

    **Example

    .. code-block:: http

        GET /api/content/editables/boxes-enclosures/ HTTP/1.1

    responds

    .. code-block:: json

        {
            "slug": "boxes-enclosures",
            "path": "/boxes-enclosures",
            "text": "Hello"
        }
    """
    serializer_class = PageElementSerializer

    def delete(self, request, *args, **kwargs):
        """
        Deletes an editable page element

        **Tags: content

        **Example

        .. code-block:: http

            DELETE /api/content/editables/boxes-enclosures/ HTTP/1.1
        """
        #pylint:disable=useless-super-delegation
        return super(PageElementDetail, self).delete(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        """
        Creates an editable page element

        **Tags: content

        **Example

        .. code-block:: http

            POST /api/content/editables/boxes-enclosures/ HTTP/1.1

        .. code-block:: json

            {
                "title": "Boxes enclosures"
            }

        responds

        .. code-block:: json

            {
                "slug": "boxes-enclosures",
                "text": "Hello"
            }

        """
        #pylint:disable=useless-super-delegation
        return super(PageElementDetail, self).create(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        """
        Updates an editable page element

        **Example

        .. code-block:: http

            PUT /api/content/editables/boxes-enclosures/ HTTP/1.1

        .. code-block:: json

            {
                "title": "Boxes and enclosures"
            }

        responds

        .. code-block:: json

            {
                "slug": "boxes-enclosures",
                "text": "Hello"
            }
        """
        #pylint:disable=useless-super-delegation
        return super(PageElementDetail, self).put(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(account=self.account)

    def update(self, request, *args, **kwargs):
        try:
            _ = self.get_object()
            return super(PageElementDetail, self).update(
                request, *args, **kwargs)
        except Http404:
            pass
        return super(PageElementDetail, self).create(request, *args, **kwargs)


class PageElementAddTags(PageElementMixin, generics.UpdateAPIView):
    """
    Adds tags to an editable node

    Add tags to a ``PageElement`` if they are not already present.

    **Tags: content

    **Example

    .. code-block:: http

        PUT /api/content/editables/boxes-and-enclosures/add-tags/ HTTP/1.1

    .. code-block:: json

        {
          "tag": "sometag"
        }

    responds

    .. code-block:: json

        {
        }
    """
    serializer_class = PageElementTagSerializer

    def perform_update(self, serializer):
        curr_tags = serializer.instance.tag
        if curr_tags:
            curr_tags = curr_tags.split(',')
        else:
            curr_tags = []
        add_tags = serializer.validated_data['tag'].split(',')
        for tag in add_tags:
            if not tag in curr_tags:
                curr_tags.append(tag)
        serializer.instance.tag = ','.join(curr_tags)
        serializer.instance.save()


class PageElementRemoveTags(PageElementMixin, generics.UpdateAPIView):
    """
    Remove tags from an editable node

    Remove tags from a ``PageElement``.

    **Tags: content

    **Examples

    .. code-block:: http

        PUT /api/content/editables/boxes-and-enclosures/remove-tags/ HTTP/1.1

    .. code-block:: json

        {
          "tag": "sometag"
        }

    responds

    **Examples

    .. code-block:: json

        {
        }
    """
    serializer_class = PageElementTagSerializer

    def perform_update(self, serializer):
        curr_tags = serializer.instance.tag
        if curr_tags:
            curr_tags = curr_tags.split(',')
        else:
            curr_tags = []
        remove_tags = serializer.validated_data['tag'].split(',')
        for tag in remove_tags:
            if tag in curr_tags:
                curr_tags.remove(tag)
        serializer.instance.tag = ','.join(curr_tags)
        serializer.instance.save()
