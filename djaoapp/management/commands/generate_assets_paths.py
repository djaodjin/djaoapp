# Copyright (c) 2019, DjaoDjin inc.
# see LICENSE

import logging, json, os

from django.apps import apps
from django.core.management.base import BaseCommand
from django.contrib.staticfiles.finders import get_finders

LOGGER = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Generate assets paths for webpack to consume"
    file_name = 'webpack_dirs.json'

    def add_arguments(self, parser):
        parser.add_argument('--node_modules', action='store',
        default='node_modules', help='use the specified database')

    def handle(self, *args, **options):
        prefix = options.get('node_modules')
        if prefix and prefix[0] != '/':
            prefix = os.path.join(os.getcwd(), prefix)
        htdocs = os.path.join(os.getcwd(), 'htdocs', 'static')
        dirs = [prefix, htdocs]
        ign = apps.get_app_config('staticfiles').ignore_patterns
        djaodjin_apps = ['djaoapp', 'saas', 'signup', 'rules', 'pages']
        for finder in get_finders():
            for path, storage in finder.list(ign):
                pth = storage.path(path)

                for app in djaodjin_apps:
                    subs = '/%s/static/' % app
                    if subs in pth:
                        static_dir = pth[0:pth.find(subs)+len(subs)][0:-1]
                        if static_dir not in dirs:
                            dirs.append(static_dir)
        with open(self.file_name, 'w') as f:
            f.write(json.dumps(dirs))

        self.stdout.write('dumped static directories to %s' % self.file_name)
