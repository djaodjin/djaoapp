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
from drf_yasg.inspectors import NotHandled, DjangoRestResponsePagination
from rest_framework.pagination import CursorPagination
from saas.pagination import BalancePagination, TotalPagination


class DocBalancePagination(DjangoRestResponsePagination):
    """
    Provides response schema pagination warpping for saas.BalancePagination
    """
    def get_paginated_response(self, paginator, response_schema):
        assert response_schema.type == openapi.TYPE_ARRAY, "array return"\
            " expected for paged response"
        paged_schema = NotHandled
        if isinstance(paginator, BalancePagination):
            has_count = not isinstance(paginator, CursorPagination)
            paged_schema = openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties=OrderedDict((
                    ('balance', openapi.Schema(
                        type=openapi.TYPE_INTEGER,
                        description="balance of all transactions in cents"\
                        " (i.e. 100ths) of unit")),
                    ('unit', openapi.Schema(
                        type=openapi.TYPE_INTEGER,
                        description="three-letter ISO 4217 code"\
                        " for currency unit (ex: usd)")),
                    ('count', openapi.Schema(
                        type=openapi.TYPE_INTEGER,
                        description="The number of records"
                    ) if has_count else None),
                    ('next', openapi.Schema(
                        type=openapi.TYPE_STRING, format=openapi.FORMAT_URI,
                        description="API end point to get the next page"\
                            "of records matching the query")),
                    ('previous', openapi.Schema(
                        type=openapi.TYPE_STRING, format=openapi.FORMAT_URI,
                        description="API end point to get the previous page"\
                            "of records matching the query")),
                    ('results', response_schema),
                )),
                required=['balance', 'unit', 'count', 'results']
            )
        return paged_schema


class DocTotalPagination(DjangoRestResponsePagination):
    """
    Provides response schema pagination warpping for saas.TotalPagination
    """
    def get_paginated_response(self, paginator, response_schema):
        assert response_schema.type == openapi.TYPE_ARRAY, "array return"\
            " expected for paged response"
        paged_schema = NotHandled
        if isinstance(paginator, TotalPagination):
            has_count = not isinstance(paginator, CursorPagination)
            paged_schema = openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties=OrderedDict((
                    ('total', openapi.Schema(
                        type=openapi.TYPE_INTEGER,
                        description=
                            "The sum of all Charge amount (in unit)")),
                    ('count', openapi.Schema(
                        type=openapi.TYPE_INTEGER,
                        description="The number of records"
                    ) if has_count else None),
                    ('next', openapi.Schema(
                        type=openapi.TYPE_STRING, format=openapi.FORMAT_URI,
                        description="API end point to get the next page"\
                            "of records matching the query")),
                    ('previous', openapi.Schema(
                        type=openapi.TYPE_STRING, format=openapi.FORMAT_URI,
                        description="API end point to get the previous page"\
                            "of records matching the query")),
                    ('results', response_schema),
                )),
                required=['total', 'count', 'results']
            )
        return paged_schema
