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

import logging
from copy import deepcopy

from django.db import transaction
from django.db.models import Max
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.mixins import DestroyModelMixin
from rest_framework.response import Response

from ..mixins import TrailMixin
from ..models import RelationShip
from ..serializers import EdgeCreateSerializer, RelationShipSerializer


LOGGER = logging.getLogger(__name__)


class EdgesUpdateAPIView(TrailMixin, generics.CreateAPIView):

    serializer_class = EdgeCreateSerializer

    def rank_or_max(self, root, rank=None):
        if rank is None:
            rank = self.get_queryset().filter(
                orig_element=root).aggregate(Max('rank')).get(
                'rank__max', None)
            rank = 0 if rank is None else rank + 1
        return rank

    @staticmethod
    def valid_against_loop(sources, targets):
        if len(sources) <= len(targets):
            is_prefix = True
            for source, target in zip(sources, targets[:len(sources)]):
                if source != target:
                    is_prefix = False
                    break
            if is_prefix:
                raise ValidationError({'detail': "'%s' cannot be attached"\
                    " under '%s' as it is a leading prefix. That would create"\
                    " a loop." % (
                    " > ".join([source.title for source in sources]),
                    " > ".join([target.title for target in targets]))})


    def perform_create(self, serializer):
        targets = self.get_full_element_path(self.kwargs.get('path', None))
        sources = self.get_full_element_path(serializer.validated_data.get(
            'source'))
        self.valid_against_loop(sources, targets)
        self.perform_change(sources, targets,
            rank=serializer.validated_data.get('rank', None))


class PageElementAliasAPIView(EdgesUpdateAPIView):
    """
    Aliases the content of an editable node

    **Examples

    .. code-block:: http

        POST /api/content/editables/alias/content-root/ HTTP/1.1

    .. code-block:: json

        {
          "source": "getting-started"
        }

    responds

    .. code-block:: json

        {}
    """
    queryset = RelationShip.objects.all()

    def perform_change(self, sources, targets, rank=None):
        root = targets[-1]
        node = sources[-1]
        LOGGER.debug("alias node %s under %s with rank=%s", node, root, rank)
        with transaction.atomic():
            RelationShip.objects.create(
                orig_element=root, dest_element=node,
                rank=self.rank_or_max(rank))
        return node


class PageElementMirrorAPIView(EdgesUpdateAPIView):
    """
    Mirrors the content of an editable node

    Mirrors the content of a PageElement and attach the mirror
    under another node.

    **Examples

    .. code-block:: http

        POST /api/content/editables/mirror/content-root/ HTTP/1.1

    .. code-block:: json

        {
          "source": "getting-started"
        }

    responds

    .. code-block:: json

        {}
    """
    queryset = RelationShip.objects.all()

    @staticmethod
    def mirror_leaf(leaf, prefix="", new_prefix=""):
        #pylint:disable=unused-argument
        return leaf

    def mirror_recursive(self, root, prefix="", new_prefix=""):
        edges = RelationShip.objects.filter(
            orig_element=root).select_related('dest_element')
        if not edges:
            return self.mirror_leaf(root, prefix=prefix, new_prefix=new_prefix)
        new_root = deepcopy(root)
        new_root.pk = None
        new_root.slug = None
        new_root.save()
        prefix = prefix + "/" + root.slug
        new_prefix = new_prefix + "/" + new_root.slug
        for edge in edges:
            new_edge = deepcopy(edge)
            new_edge.pk = None
            new_edge.orig_element = new_root
            new_edge.dest_element = self.mirror_recursive(
                edge.dest_element, prefix=prefix, new_prefix=new_prefix)
            new_edge.save()
        return new_root

    def perform_change(self, sources, targets, rank=None):
        root = targets[-1]
        node = sources[-1]
        LOGGER.debug("mirror node %s under %s with rank=%s", node, root, rank)
        with transaction.atomic():
            new_node = self.mirror_recursive(node,
                prefix="/" + "/".join([elm.slug for elm in sources[:-1]]),
                new_prefix="/" + "/".join([elm.slug for elm in targets]))
            RelationShip.objects.create(
                orig_element=root, dest_element=new_node,
                rank=self.rank_or_max(root, rank))
        return new_node


class PageElementMoveAPIView(EdgesUpdateAPIView):
    """
    Moves an editable node

    Moves a PageElement from one attachement to another.

    **Examples

    .. code-block:: http

        POST /api/content/editables/attach/content-root/ HTTP/1.1

    .. code-block:: json

        {
          "source": "getting-started"
        }

    responds

    .. code-block:: json

        {}
    """
    queryset = RelationShip.objects.all()

    def perform_change(self, sources, targets, rank=None):
        if len(sources) < 2 or len(targets) < 1:
            LOGGER.error("There will be a problem calling "\
                " perform_change(sources=%s, targets=%s, rank=%s)"\
                " - data=%s", sources, targets, rank, self.request.data,
                extra={'request': self.request})
        old_root = sources[-2]
        root = targets[-1]
        LOGGER.debug("update node %s to be under %s with rank=%s",
            sources[-1], root, rank)
        with transaction.atomic():
            edge = RelationShip.objects.get(
                orig_element=old_root, dest_element=sources[-1])
            if rank is None:
                rank = self.rank_or_max(root, rank)
            else:
                RelationShip.objects.insert_available_rank(root, pos=rank,
                    node=sources[-1] if root == old_root else None)
            if root != old_root:
                edge.orig_element = root
            edge.rank = rank
            edge.save()
        return sources[-1]


class RelationShipListAPIView(DestroyModelMixin, generics.ListCreateAPIView):
    """
    Lists edges of an editable node


    **Examples

    .. code-block:: http

        GET /api/content/editables/relationship/ HTTP/1.1

    responds

    .. code-block:: json

        {
          "count": 1,
          "next": null,
          "previous": null,
          "results": [{
            "orig_elements": ["readme"],
            "dest_elements": []
          }]
        }
    """
    model = RelationShip
    serializer_class = RelationShipSerializer
    queryset = RelationShip.objects.all()

    def delete(self, request, *args, **kwargs):#pylint: disable=unused-argument
        """
        Deletes edges of an editable node

        **Examples

        .. code-block:: http

            DELETE /api/content/editables/relationship/ HTTP/1.1
       """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid()
        elements = self.queryset.filter(
            orig_element__slug__in=serializer.validated_data['orig_elements'],
            dest_element__slug__in=serializer.validated_data['dest_elements'])
        elements.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def post(self, request, *args, **kwargs):
        """
        Creates edges of an editable node


        **Examples

        .. code-block:: http

            POST /api/content/editables/relationship/ HTTP/1.1

        .. code-block:: json

             {
             }

        responds

        .. code-block:: json

             {
             }
        """
        #pylint: disable=unused-argument,useless-super-delegation
        return super(RelationShipListAPIView, self).post(
            request, *args, **kwargs)
