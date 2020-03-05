# Copyright (c) 2020, DjaoDjin inc.
# see LICENSE

import json, logging
from hashlib import sha256

from django.conf import settings
from django.core.management.base import BaseCommand

from ...views.docs import (APIDocGenerator,
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
        parser.add_argument('--errors', action='store_true', default=False,
            help='toggle errors')

    def handle(self, *args, **options):
        formatted_examples = []
        api_base_url = getattr(settings,
            'API_BASE_URL', 'https://djaodjin.com/api')
        generator = APIDocGenerator()
        schema = generator.get_schema(request=None, public=True)
        descr_hashes = []
        for path, path_details in schema.paths.items():
            for func, func_details in path_details.items():
                try:
                    func_tags, summary, description, examples = \
                        split_descr_and_examples(func_details,
                            api_base_url=api_base_url)
                    func_examples = format_examples(examples)
                    hsh = sha256(func_details.description.encode()).hexdigest()
                    errors = []
                    if func_examples[0]['path']:
                        if ('responds' not in examples and func != 'delete'):
                            errors.append('missing-response')
                    else:
                        func_examples[0]['path'] = path
                        func_examples[0]['func'] = func
                        if not description and not examples:
                            errors.append('undocumented')
                        else:
                            errors.append('parsing')
                    if hsh in descr_hashes:
                        errors.append('duplicate-description')
                    else:
                        descr_hashes.append(hsh)
                    if options['errors']:
                        if errors:
                            func_examples[0]['errors'] = errors
                            formatted_examples += func_examples
                    else:
                        if not errors:
                            formatted_examples += func_examples
                except AttributeError:
                    pass
        self.stdout.write(json.dumps(formatted_examples, indent=2))
