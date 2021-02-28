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

from __future__ import unicode_literals

import json, logging, random
from collections import OrderedDict

from django.db import IntegrityError, models, transaction
from django.db.models import Max
from django.template.defaultfilters import slugify
from django.utils.translation import ugettext_lazy as _
from rest_framework.exceptions import ValidationError

from . import settings
from .compat import python_2_unicode_compatible


LOGGER = logging.getLogger(__name__)

class RelationShipManager(models.Manager):

    def insert_available_rank(self, root, pos=0, node=None):
        # Implementation Note:
        #   Edges are ordered loosily. That is: only when a node is specified
        #   to be at a specific position in the outbound adjency list from
        #   an origin node will ranks be computed. By default all ranks
        #   are zero.
        #   This means we can end-up in the following situations before
        #   inserting a node:
        #      (sort order 0 1 2 3 4 5 6)
        #   1. rank        0 0 0 0 0 0 0
        #   2. rank        6 6 6 6 6 6 6
        #   insertion pos      ^
        #   The resulting ranks must keep the current order yet leave
        #   a hole to insert the new node.
        #   1. new rank    0 0 3 4 5 6 7
        #   2. new rank    0 1 6 6 6 6 6
        sorted_edges = list(self.filter(orig_element=root).order_by(
            'rank', 'pk'))

        if node:
            for index, edge in enumerate(sorted_edges):
                if edge.dest_element_id == node.pk:
                    prev_pos = index
                    break
            if prev_pos < pos:
                pos = pos + 1

        for index, edge in enumerate(sorted_edges[:pos]):
            if edge.rank >= pos:
                edge.rank = index
                edge.save()
        for index, edge in enumerate(sorted_edges[pos:]):
            if edge.rank < (pos + index + 1):
                edge.rank = pos + index + 1
                edge.save()

    def insert_node(self, root, node, pos=0):
        """
        Insert a *node* at a specific position in the list of outbound
        edges from *root*.
        """
        with transaction.atomic():
            self.insert_available_rank(root, pos=pos)
            self.create(orig_element=root, dest_element=node, rank=pos)


@python_2_unicode_compatible
class RelationShip(models.Model):
    """
    Encodes a relation between two ``PageElement``.
    """
    objects = RelationShipManager()

    orig_element = models.ForeignKey(
        "PageElement", on_delete=models.CASCADE, related_name='from_element')
    dest_element = models.ForeignKey(
        "PageElement", on_delete=models.CASCADE, related_name='to_element')
    tag = models.SlugField(null=True)
    rank = models.IntegerField(default=0)

    class Meta:
        unique_together = ('orig_element', 'dest_element')

    def __str__(self):
        return "%s to %s" % (
            self.orig_element.slug, self.dest_element.slug) #pylint: disable=no-member


class PageElementQuerySet(models.QuerySet):


    def build_content_tree(self, prefix="", cut=None):
        return build_content_tree(roots=self, prefix=prefix, cut=cut)


class PageElementManager(models.Manager):

    def get_queryset(self):
        return PageElementQuerySet(self.model, using=self._db)

    def get_roots(self):
        return self.all().extra(where=[
            '(SELECT COUNT(*) FROM pages_relationship'\
            ' WHERE pages_relationship.dest_element_id = pages_pageelement.id)'\
            ' = 0'])

    def get_leafs(self):
        return self.all().extra(where=[
            '(SELECT COUNT(*) FROM pages_relationship'\
            ' WHERE pages_relationship.orig_element_id = pages_pageelement.id)'\
            ' = 0'])


@python_2_unicode_compatible
class PageElement(models.Model):
    """
    Elements of an editable HTML page.
    """
    objects = PageElementManager()

    slug = models.SlugField(unique=True,
        help_text=_("Unique identifier that can be used in URL paths"))
    title = models.CharField(max_length=720, blank=True,
        help_text=_("Title of the page element"))
    text = models.TextField(blank=True,
        help_text=_("Long description of the page element"))
    account = models.ForeignKey(
        settings.ACCOUNT_MODEL, related_name='account_page_element',
        null=True, on_delete=models.SET_NULL)
    relationships = models.ManyToManyField("self",
        related_name='related_to', through='RelationShip', symmetrical=False)
    tag = models.CharField(max_length=255, null=True, blank=True,
        help_text=_("Extra meta data (can be stringify JSON)"))

    def __str__(self):
        return self.slug

    def add_relationship(self, element, tag=None):
        rank = RelationShip.objects.filter(
            orig_element=self).aggregate(Max('rank')).get('rank__max', None)
        if rank is None:
            rank = 0
        return RelationShip.objects.get_or_create(
            orig_element=self, dest_element=element,
            defaults={'tag': tag, 'rank': rank})

    def remove_relationship(self, element):
        RelationShip.objects.filter(
            orig_element=self,
            dest_element=element).delete()
        return True

    def get_parent_paths(self, depth=None, hints=None):
        """
        Returns a list of paths.

        When *depth* is specified each paths will be *depth* long or shorter.
        When *hints* is specified, it is a list of elements in a path. The
        paths returns will contain *hints* along the way.
        """
        #pylint:disable=too-many-nested-blocks
        if depth is not None and depth == 0:
            return [[self]]
        results = []
        parents = PageElement.objects.filter(
            pk__in=RelationShip.objects.filter(
                dest_element=self).values('orig_element_id'))
        if not parents:
            return [[self]]
        if hints:
            for parent in parents:
                if parent.slug == hints[-1]:
                    # we found a way to cut the search space early.
                    parents = [parent]
                    hints = hints[:-1]
                    break
        for parent in parents:
            grandparents = parent.get_parent_paths(
                depth=(depth - 1) if depth is not None else None,
                hints=hints)
            if grandparents:
                for grandparent in grandparents:
                    term_index = 0
                    if hints:
                        for node in grandparent:
                            if node.slug == hints[term_index]:
                                term_index += 1
                                if term_index >= len(hints):
                                    break
                    if not hints or term_index >= len(hints):
                        # we have not hints or we consumed all of them.
                        results += [grandparent + [self]]
        return results

    def get_relationships(self, tag=None):
        if not tag:
            return self.relationships.filter(
                to_element__orig_element=self)
        return self.relationships.filter(
            to_element__tag=tag, to_element__orig_element=self)

    def get_related_to(self, tag):
        return self.related_to.filter(
            from_element__tag=tag,
            from_element__dest_element=self)

    def save(self, force_insert=False, force_update=False,
             using=None, update_fields=None):
        if self.slug: # serializer will set created slug to '' instead of None.
            return super(PageElement, self).save(
                force_insert=force_insert, force_update=force_update,
                using=using, update_fields=update_fields)
        max_length = self._meta.get_field('slug').max_length
        slug_base = slugify(self.title)
        if not slug_base:
            # title might be empty
            "".join([random.choice("abcdef0123456789") for _ in range(7)])
        elif len(slug_base) > max_length:
            slug_base = slug_base[:max_length]
        self.slug = slug_base
        for _ in range(1, 10):
            try:
                with transaction.atomic():
                    return super(PageElement, self).save(
                        force_insert=force_insert, force_update=force_update,
                        using=using, update_fields=update_fields)
            except IntegrityError as err:
                if 'uniq' not in str(err).lower():
                    raise
                suffix = '-%s' % "".join([random.choice("abcdef0123456789")
                    for _ in range(7)])
                if len(slug_base) + len(suffix) > max_length:
                    self.slug = slug_base[:(max_length - len(suffix))] + suffix
                else:
                    self.slug = slug_base + suffix
        raise ValidationError({'detail':
            "Unable to create a unique URL slug from title '%s'" % self.title})


@python_2_unicode_compatible
class MediaTag(models.Model):

    location = models.CharField(max_length=250)
    tag = models.CharField(max_length=50)

    def __str__(self):
        return str(self.tag)


@python_2_unicode_compatible
class LessVariable(models.Model):
    """
    This model stores value of a variable used to generate a css file.
    """
    name = models.CharField(max_length=250)
    value = models.CharField(max_length=250)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    account = models.ForeignKey(settings.ACCOUNT_MODEL,
        null=True, on_delete=models.SET_NULL,
        related_name='account_less_variable')
    cssfile = models.CharField(max_length=50)

    class Meta:
        unique_together = ('account', 'cssfile', 'name')

    def __str__(self):
        return '%s: %s' % (self.name, self.value)


@python_2_unicode_compatible
class ThemePackage(models.Model):
    """
    This model allow to record uploaded template.
    """
    slug = models.SlugField(unique=True)
    account = models.ForeignKey(
        settings.ACCOUNT_MODEL, null=True, on_delete=models.CASCADE,
        related_name='account_template', blank=True)
    name = models.CharField(max_length=150)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=False)

    def __str__(self):
        if self.account:
            return '%s-%s' % (self.account, self.name)
        return self.name


def build_content_tree(roots=None, prefix=None, cut=None):
    """
    Returns a content tree from a list of roots.

    code::

        build_content_tree(roots=[PageElement<boxes-and-enclosures>])
        {
          "/boxes-and-enclosures": [
            { ... data for node ... },
            {
              "boxes-and-enclosures/management": [
              { ... data for node ... },
              {}],
              "boxes-and-enclosures/design": [
              { ... data for node ... },
              {}],
            }]
        }
    """
    #pylint:disable=too-many-locals,too-many-statements
    # Implementation Note: The structure of the content in the database
    # is stored in terms of `PageElement` (node) and `Relationship` (edge).
    # We use a breadth-first search algorithm here such as to minimize
    # the number of queries to the database.
    if roots is None:
        roots = PageElement.objects.get_roots()
        if prefix and prefix != '/':
            LOGGER.warning("[build_content_tree] prefix=%s but no roots"\
                " were defined", prefix)
        else:
            prefix = ''
    else:
        if not prefix:
            LOGGER.warning("[build_content_tree] roots=%s but not prefix"\
                " was defined", roots)
    # insures the `prefix` will match a `PATH_RE` (starts with a '/' and
    # does not end with one).
    if not prefix.startswith("/"):
        prefix = "/" + prefix
    if prefix.endswith("/"):
        prefix = prefix[:-1]

    results = OrderedDict()
    pks_to_leafs = {}
    roots_after_cut = []
    for root in roots:
        if isinstance(root, PageElement):
            slug = root.slug
            orig_element_id = root.pk
            title = root.title
            extra = root.tag
        else:
            slug = root.get('slug', root.get('dest_element__slug'))
            orig_element_id = root.get('dest_element__pk')
            title = root.get('dest_element__title')
            extra = root.get('dest_element__tag')
        leaf_slug = "/" + slug
        if prefix.endswith(leaf_slug):
            # Workaround because we sometimes pass a prefix and sometimes
            # a path `from_root`.
            base = prefix
        else:
            base = prefix + leaf_slug
        try:
            extra = json.loads(extra)
        except (TypeError, ValueError):
            pass
        result_node = {'title': title}
        if extra:
            result_node.update({'extra': extra})
        pks_to_leafs[orig_element_id] = {
            'path': base,
            'node': (result_node, OrderedDict())
        }
        results.update({base: pks_to_leafs[orig_element_id]['node']})
        if cut is None or cut.enter(extra):
            roots_after_cut += [root]

    args = tuple([])
    edges = RelationShip.objects.filter(
        orig_element__in=roots_after_cut).values(
        'orig_element_id', 'dest_element_id', 'rank',
        'dest_element__slug', 'dest_element__title',
        'dest_element__tag', *args).order_by('rank', 'pk')
    while edges:
        next_pks_to_leafs = {}
        for edge in edges:
            orig_element_id = edge.get('orig_element_id')
            dest_element_id = edge.get('dest_element_id')
            slug = edge.get('slug', edge.get('dest_element__slug'))
            base = pks_to_leafs[orig_element_id]['path'] + "/" + slug
            title = edge.get('dest_element__title')
            extra = edge.get('dest_element__tag')
            try:
                extra = json.loads(extra)
            except (TypeError, ValueError):
                pass
            result_node = {'title': title}
            if extra:
                result_node.update({'extra': extra})
            text = edge.get('dest_element__text', None)
            if text:
                result_node.update({'text': text})
            pivot = (result_node, OrderedDict())
            pks_to_leafs[orig_element_id]['node'][1].update({base: pivot})
            if cut is None or cut.enter(extra):
                next_pks_to_leafs[dest_element_id] = {
                    'path': base,
                    'node': pivot
                }
        pks_to_leafs = next_pks_to_leafs
        next_pks_to_leafs = {}
        edges = RelationShip.objects.filter(
            orig_element_id__in=pks_to_leafs.keys()).values(
            'orig_element_id', 'dest_element_id', 'rank',
            'dest_element__slug', 'dest_element__title',
            'dest_element__tag', *args).order_by('rank', 'pk')
    return results


def get_active_theme():
    """
    Returns the active theme from a request.
    """
    if settings.ACTIVE_THEME_CALLABLE:
        from .compat import import_string  # Because AppRegistryNotReady
        theme_slug = import_string(settings.ACTIVE_THEME_CALLABLE)()
        LOGGER.debug("pages: get_active_theme('%s')", theme_slug)
        try:
            return ThemePackage.objects.get(slug=theme_slug)
        except ThemePackage.DoesNotExist:
            pass
    return None
