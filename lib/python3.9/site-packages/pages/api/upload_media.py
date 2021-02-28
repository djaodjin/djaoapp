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


import hashlib, os

from django.utils.encoding import force_text
from deployutils.helpers import datetime_or_now
from rest_framework import parsers, status
from rest_framework.generics import ListCreateAPIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from ..models import MediaTag, PageElement
from ..mixins import AccountMixin, UploadedImageMixin
from ..serializers import AssetSerializer, MediaItemListSerializer
from ..utils import validate_title, get_default_storage

from ..compat import urljoin, urlparse, urlunparse


class MediaListAPIView(UploadedImageMixin, AccountMixin, ListCreateAPIView):
    """
    Lists static asset files

    **Examples

    .. code-block:: http

        GET /api/assets/ HTTP/1.1

    responds

    .. code-block:: json

        {
          "count": 1,
          "previous": null,
          "next": null,
          "results": [{
              "location": "/media/image-001.jpg",
              "updated_at": "2016-10-26T00:00:00.00000+00:00",
              "tags": ""
          }]
        }

    """
    store_hash = True
    replace_stored = False
    content_type = None
    serializer_class = AssetSerializer
    pagination_class = PageNumberPagination
    parser_classes = (parsers.JSONParser, parsers.FormParser,
        parsers.MultiPartParser, parsers.FileUploadParser)

    def get(self, request, *args, **kwargs): #pylint:disable=unused-argument
        tags = None
        search = request.GET.get('q')
        if search:
            validate_title(search)
            tags = MediaTag.objects.filter(tag__startswith=search)\
                .values_list('location', flat=True)
        results, total_count = self.list_media(
            get_default_storage(self.request, self.account), tags,
            prefix=kwargs.get('path', '.'))
        return self.get_paginated_response(results)

    def get_paginated_response(self, results):
        # XXX - Deactivate pagination until not
        # implemented in djaodjin-sidebar-gallery
        # page = self.paginate_queryset(queryset['results'])
        # if page is not None:
        #     queryset = {'count': len(page), 'results' : page}
        total_count = len(results)
        return Response({
            'count': total_count,
            'results': sorted(results, key=lambda x: x['updated_at'])
        })

    def post(self, request, *args, **kwargs):
        """
        Uploads a static asset file

        **Examples

        .. code-block:: http

            POST /api/assets/ HTTP/1.1

        """
        #pylint: disable=unused-argument,too-many-locals
        uploaded_file = request.data['file']
        if self.content_type:
            # We optionally force the content_type because S3Store uses
            # mimetypes.guess and surprisingly it doesn't get it correct
            # for 'text/css'.
            uploaded_file.content_type = self.content_type
        sha1 = hashlib.sha1(uploaded_file.read()).hexdigest()

        # Store filenames with forward slashes, even on Windows
        filename = force_text(uploaded_file.name.replace('\\', '/'))
        sha1_filename = sha1 + os.path.splitext(filename)[1]
        storage = get_default_storage(self.request, self.account)
        stored_filename = sha1_filename if self.store_hash else filename
        prefix = request.data.get('prefix', None)
        if prefix is not None:
            stored_filename = urljoin(prefix, stored_filename)

        result = {}
        if storage.exists(stored_filename):
            if self.replace_stored:
                storage.delete(stored_filename)
                storage.save(stored_filename, uploaded_file)
                response_status = status.HTTP_201_CREATED
            else:
                result = {
                    "message": "%s is already in the gallery." % filename}
                response_status = status.HTTP_200_OK
        else:
            storage.save(stored_filename, uploaded_file)
            response_status = status.HTTP_201_CREATED
        result.update({
            'location': storage.url(stored_filename),
            'updated_at': datetime_or_now(),
            'tags': []
            })
        return Response(self.get_serializer().to_representation(result),
            status=response_status)

    def delete(self, request, *args, **kwargs):
        """
        Deletes static assets file

        **Examples

        .. code-block:: http

            DELETE /api/assets/ HTTP/1.1

        .. code-block:: json

            {
                "items": [
                    {"location": "/media/item/url1.jpg"},
                    {"location": "/media/item/url2.jpg"}
                ]
            }

        """
        #pylint: disable=unused-argument,too-many-locals
        storage = get_default_storage(self.request, self.account)
        serializer = MediaItemListSerializer(data=request.data)
        serializer.is_valid()
        validated_data = serializer.validated_data
        filter_list = self.build_filter_list(validated_data)
        results, _ = self.list_media(storage, filter_list,
            prefix=kwargs.get('path', '.'))
        if not results:
            return Response({}, status=status.HTTP_404_NOT_FOUND)

        base = storage.url('')
        for item in results:
            location = item['location']
            if location.startswith(base):
                location = location[len(base):]
                storage.delete(location)
                # Delete all MediaTag and PageElement using this location
                MediaTag.objects.filter(location=location).delete()
                elements = PageElement.objects.filter(text=location)
                for element in elements:
                    element.text = ""
                    element.save()
        return Response({}, status=status.HTTP_204_NO_CONTENT)

    def put(self, request, *args, **kwargs):
        """
        Updates meta tags on assets

        **Examples

        .. code-block:: http

            PUT /api/assets/ HTTP/1.1

        .. code-block:: json

            {
                "items": [
                    {"location": "/media/item/url1.jpg"},
                    {"location": "/media/item/url2.jpg"}
                ],
                "tags": ["photo", "homepage"]
            }

        When the API returns, both assets file listed in items will be tagged
        with 'photo' and 'homepage'. Those tags can then be used later on
        in searches.
        """
        #pylint: disable=unused-argument
        serializer = MediaItemListSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        assets, total_count = self.list_media(
            get_default_storage(self.request, self.account),
            self.build_filter_list(serializer.validated_data))
        if not assets:
            return Response({}, status=status.HTTP_404_NOT_FOUND)

        tags = [tag for tag in serializer.validated_data.get('tags') if tag]
        for item in assets:
            parts = urlparse(item['location'])
            location = urlunparse((parts.scheme, parts.netloc, parts.path,
                None, None, None))
            media_tags = MediaTag.objects.filter(location=location)
            for tag in tags:
                MediaTag.objects.get_or_create(location=location, tag=tag)
            # Remove tags which are no more set for the location.
            media_tags.exclude(tag__in=tags).delete()

            # Update tags returned by the API.
            item['tags'] = ",".join(list(MediaTag.objects.filter(
                location=location).values_list('tag', flat=True)))

        serializer = self.get_serializer(
            sorted(assets, key=lambda x: x['updated_at']), many=True)
        return self.get_paginated_response(serializer.data)
