# Copyright (c) 2025, DjaoDjin inc.
# see LICENSE

import logging
from importlib import import_module

from django.conf import settings
from django.core.management.base import BaseCommand

LOGGER = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Decode sessions in the database"

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument('session_keys', metavar='session_keys', nargs='+',
            help="key for the session")


    def handle(self, *args, **options):
        engine = import_module(settings.SESSION_ENGINE)
        for session_key in options['session_keys']:
            session = engine.SessionStore(session_key=session_key)
            decoded_data = session.load()
            self.stdout.write('%s, %s' % (session_key, decoded_data))
