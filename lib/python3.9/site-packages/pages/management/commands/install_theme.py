# Copyright (c) 2018, Djaodjin Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
# OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
# OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
# ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from django.core.management.base import BaseCommand

from ...themes import install_theme


class Command(BaseCommand):
    """
    Install resources and templates into a multi-tier environment.

    Templates are installed into ``THEMES_DIR/APP_NAME/templates/``.
    Resources include CSS, JS, images and other files which can be accessed
    anonymously over HTTP and are necessary for the functionality of the site.
    They are copied into ``PUBLIC_ROOT/APP_NAME``
    """

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument('--force',
            action='store_true', dest='force', default=False,
            help='overwrite existing directories and files')
        parser.add_argument('--app_name',
            action='store', dest='app_name', default=None,
            help='overrides the destination theme name')
        parser.add_argument('--path_prefix', action='store',
            dest='path_prefix', default=None,
            help='Adds a prefix to all URLs for static assets')
        parser.add_argument('packages', nargs='*',
            help='list of theme packages')

    def handle(self, *args, **options):
        app_name = options['app_name']
        for package_uri in options['packages']:
            install_theme(app_name, package_uri, force=options['force'])
