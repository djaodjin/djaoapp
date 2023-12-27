# Copyright (c) 2023, DjaoDjin inc.
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

from rest_framework.pagination import (
    PageNumberPagination as BasePageNumberPagination)

from .compat import gettext_lazy as _


class PageNumberPagination(BasePageNumberPagination):

    max_page_size = 100
    page_size_query_param = 'page_size'
    page_size_query_description = _("Number of results to return per page"\
    " between 1 and 100 (defaults to 25).")

    def get_paginated_response_schema(self, schema):
        if 'description' not in schema:
            schema.update({'description': "Records in the queryset"})
        return {
            'type': 'object',
            'properties': {
                'count': {
                    'type': 'integer',
                    'description': "The number of records"
                },
                'next': {
                    'type': 'string',
                    'description': "API end point to get the next page"\
                        " of records matching the query",
                    'nullable': True,
                    'format': 'uri',
                },
                'previous': {
                    'type': 'string',
                    'description': "API end point to get the previous page"\
                        " of records matching the query",
                    'nullable': True,
                    'format': 'uri',
                },
                'results': schema,
            },
        }
