# Copyright (c) 2020, Djaodjin Inc.
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

from __future__ import absolute_import

import datetime, logging, os, subprocess, sys

from optparse import make_option
from django.conf import settings as django_settings
from django.core.management.base import BaseCommand

from .....filesys import list_local
from ... import settings

LOGGER = logging.getLogger(__name__)


class ResourceCommand(BaseCommand):
    """Commands intended to interact with the resources server directly."""

    def __init__(self):
        BaseCommand.__init__(self)
        self.webapp = os.path.basename(
            os.path.dirname(os.path.abspath(sys.argv[0])))
        self.deployed_path = os.path.join(
            settings.DEPLOYED_WEBAPP_ROOT, self.webapp)

    def add_arguments(self, parser):
        super(ResourceCommand, self).add_arguments(parser)
        parser.add_argument('-n', action='store_true', dest='no_execute',
            default=False,
            help='Print but do not execute')

    def handle(self, *args, **options):
        settings.DRY_RUN = options['no_execute']


def build_assets():
    """Call django_assets ./manage.py assets build if the app is present."""
    cwd = os.getcwd()
    try:
        from webassets.script import GenericArgparseImplementation
        from django_assets.env import get_env
        prog = "%s assets" % os.path.basename(sys.argv[0])
        impl = GenericArgparseImplementation(
            env=get_env(), log=LOGGER, no_global_options=True, prog=prog)
        impl.run_with_argv(["build"])
    except ImportError:
        pass
    os.chdir(cwd)
