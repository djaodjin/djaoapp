# Copyright (c) 2019, DjaoDjin inc.
# see LICENSE

import logging, json, os

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand
from django.contrib.staticfiles.finders import get_finders

LOGGER = logging.getLogger(__name__)


class Command(BaseCommand):
	help = "Generate assets paths for webpack to consume"

	def add_arguments(self, parser):
		parser.add_argument('--venv', action='store',
			default='venv', help='path to virtualenvironment')
		parser.add_argument('PATH', nargs=1, type=str)

	def handle(self, *args, **options):
		venv = options.get('venv')
		base = settings.BASE_DIR
		output = options['PATH'][0]
		if venv and venv[0] != '/':
			venv = os.path.join(base, venv)
		node_modules = os.path.join(venv, 'node_modules')
		djaoapp = os.path.join(base, 'djaoapp', 'static')
		htdocs = os.path.join(base, 'htdocs', 'static')
		dirs = {
			'venv': venv,
			'htdocs': htdocs,
			'node_modules': [node_modules],
		}
		ign = apps.get_app_config('staticfiles').ignore_patterns
		djaodjin_apps = ['djaoapp', 'saas', 'signup', 'rules', 'pages']
		djaodjin_mods = [djaoapp]
		for finder in get_finders():
			for path, storage in finder.list(ign):
				pth = storage.path(path)

				for app in djaodjin_apps:
					subs = '/%s/static/' % app
					if subs in pth:
						static_dir = pth[0:pth.find(subs)+len(subs)][0:-1]
						if static_dir not in djaodjin_mods:
							djaodjin_mods.append(static_dir)
		dirs['djaodjin_modules'] = djaodjin_mods + [htdocs, node_modules]
		with open(output, 'w') as f:
			f.write(json.dumps(dirs))

		self.stdout.write('dumped djaodjin-webpack config to %s' % output)
