# Copyright (c) 2020, DjaoDjin inc.
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

import datetime, logging

from dateutil.relativedelta import relativedelta
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import F, Q, Max, Count
from django.db.utils import IntegrityError
from django.utils.timezone import utc
from rest_framework.generics import (GenericAPIView,
    ListCreateAPIView, RetrieveUpdateDestroyAPIView, ListAPIView)
from rest_framework.response import Response
from rest_framework import serializers

from .serializers import (RuleSerializer, RuleRankUpdateSerializer,
    UserEngagementSerializer, EngagementsSerializer)
from ..docs import swagger_auto_schema
from ..mixins import AppMixin
from ..models import Rule, Engagement
from ..utils import parse_tz, datetime_or_now

#pylint: disable=no-init

LOGGER = logging.getLogger(__name__)


class UpdateRuleSerializer(RuleSerializer):

    class Meta:
        model = Rule
        fields = ('rank', 'path', 'allow', 'is_forward', 'engaged')
        read_only_fields = ('path',)


class RuleMixin(AppMixin):

    model = Rule
    serializer_class = RuleSerializer
    lookup_field = 'path'
    lookup_url_kwarg = 'rule'

    def get_queryset(self):
        return self.model.objects.get_rules(self.app)

    def perform_create(self, serializer):
        # We don't compact ranks after DELETE
        last_rank = self.get_queryset().aggregate(
            Max('rank')).get('rank__max', 0)
        # If the key exists and return None the default value is not applied
        last_rank = last_rank + 1 if last_rank is not None else 1
        serializer.save(app=self.app, rank=last_rank)

    def perform_update(self, serializer):
        serializer.save(app=self.app)


class RuleListAPIView(RuleMixin, ListCreateAPIView):
    """
    Lists access rules

    Queries a page (``PAGE_SIZE`` records) of ``Rule``.

    **Tags: rbac

    **Examples

    .. code-block:: http

        GET /api/proxy/rules HTTP/1.1

    responds

    .. code-block:: json

        {
            "count": 1,
            "next": null,
            "previous": null,
            "results": [
                {
                    "rank": 0,
                    "path": "/",
                    "allow": "authenticated",
                    "is_forward": true,
                    "engaged": "app"
                }
            ]
        }
    """
    def get_queryset(self):
        return super(RuleListAPIView, self).get_queryset().order_by('rank')

    @staticmethod
    def check_path(request):
        if 'path' not in request.data:
            request.data.update({'path': "/"})
        if not request.data['path'].endswith('/'):
            request.data['path'] += '/'
        if not request.data['path'].startswith('/'):
            request.data['path'] = '/' + request.data['path']

    def perform_create(self, serializer):
        try:
            return super(RuleListAPIView, self).perform_create(serializer)
        except IntegrityError as err:
            if 'uniq' in str(err).lower():
                raise serializers.ValidationError({'detail':
                    "Rule with path prefix '%s' already exists."
                    % serializer.validated_data['path']})
            raise

    def post(self, request, *args, **kwargs):
        """
        Creates an access rule

        **Tags: rbac

        **Examples

        .. code-block:: http

            POST /api/proxy/rules/ HTTP/1.1

        .. code-block:: json

            {
                "rank": 0,
                "path": "/",
                "allow": "authenticated",
                "is_forward": true,
                "engaged": ""
            }

        responds

            {
                "rank": 0,
                "path": "/",
                "allow": "authenticated",
                "is_forward": true,
                "engaged": ""
            }
        """
        self.check_path(request)
        return self.create(request, *args, **kwargs)

    @swagger_auto_schema(request_body=RuleRankUpdateSerializer)
    def patch(self, request, *args, **kwargs):
        """
        Updates order of rules

        When receiving a request like [{"newpos": 1, "oldpos": 3}],
        it will move the rule at position 3 to position 1, updating all
        rules ranks in-between.

        **Tags: rbac

        **Examples

        .. code-block:: http

            POST /api/proxy/rules/ HTTP/1.1

        .. code-block:: json

            {"updates": [
              {
                "newpos": 1,
                "oldpos": 3
               }
            ]}
        """
        serializer = RuleRankUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            for move in serializer.validated_data['updates']:
                try:
                    oldrank = move['oldpos']
                    newrank = move['newpos']
                    queryset = self.get_queryset()
                    updated = queryset.get(rank=oldrank)
                    if newrank < oldrank:
                        queryset.filter(Q(rank__gte=newrank)
                                        & Q(rank__lt=oldrank)).update(
                            rank=F('rank') + 1, moved=True)
                    else:
                        queryset.filter(Q(rank__lte=newrank)
                                        & Q(rank__gt=oldrank)).update(
                            rank=F('rank') - 1, moved=True)
                    updated.rank = newrank
                    updated.moved = True
                    updated.save(update_fields=['rank', 'moved'])
                    queryset.filter(moved=True).update(moved=False)
                except Rule.DoesNotExist:
                    LOGGER.info("unable to move rule with rank=%d to rank=%d",
                        oldrank, newrank)
        return self.get(request, *args, **kwargs)


class RuleDetailAPIView(RuleMixin, RetrieveUpdateDestroyAPIView):
    """
    Retrieves an access rule

    **Tags: rbac

    **Examples

    .. code-block:: http

        GET /api/proxy/rules/app/ HTTP/1.1

    responds

    .. code-block:: json

        {
            "rank": 0,
            "path": "/app/",
            "allow": "authenticated",
            "is_forward": true,
            "engaged": ""
        }
    """
    serializer_class = UpdateRuleSerializer

    def put(self, request, *args, **kwargs):
        """
        Updates an access rule

        **Tags: rbac

        **Examples

        .. code-block:: http

            PUT /api/proxy/rules/app/ HTTP/1.1

        .. code-block:: json

            {
                "rank": 0,
                "path": "/app/",
                "allow": "authenticated",
                "is_forward": true,
                "engaged": ""
            }

        responds

        .. code-block:: json

            {
                "rank": 0,
                "path": "/app/",
                "allow": "authenticated",
                "is_forward": true,
                "engaged": ""
            }
        """
        #pylint:disable=useless-super-delegation
        return super(RuleDetailAPIView, self).put(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        """
        Deletes an access rule

        **Tags: rbac

        **Examples

        .. code-block:: http

            DELETE /api/proxy/rules/app/ HTTP/1.1
        """
        #pylint:disable=useless-super-delegation
        return super(RuleDetailAPIView, self).delete(request, *args, **kwargs)


class UserEngagementAPIView(ListAPIView):
    """
    Retrieves engagement metrics

    **Tags: rbac

    **Examples

    .. code-block:: http

        GET /api/proxy/engagement/users/ HTTP/1.1

    responds

    .. code-block:: json

        {
            "count": 2,
            "next": null,
            "previous": null,
            "results": [
              {
                "username": "alice",
                "engagements": ["app", "profile"]
              },
              {
                "username": "kenneth",
                "engagements": ["app", "billing"]
              }
            ]
        }
    """
    serializer_class = UserEngagementSerializer
    user_model = get_user_model()

    def get_queryset(self):
        return self.user_model.objects.order_by(
            '-last_login').prefetch_related('engagements')


class EngagementAPIView(AppMixin, GenericAPIView):

    serializer_class = EngagementsSerializer
    user_model = get_user_model()

    def get(self, request, *args, **kwargs):
        """
        Retrieves users engagement

        **Tags: rbac

        **Examples

        .. code-block:: http

            GET /api/proxy/engagement/ HTTP/1.1

        responds

        .. code-block:: json

            {
                "active_users": 10,
                "authentication": "enabled",
                "engagements": []
            }
        """
        #pylint:disable=unused-argument
        # https://docs.djangoproject.com/en/2.2/topics/db/aggregation/
        # #interaction-with-default-ordering-or-order-by
        engs = Engagement.objects.values('slug').annotate(
            count=Count('slug')).order_by('slug')
        nb_users = self.user_model.objects.count()
        engagement_stats = []
        for eng in engs:
            engagement_stats += [{
                'slug': eng['slug'],
                'count': eng['count'] * 100 / nb_users
            }]
        # Compute number active users for yesterday
        # XXX there should already be a function to compute that date range.
        yest_dt = datetime_or_now() - relativedelta(days=1)
        yest_start = datetime.datetime(year=yest_dt.year, month=yest_dt.month,
            day=yest_dt.day)
        yest_end = yest_start.replace(hour=23, minute=59, second=59,
            # https://stackoverflow.com/a/34593058/1491475
            microsecond=999999)
        timezone = self.request.GET.get('timezone')
        tz_ob = parse_tz(timezone)
        if not tz_ob:
            tz_ob = utc
        yest_start = tz_ob.localize(yest_start)
        yest_end = tz_ob.localize(yest_end)
        users = self.user_model.objects.filter(
            last_login__gt=yest_start, last_login__lt=yest_end).count()

        return Response(self.get_serializer({
            'authentication': self.app.authentication,
            'engagements': engagement_stats,
            'active_users': users}).data)
