# Copyright (c) 2018, DjaoDjin inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED
# TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
# OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
# OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
# ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from collections import OrderedDict

from drf_yasg import openapi
from drf_yasg.inspectors.query import DjangoRestResponsePagination
from rest_framework.pagination import CursorPagination
from saas.pagination import TotalPagination


class DocTotalPagination(DjangoRestResponsePagination):
    """
    Provides response schema pagination warpping for saas.TotalPagination
    """
    def get_paginated_response(self, paginator, response_schema):
        assert response_schema.type == openapi.TYPE_ARRAY, "array return"\
            " expected for paged response"
        paged_schema = None
        if isinstance(paginator, TotalPagination):
            has_count = not isinstance(paginator, CursorPagination)
            paged_schema = openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties=OrderedDict((
                    ('total', openapi.Schema(
                        type=openapi.TYPE_INTEGER)),
                    ('count', openapi.Schema(
                        type=openapi.TYPE_INTEGER) if has_count else None),
                    ('next', openapi.Schema(
                        type=openapi.TYPE_STRING, format=openapi.FORMAT_URI)),
                    ('previous', openapi.Schema(
                        type=openapi.TYPE_STRING, format=openapi.FORMAT_URI)),
                    ('results', response_schema),
                )),
                required=['total', 'count', 'results']
            )
        return paged_schema
