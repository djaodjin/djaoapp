# Copyright (c) 2020 DjaoDjin inc.
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

from boto.exception import S3ResponseError
from django.http import Http404
from django.utils._os import safe_join
from rest_framework.generics import get_object_or_404

from . import settings
from .compat import six, urlsplit
from .models import MediaTag, PageElement
from .extras import AccountMixinBase


LOGGER = logging.getLogger(__name__)


class AccountMixin(AccountMixinBase, settings.EXTRA_MIXIN):
    pass


class TrailMixin(object):
    """
    Generate a trail of PageElement based on a path.
    """

    @staticmethod
    def get_full_element_path(path):
        if not path:
            return []
        parts = path.split('/')
        if not parts[0]:
            parts.pop(0)
        results = []
        if parts:
            element = get_object_or_404(
                PageElement.objects.all(), slug=parts[-1])
            candidates = element.get_parent_paths(hints=parts[:-1])
            if not candidates:
                raise Http404("%s could not be found." % path)
            # XXX Implementation Note: if we have multiple candidates,
            # it means the hints were not enough to select a single path.
            # This is still OK to pick the first candidate as the breadcrumbs
            # should take a user back to the top-level page.
            if len(candidates) > 1:
                LOGGER.info("get_full_element_path has multiple candidates"\
                    " for '%s': %s", path, candidates)
            results = candidates[0]
        return results


class PageElementMixin(AccountMixin):

    lookup_field = 'slug'
    lookup_url_kwarg = 'slug'

    def get_queryset(self):
        return PageElement.objects.filter(account=self.account)

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())

        lookup_value = None
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        if lookup_url_kwarg in self.kwargs:
            lookup_value = self.kwargs[lookup_url_kwarg]
        else:
            parts = self.kwargs.get('path').split('/')
            for part in reversed(parts):
                if part:
                    lookup_value = part
                    break

        filter_kwargs = {self.lookup_field: lookup_value}
        obj = get_object_or_404(queryset, **filter_kwargs)

        # May raise a permission denied
        self.check_object_permissions(self.request, obj)

        return obj


class UploadedImageMixin(object):

    def build_filter_list(self, validated_data):
        items = validated_data.get('items')
        filter_list = []
        if items:
            for item in items:
                location = item['location']
                parts = urlsplit(location)
                if parts.netloc == self.request.get_host():
                    location = parts.path
                filter_list += [location]
        return filter_list

    def list_media(self, storage, filter_list, prefix='.'):
        """
        Return a list of media from default storage
        """
        results = []
        total_count = 0
        if prefix.startswith('/'):
            prefix = prefix[1:]
        try:
            dirs, files = storage.listdir(prefix)
            for media in files:
                if prefix and prefix != '.':
                    media = prefix + '/' + media
                if not media.endswith('/') and media != "":
                    total_count += 1
                    location = storage.url(media)
                    try:
                        updated_at = storage.get_modified_time(media)
                    except AttributeError: # Django<2.0
                        updated_at = storage.modified_time(media)
                    normalized_location = location.split('?')[0]
                    if (filter_list is None
                        or normalized_location in filter_list):
                        tags = ",".join(list(MediaTag.objects.filter(
                            location=normalized_location).values_list(
                            'tag', flat=True)))
                        results += [
                            {'location': location,
                            'tags': tags,
                            'updated_at': updated_at
                            }]
            for asset_dir in dirs:
                dir_results, dir_total_count = self.list_media(
                    storage, filter_list, prefix=prefix + '/' + asset_dir)
                results += dir_results
                total_count += dir_total_count
        except OSError:
            if storage.exists('.'):
                LOGGER.exception(
                    "Unable to list objects in %s.", storage.__class__.__name__)
        except S3ResponseError:
            LOGGER.exception(
                "Unable to list objects in 's3://%s/%s/%s'.",
                storage.bucket_name, storage.location, prefix)

        # sort results by updated_at to sort by created_at.
        # Media are not updated, so updated_at = created_at
        return results, total_count


class ThemePackageMixin(AccountMixin):

    theme_url_kwarg = 'theme'

    @property
    def theme(self):
        if not hasattr(self, '_theme'):
            self._theme = self.kwargs.get(self.theme_url_kwarg)
            if not self._theme:
                self._theme = settings.APP_NAME
        return self._theme

    @staticmethod
    def get_templates_dir(theme):
        if isinstance(settings.THEME_DIR_CALLABLE, six.string_types):
            from .compat import import_string
            settings.THEME_DIR_CALLABLE = import_string(
                settings.THEME_DIR_CALLABLE)
        theme_dir = settings.THEME_DIR_CALLABLE(theme)
        return safe_join(theme_dir, 'templates')

    @staticmethod
    def get_statics_dir(theme):
        return safe_join(settings.PUBLIC_ROOT, theme, 'static')
