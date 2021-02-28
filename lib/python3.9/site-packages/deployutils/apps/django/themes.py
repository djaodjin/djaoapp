# Copyright (c) 2020, Djaodjin Inc.
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

import logging, os, re, shutil, subprocess, zipfile

from django.conf import settings as django_settings
from django.template.base import (Parser, NodeList, TemplateSyntaxError)
from django.template.backends.django import DjangoTemplates
from django.template.context import Context
from django.utils.encoding import force_text
from django_assets.templatetags.assets import assets
from jinja2.lexer import Lexer
from webassets import Bundle

from . import settings
from .compat import (DebugLexer, TokenType, do_static, get_html_engine,
    six, urlparse, urlunparse)
from ...copy import shell_command


LOGGER = logging.getLogger(__name__)

STATE_BLOCK_BEGIN = 1
STATE_ASSETS_BEGIN = 2
STATE_ASSETS_END = 3
STATE_BLOCK_CONTENT = 4

class URLRewriteWrapper(object):

    def __init__(self, file_obj, path_prefix=None):
        self.wrapped = file_obj
        self.path_prefix = path_prefix

    def write(self, text):
        if self.path_prefix:
            text = text.replace(
                '="/static', '="/%s/static' % self.path_prefix)
        return self.wrapped.write(text)


class Template(object):

    def __init__(self, engine):
        self.engine = engine


class AssetsParser(Parser):

    def __init__(self, tokens, dest_stream,
                 libraries=None, builtins=None, origin=None):
        #pylint:disable=too-many-arguments
        super(AssetsParser, self).__init__(tokens,
            libraries=libraries, builtins=builtins, origin=origin)
        self.dest_stream = dest_stream
        self.context = Context()
        engine, _, _ = get_html_engine()
        self.context.template = Template(engine)

    def parse_through(self, parse_until=None):
        if parse_until is None:
            parse_until = []
        nodelist = NodeList()
        while self.tokens:
            token = self.next_token()
            if six.PY2:
                contents = token.contents.encode('utf8')
            else:
                contents = token.contents
            if token.token_type == TokenType.TEXT:
                self.dest_stream.write(contents)
            elif token.token_type == TokenType.VAR:
                self.dest_stream.write("{{%s}}" % contents)
            elif token.token_type == TokenType.BLOCK:
                try:
                    command = token.contents.split()[0]
                except IndexError:
                    self.empty_block_tag(token)
                if command in parse_until:
                    # put token back on token list so calling
                    # code knows why it terminated
                    self.prepend_token(token)
                    return nodelist
                if command == 'assets':
                    try:
                        # XXX This should work but for some reason debug does
                        # not get propagated.
                        # Lost in webassets.bundle.resolve_contents
                        token.contents += ' debug=False'
                        assets_string = str(
                            assets(self, token).render(self.context))
                        self.dest_stream.write(assets_string)
                    except TemplateSyntaxError as err:
                        if hasattr(self, 'error'):
                            raise self.error(token, err)
                        # Django < 1.8
                        if not self.compile_function_error(token, err):
                            raise
                elif command == 'static':
                    self.dest_stream.write(
                        do_static(self, token).render(self.context))
                else:
                    self.dest_stream.write("{%% %s %%}" % contents)
            elif token.token_type == TokenType.COMMENT:
                pass


def _render_assets(tokens, env):
    #pylint:disable=too-many-locals
    # Construct a bundle with the given options
    output = None
    filters = None
    depends = None
    bundle_kwargs = {
        'output': output,
        'filters': filters,
        'debug': False,  # because of `Bundle.iterbuild`, this is useless.
        'depends': depends,
    }

    # Resolve bundle names.
    files = []
    state = None
    buffered_tokens = []
    for token in tokens:
        if state is None:
            if token[1] == 'block_begin':
                state = STATE_BLOCK_BEGIN
        elif state == STATE_BLOCK_BEGIN:
            if token[1] == 'name':
                # nothing to be done?
                pass
            elif token[1] == 'string':
                files = [token[2][1:-1]] # removes '"'.
            if token[1] == 'block_end':
                state = STATE_BLOCK_CONTENT
        elif state == STATE_BLOCK_CONTENT:
            if token[1] == 'block_begin':
                state = None
            else:
                buffered_tokens += [token]

    content = ''.join([token[2] for token in buffered_tokens]).strip()

    urls = []
    bundle_names = []
    for fname in files:
        try:
            bundle = env[fname]
            debug = bundle.config.get('debug')
            bundle.config.update({'debug': False})
            with bundle.bind(env):
                urls += bundle.urls()
            bundle.config.update({'debug': debug})
        except KeyError:
            bundle_names.append(fname)

    if bundle_names:
        bundle = Bundle(*bundle_names, **bundle_kwargs)
        # Retrieve urls (this may or may not cause a build)
        with bundle.bind(env):
            urls += bundle.urls()

    # For each url, execute the content of this template tag (represented
    # by the macro ```caller`` given to use by Jinja2).
    result = content
    for url in urls:
        look = re.match(r'(.*)({{\s*ASSET_URL.*}})(.*)', content)
        if look:
            parts = urlparse(url)
            url = urlunparse((parts.scheme, parts.netloc, parts.path,
                None, None, None))
            result = look.group(1) + url + look.group(3)
        else:
            result = content
    return result


def get_template_search_path(app_name=None):
    template_dirs = []
    if app_name:
        candidate_dir = os.path.join(
            settings.MULTITIER_THEMES_DIR, app_name, 'templates')
        if os.path.isdir(candidate_dir):
            template_dirs += [candidate_dir]
    # Django 1.8+
    for loader in getattr(django_settings, 'TEMPLATES', []):
        for dir_path in loader['DIRS']:
            if dir_path not in template_dirs:
                template_dirs += [dir_path]
    # Previous Django versions
    for field_name in ['TEMPLATE_DIRS', 'TEMPLATES_DIRS']:
        template_dirs += list(getattr(django_settings, field_name, []))
    return template_dirs


def init_build_and_install_dirs(app_name, build_dir=None, install_dir=None):
    if not build_dir:
        build_dir = os.path.join(os.getcwd(), 'build')
    if not install_dir:
        install_dir = os.getcwd()
    build_dir = os.path.join(
        os.path.normpath(os.path.abspath(build_dir)), app_name)
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir)
    os.makedirs(build_dir)
    install_dir = os.path.normpath(os.path.abspath(install_dir))
    if not os.path.isdir(install_dir):
        os.makedirs(install_dir)
    return build_dir, install_dir


def package_assets(app_name, build_dir):#pylint:disable=unused-argument
    resources_dest = os.path.join(build_dir, 'public')

    # Copy local resources (not under source control) to resources_dest.
    excludes = ['--exclude', '*~', '--exclude', '.DS_Store',
        '--exclude', '.webassets-cache']
    app_static_root = django_settings.STATIC_ROOT
    assert app_static_root is not None and app_static_root
    # When app_static_root ends with the static_url, we will want
    # to insert the app_name prefix.
    static_root_parts = app_static_root.split(os.sep)
    root_parts_idx = len(static_root_parts)
    root_idx = len(app_static_root)
    found = False
    orig_static_url = django_settings.STATIC_URL
    orig_static_url_parts = orig_static_url.split('/')
    if not orig_static_url_parts[0]:
        orig_static_url_parts = orig_static_url_parts[1:]
    if orig_static_url_parts[0] == app_name:
        orig_static_url_parts = orig_static_url_parts[1:]
    for url_part in reversed(orig_static_url_parts):
        found = True # With ``break`` later on to default to False
                     # when zero iteration.
        if url_part:
            root_parts_idx = root_parts_idx - 1
            root_idx = root_idx - len(static_root_parts[root_parts_idx]) - 1
            if url_part != static_root_parts[root_parts_idx]:
                found = False
                break
    if found:
        app_static_root = os.path.join(
            app_static_root[:root_idx], django_settings.STATIC_URL[1:-1])
        # static_url is required per-Django to start and ends with a '/'
        # (i.e. '/static/').
        # If we have a trailing '/', rsync will copy the content
        # of the directory instead of the directory itself.
    cmdline = (['/usr/bin/rsync']
        + excludes + ['-az', '--safe-links', '--rsync-path', '/usr/bin/rsync']
        + [app_static_root, resources_dest])
    LOGGER.info(' '.join(cmdline))
    shell_command(cmdline)


def package_theme(app_name, build_dir,
                  excludes=None, includes=None, path_prefix=None,
                  template_dirs=None):
    """
    Package resources and templates for a multi-tier environment
    into a zip file.

    Templates are pre-compiled into ``*build_dir*/*app_name*/templates``.
    Compilation means {% assets '*path*' %} and {% static '*path*' %} tags
    are replaced by their compiled expression.
    """
    #pylint:disable=too-many-locals,too-many-arguments
    templates_dest = os.path.join(build_dir, 'templates')
    # override STATIC_URL to prefix APP_NAME.
    orig_static_url = django_settings.STATIC_URL
    if (app_name != settings.APP_NAME
        and not django_settings.STATIC_URL.startswith('/' + app_name)):
        django_settings.STATIC_URL = '/' + app_name + orig_static_url
    if not os.path.exists(templates_dest):
        os.makedirs(templates_dest)
    if template_dirs is None:
        template_dirs = get_template_search_path(app_name)
    for template_dir in template_dirs:
        # The first of template_dirs usually contains the most specialized
        # templates (ie. the ones we truely want to install).
        if (templates_dest
            and not os.path.samefile(template_dir, templates_dest)):
            install_templates(template_dir, templates_dest,
                excludes=excludes, includes=includes, path_prefix=path_prefix)


def fill_package(app_name, build_dir=None, install_dir=None):
    """
    Creates the theme package (.zip) from templates and optionally
    assets installed in the ``build_dir``.
    """
    zip_path = os.path.join(install_dir, '%s.zip' % app_name)
    with zipfile.ZipFile(zip_path, 'w') as zip_file:
        fill_package_zip(zip_file, os.path.dirname(build_dir), prefix=app_name)
    return zip_path


def fill_package_zip(zip_file, srcroot, prefix=''):
    for pathname in os.listdir(os.path.join(srcroot, prefix)):
        pathname = os.path.join(prefix, pathname)
        full_path = os.path.join(srcroot, pathname)
        if os.path.isfile(full_path):
            zip_file.write(full_path, pathname)
        if os.path.isdir(full_path):
            fill_package_zip(zip_file, srcroot, prefix=pathname)


def install_templates(srcroot, destroot, prefix='', excludes=None,
                      includes=None, path_prefix=None):
    #pylint:disable=too-many-arguments,too-many-statements
    """
    Expand link to compiled assets all templates in *srcroot*
    and its subdirectories.
    """
    #pylint: disable=too-many-locals
    if excludes is None:
        excludes = []
    if includes is None:
        includes = []
    if not os.path.exists(os.path.join(prefix, destroot)):
        os.makedirs(os.path.join(prefix, destroot))
    for pathname in os.listdir(os.path.join(srcroot, prefix)):
        pathname = os.path.join(prefix, pathname)
        excluded = False
        for pat in excludes:
            if re.match(pat, pathname):
                excluded = True
                break
        if excluded:
            for pat in includes:
                if re.match(pat, pathname):
                    excluded = False
                    break
        if excluded:
            LOGGER.debug("skip %s", pathname)
            continue
        source_name = os.path.join(srcroot, pathname)
        dest_name = os.path.join(destroot, pathname)
        if os.path.isfile(source_name) and not os.path.exists(dest_name):
            # We don't want to overwrite specific theme files by generic ones.
            with open(source_name) as source:
                template_string = source.read()
            try:
                template_string = force_text(template_string)
                lexer = DebugLexer(template_string)
                tokens = lexer.tokenize()
                if not os.path.isdir(os.path.dirname(dest_name)):
                    os.makedirs(os.path.dirname(dest_name))
                engine, libraries, builtins = get_html_engine()
                if isinstance(engine, DjangoTemplates):
                    with open(dest_name, 'w') as dest:
                        parser = AssetsParser(tokens,
                            URLRewriteWrapper(dest, path_prefix),
                            libraries=libraries,
                            builtins=builtins,
                            origin=None)
                        parser.parse_through()
                else:
                    template_name = None
                    tokens = Lexer(engine.env).tokeniter(template_string,
                        template_name, filename=source_name)
                    buffered_tokens = []
                    state = None
                    with open(dest_name, 'w') as dest:
                        for token in tokens:
                            if state is None:
                                if token[1] == 'block_begin':
                                    state = STATE_BLOCK_BEGIN
                            elif state == STATE_BLOCK_BEGIN:
                                if token[1] == 'name':
                                    if token[2] == 'assets':
                                        state = STATE_ASSETS_BEGIN
                                    else:
                                        buffered_tokens += [token]
                                        state = None
                            elif state == STATE_ASSETS_BEGIN:
                                if (token[1] == 'name'
                                    and token[2] == 'endassets'):
                                    state = STATE_ASSETS_END
                            elif state == STATE_ASSETS_END:
                                if token[1] == 'block_end':
                                    buffered_tokens += [token]
                                    state = None
                            if state is None:
                                if buffered_tokens:
                                    for tok in buffered_tokens:
                                        if (tok[1] == 'name' and
                                            tok[2] == 'assets'):
                                            dest.write(_render_assets(
                                                buffered_tokens,
                                                engine.env.assets_environment))
                                            buffered_tokens = []
                                            break
                                    if buffered_tokens:
                                        dest.write("%s" % ''.join([token[2]
                                            for token in buffered_tokens]))
                                    buffered_tokens = []
                                elif six.PY2:
                                    dest.write("%s" % token[2].encode('utf-8'))
                                else:
                                    dest.write("%s" % str(token[2]))
                            else:
                                buffered_tokens += [token]
                        if buffered_tokens:
                            dest.write("%s" % ''.join([
                                token[2] for token in buffered_tokens]))
                            buffered_tokens = []
                        dest.write("\n")

                cmdline = ['diff', '-u', source_name, dest_name]
                cmd = subprocess.Popen(cmdline, stdout=subprocess.PIPE)
                lines = cmd.stdout.readlines()
                cmd.wait()
                # Non-zero error codes are ok here. That's how diff
                # indicates the files are different.
                if lines:
                    verb = 'compile'
                else:
                    verb = 'install'
                dest_multitier_name = dest_name.replace(destroot,
                        '*MULTITIER_TEMPLATES_ROOT*')
                LOGGER.debug("%s %s to %s", verb,
                    source_name.replace(
                        django_settings.BASE_DIR, '*APP_ROOT*'),
                    dest_multitier_name)
            except UnicodeDecodeError:
                LOGGER.warning("%s: Templates can only be constructed "
                    "from unicode or UTF-8 strings.", source_name)
        elif os.path.isdir(source_name):
            install_templates(srcroot, destroot, prefix=pathname,
                excludes=excludes, includes=includes, path_prefix=path_prefix)
