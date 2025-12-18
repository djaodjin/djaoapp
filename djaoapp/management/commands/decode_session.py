# Copyright (c) 2025, DjaoDjin inc.
# see LICENSE

import logging
from importlib import import_module

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.utils import DatabaseError
from multitier.thread_locals import clear_cache, set_current_site
from multitier.utils import get_site_model

LOGGER = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Decode sessions in the database"

    site_model = get_site_model()

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument('--db_name', action='store',
            dest='db_name', default=None,
            help='Specifies the database to run against.')
        parser.add_argument('session_keys', metavar='session_keys', nargs='+',
            help="key for the session")


    def handle(self, *args, **options):
        db_name = options.get('db_name')
        if db_name:
            try:
                site = self.site_model.objects.get(db_name=db_name)
                LOGGER.info("decode_session in db '%s'", db_name)
            except self.site_model.DoesNotExist:
                LOGGER.error(
                    "decode_session in db '%s': no associated site", db_name)
                return 1
            except self.site_model.MultipleObjectsReturned:
                LOGGER.error(
                    "decode_session in db '%s': ambiguous multiple sites",
                    db_name)
                return 1
        try:
            clear_cache()
            set_current_site(site, path_prefix='',
                default_scheme='https', default_host=site.domain)
            self.decode_sessions(options['session_keys'])
        except DatabaseError as err:
            LOGGER.error(
                "decode_session in db '%s': %s", db_name, err)
            return 1

        return 0


    def decode_sessions(self, session_keys, db_name=None):
        engine = import_module(settings.SESSION_ENGINE)
        for session_key in session_keys:
            session = engine.SessionStore(session_key=session_key)
            decoded_data = session.load()
            self.stdout.write('%s, %s%s' % (session_key, decoded_data,
                ", %s" % db_name if db_name else ""))
