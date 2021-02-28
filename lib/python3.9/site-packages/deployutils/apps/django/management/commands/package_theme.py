# Copyright (c) 2018, Djaodjin Inc.
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

from __future__ import absolute_import
from __future__ import unicode_literals

import sys

from . import ResourceCommand
from ... import settings
from ...themes import (init_build_and_install_dirs, package_assets,
    package_theme, fill_package)


class Command(ResourceCommand):
    """
    Package resources and templates for a multi-tier environment
    into a zip file.

    Templates are pre-compiled into ``*build_dir*/*app_name*/templates``.
    Compilation means {% assets '*path*' %} and {% static '*path*' %} tags
    are replaced by their compiled expression.

    Resources are copied into ``*build_dir*/*app_name*/static``.
    Resources include CSS, JS, images and other files which can be accessed
    anonymously over HTTP and are necessary for the functionality of the site.
    This command considers everything in ``STATIC_ROOT`` to be a resource.

    This command must be run with DEBUG=False and the cached assets must
    have been built before this command is invoked. They won't be rebuilt here.

    Example::

    $ DEBUG=0 python manage.py package_theme

    APP_NAME can be overriden with the ``--app_name`` command line flag.

    Example::

    $ ls
    templates/base.html
    $ python manage.py package_theme --app_name webapp
    $ ls build
    build/webapp/templates/base.html

    It is possible to exclude template files that match a regular expression.
    For more complex filters, it is possible to still include a subset
    of the excluded templates when they also match a secondary regular
    expression.

    Example::

    $ ls
    templates/base.html
    templates/skip/template.html
    templates/skip/deep/template.html
    $ python manage.py package_theme --exclude='skip/*' --include='skip/deep/*'
    $ ls build
    build/app_name/templates/base.html
    build/app_name/templates/skip/deep/template.html
    """
    help = "package templates and resources for a multitier setup."

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument('--app_name', action='store', dest='app_name',
            default=settings.APP_NAME,
            help='overrides the destination site name')
        parser.add_argument('--path_prefix', action='store',
            dest='path_prefix', default=None,
            help='Adds a prefix to all URLs for static assets')
        parser.add_argument('--build_dir',
            action='store', dest='build_dir', default=None,
            help='set the directory root where temporary files are created.')
        parser.add_argument('--install_dir',
            action='store', dest='install_dir', default=None,
            help='set the directory root where output files are created.')
        parser.add_argument('--exclude', action='append', dest='excludes',
            default=[], help='exclude specified templates directories')
        parser.add_argument('--include', action='append', dest='includes',
            default=[], help='include specified templates directories'\
                ' (after excludes have been applied)')

    def handle(self, *args, **options):
        app_name = options['app_name']
        build_dir, install_dir = init_build_and_install_dirs(app_name,
            build_dir=options['build_dir'],
            install_dir=options['install_dir'])
        package_theme(app_name, build_dir,
            excludes=options['excludes'],
            includes=options['includes'],
            path_prefix=options['path_prefix'])
        package_assets(app_name, build_dir=build_dir)
        zip_path = fill_package(app_name,
            build_dir=build_dir,
            install_dir=install_dir)
        sys.stdout.write('package built: %s\n' % zip_path)
