# Copyright (c) 2023, DjaoDjin inc.
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

from .schemas import (APIDocGenerator, format_json,
    rst_to_html, get_notification_schema)

LOGGER = logging.getLogger(__name__)


class APIDocView(TemplateView):

    template_name = 'docs/api.html'
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
         'api_jwt_user': "<a href=\"#createJWTLogin\">JWT auth token</a>",
         'api_jwt_subscriber': "<a href=\"#createJWTLogin\">JWT auth token</a>",
         'api_jwt_provider': "<a href=\"#createJWTLogin\">JWT auth token</a>",
         'api_jwt_broker': "<a href=\"#createJWTLogin\">JWT auth token</a>",
        })
        return context


class NotificationDocGenerator(object):

    @staticmethod
    def get_schema(request=None, public=True):
        #pylint:disable=unused-argument
        api_base_url = getattr(settings, 'API_BASE_URL',
            request.build_absolute_uri(location='/').strip('/'))
        api_end_points = OrderedDict({
            'user_contact': get_notification_schema('user_contact',
                api_base_url=api_base_url),
            'user_registered': get_notification_schema('user_registered',
                api_base_url=api_base_url),
            'user_activated': get_notification_schema('user_activated',
                api_base_url=api_base_url),
            'user_verification': get_notification_schema('user_verification',
                api_base_url=api_base_url),
            'user_reset_password': get_notification_schema(
                'user_reset_password', api_base_url=api_base_url),
            'user_mfa_code': get_notification_schema('user_mfa_code',
                api_base_url=api_base_url),
            'card_expires_soon': get_notification_schema('card_expires_soon',
                api_base_url=api_base_url),
            'expires_soon': get_notification_schema('expires_soon',
                api_base_url=api_base_url),
            'profile_updated': get_notification_schema(
                'profile_updated', api_base_url=api_base_url),
            'card_updated': get_notification_schema('card_updated',
                api_base_url=api_base_url),
            'weekly_sales_report_created': get_notification_schema(
                'weekly_sales_report_created', api_base_url=api_base_url),
            'charge_updated': get_notification_schema('charge_updated',
                api_base_url=api_base_url),
            'order_executed': get_notification_schema('order_executed',
                api_base_url=api_base_url),
            'renewal_charge_failed': get_notification_schema(
                'renewal_charge_failed', api_base_url=api_base_url),
            'claim_code_generated': get_notification_schema(
                'claim_code_generated', api_base_url=api_base_url),
            'processor_setup_error': get_notification_schema(
                'processor_setup_error', api_base_url=api_base_url),
            'role_grant_created': get_notification_schema(
                'role_grant_created', api_base_url=api_base_url),
            'role_request_created': get_notification_schema(
                'role_request_created', api_base_url=api_base_url),
            'role_grant_accepted': get_notification_schema(
                'role_grant_accepted', api_base_url=api_base_url),
            'subscription_grant_accepted': get_notification_schema(
                'subscription_grant_accepted', api_base_url=api_base_url),
            'subscription_grant_created': get_notification_schema(
                'subscription_grant_created', api_base_url=api_base_url),
            'subscription_request_accepted': get_notification_schema(
                'subscription_request_accepted', api_base_url=api_base_url),
            'subscription_request_created': get_notification_schema(
                'subscription_request_created', api_base_url=api_base_url),
        })
        api_paths = {}
        for api_end_point in api_end_points.values():
            funcs = {}
            funcs.update({api_end_point.get('func'): api_end_point})
            api_paths.update({api_end_point.get('operationId'): funcs})
        schema = {
            'paths': api_paths
        }
        return schema


class NotificationDocView(APIDocView):
    """
    Documentation for notifications triggered by the application
    """
    template_name = 'docs/notifications.html'
    generator = NotificationDocGenerator()
