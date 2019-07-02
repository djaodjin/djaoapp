# Copyright (c) 2019, DjaoDjin inc.
# see LICENSE

import json, logging, re

from django.conf import settings
from django.core.management.base import BaseCommand

from ...views.docs import (OPENAPI_INFO, APIDocGenerator,
    format_examples, split_descr_and_examples)


LOGGER = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Load the database with random transactions (testing purposes)."

    def add_arguments(self, parser):
        parser.add_argument('--database',
            action='store', dest='database', default=None,
            help='use the specified database')
        parser.add_argument('--provider',
            action='store', dest='provider', default=settings.APP_NAME,
            help='create sample subscribers on this provider')

    def handle(self, *args, **options):
        formatted_examples = []
        api_base_url = getattr(settings, 'API_BASE_URL', '/api')
        generator = APIDocGenerator(info=OPENAPI_INFO, url=api_base_url)
        schema = generator.get_schema(request=None, public=True)
        for path, path_details in schema.paths.items():
            for func, func_details in path_details.items():
                try:
                    func_tags, summary, description, examples = \
                        split_descr_and_examples(func_details,
                            api_base_url=api_base_url)
                    formatted_examples += format_examples(examples)
                except AttributeError:
                    pass
        self.stdout.write(json.dumps(formatted_examples, indent=2))
