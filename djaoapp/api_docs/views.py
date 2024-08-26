# Copyright (c) 2024, DjaoDjin inc.
# see LICENSE

"""
Default start page for a djaodjin-hosted product.
"""
#pylint:disable=too-many-lines

import json, logging, warnings
from collections import OrderedDict

from django.conf import settings
from django.views.generic import TemplateView
from rest_framework.request import Request as HttpRequest

from .schemas import (APIDocGenerator, NotificationDocGenerator,
    format_json, rst_to_html, get_notification_schema)

LOGGER = logging.getLogger(__name__)


class APIDocView(TemplateView):

    template_name = 'api_docs/index.html'
    generator = APIDocGenerator()

    def get_context_data(self, **kwargs):
        #pylint:disable=too-many-locals,too-many-nested-blocks
        context = super(APIDocView, self).get_context_data(**kwargs)
        request = HttpRequest(self.request)
        api_end_points = []
        api_base_url = getattr(settings, 'API_BASE_URL',
            request.build_absolute_uri(location='/').strip('/'))
        schema = self.generator.get_schema(request=request, public=True)
        tags = set([])
        paths = schema.get('paths', [])
        api_paths = OrderedDict()
        for path in sorted(paths):
            api_paths[path] = paths[path]
        for path, path_details in api_paths.items():
            for func, func_details in path_details.items():
                if func.lower() == 'patch':
                    # We merge PUT and PATCH together.
                    continue
                try:
                    examples = ""
                    if 'examples' in func_details:
                        examples = func_details['examples']
                        for example in examples:
                            if 'requestBody' in example:
                                example['requestBody'] = json.dumps(
                                    example['requestBody'])
                            if 'resp' in example:
                                example['resp'] = format_json(
                                    example['resp'])
                    description = func_details.get('description', None)
                    if description is None:
                        warnings.warn("%s %s: description is None" % (
                            func.upper(), path))
                    func_details.update({
                        'func': func,
                        'path': '%s' % path,
                        'description': rst_to_html(description),
                        'examples': examples
                    })
                    if 'tags' in func_details and func_details['tags']:
                        if ('content' not in func_details['tags'] and
                            'editors' not in func_details['tags']):
                            tags |= set(func_details['tags'])
                            api_end_points += [func_details]
                except AttributeError:
#                    raise
                    pass
        expanded_tags = OrderedDict({
            'auth': "Auth & credentials",
            'billing': "Billing",
            'metrics': "Metrics",
            'profile': "Profile",
            'rbac': "Roles & rules",
            'subscriptions': "Subscriptions",
            'themes': "Themes",
        })
        for tag in sorted(tags):
            if not tag in expanded_tags:
                expanded_tags.update({tag: ""})

        if hasattr(self.generator, 'registry'):
            context.update({'definitions': self.generator.registry})
        else:
            # XXX No schema.definitions in restframework,
            context.update({'definitions': {}})

        context.update({
            'api_end_points': sorted(
                api_end_points, key=lambda val: val['path']),
            'api_end_points_by_summary': sorted(
                api_end_points, key=lambda val: val.get('summary', "")),
            'tags': expanded_tags,
#            'api_base_url': api_base_url,
            'api_base_url': "{{api_base_url}}",
         'api_jwt_user': "<a href=\"#auth_create\">JWT auth token</a>",
         'api_jwt_subscriber': "<a href=\"#auth_create\">JWT auth token</a>",
         'api_jwt_provider': "<a href=\"#auth_create\">JWT auth token</a>",
         'api_jwt_broker': "<a href=\"#auth_create\">JWT auth token</a>",
        })
        return context


class NotificationDocView(APIDocView):
    """
    Documentation for notifications triggered by the application
    """
    template_name = 'api_docs/notifications.html'
    generator = NotificationDocGenerator()
