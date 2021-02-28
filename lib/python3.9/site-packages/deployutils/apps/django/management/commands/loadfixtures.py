# Copyright (c) 2017, Djaodjin Inc.
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
from __future__ import unicode_literals

import os, re, tempfile

from django.core.management.commands.loaddata import Command as BaseCommand


class Command(BaseCommand):

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument('--email', action='store', dest='email',
            default='', help='Replace email fields in fixtures by a derivative'\
            ' of this parameter (e.g. support+idx@example.com)')

    def handle(self, *fixture_labels, **options):
        email = options.get('email')
        if email:
            fixture_tmps = self.replace_email(email, *fixture_labels)
            try:
                super(Command, self).handle(*fixture_tmps, **options)
            finally:
                for fixture in fixture_tmps:
                    os.remove(fixture)
        else:
            super(Command, self).handle(*fixture_labels, **options)

    @staticmethod
    def replace_email(email, *fixture_labels):
        look = re.match(r'(\S+)@(\S+)', email)
        username = look.group(1)
        domain = look.group(2)
        index = 1
        fixture_tmps = []
        for fixture in fixture_labels:
            with open(fixture) as fixture_file:
                tmp_file = tempfile.NamedTemporaryFile(
                    mode='w+t', suffix='.json', delete=False)
                for line in fixture_file.readlines():
                    look = re.match(r'(\s*"email":\s*)"(\S+)"(,)?', line)
                    if look:
                        prefix = look.group(1)
                        suffix = look.group(3)
                        derivative = '%s+%d@%s' % (username, index, domain)
                        index += 1
                        tmp_file.write('%s"%s"%s' % (
                            prefix, derivative, suffix))
                    else:
                        tmp_file.write(line)
                tmp_file.close()
                fixture_tmps += [os.path.join(
                    tempfile.gettempdir(), tmp_file.name)]
        return fixture_tmps
