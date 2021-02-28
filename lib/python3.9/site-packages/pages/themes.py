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
from __future__ import unicode_literals

import logging, os, tempfile, shutil, subprocess, sys, zipfile

from django.core.files.storage import FileSystemStorage
from django.core.exceptions import PermissionDenied
from django.template.base import Parser, NodeList
from django.template.backends.jinja2 import get_exception_info
from django.template.context import Context
from django.template.exceptions import TemplateDoesNotExist, TemplateSyntaxError
from django.template.loader import _engine_list, get_template
from django.utils._os import safe_join
from django.utils.encoding import force_text
from django_assets.templatetags.assets import assets
import jinja2
import requests

from . import settings
from .compat import TokenType, do_static, get_html_engine, six, urlparse


LOGGER = logging.getLogger(__name__)


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
                        elif not self.compile_function_error(token, err):
                            raise
                elif command == 'static':
                    self.dest_stream.write(
                        do_static(self, token).render(self.context))
                else:
                    self.dest_stream.write("{%% %s %%}" % contents)
            elif token.token_type == TokenType.COMMENT:
                pass


def check_template(template_source, using=None):
    """
    Loads and returns a template for the given name.

    Raises TemplateDoesNotExist if no such template exists.
    """
    errs = {}
    engines = _engine_list(using)
    # We should find at least one engine that does not raise an error.
    for engine in engines:
        try:
            try:
                return engine.from_string(template_source)
            except jinja2.TemplateSyntaxError as exc:
                new = TemplateSyntaxError(exc.args)
                new.template_debug = get_exception_info(exc)
                six.reraise(TemplateSyntaxError, new, sys.exc_info()[2])
        except TemplateSyntaxError as err:
            errs.update({engine: err})
    if errs:
        raise TemplateSyntaxError(errs)


def get_template_path(template=None, relative_path=None):
    if template is None:
        template = get_template(relative_path)
    try:
        return template.template.filename
    except AttributeError:
        return template.origin.name


def get_theme_dir(theme_name):
    if isinstance(settings.THEME_DIR_CALLABLE, six.string_types):
        from .compat import import_string
        settings.THEME_DIR_CALLABLE = import_string(
            settings.THEME_DIR_CALLABLE)
    theme_dir = settings.THEME_DIR_CALLABLE(theme_name)
    return theme_dir


def install_theme(app_name, package_uri, force=False):
    parts = urlparse(package_uri)
    package_file = None
    try:
        if parts.scheme == 's3':
            from .backends.s3 import get_package_file_from_s3
            package_file = get_package_file_from_s3(package_uri)
        elif parts.scheme in ['http', 'https']:
            basename = os.path.basename(parts.path)
            resp = requests.get(package_uri, stream=True)
            if resp.status_code == 200:
                package_file = tempfile.NamedTemporaryFile()
                shutil.copyfileobj(resp.raw, package_file)
                package_file.seek(0)
            else:
                raise RuntimeError(
                    "requests status code: %d" % resp.status_code)
        else:
            basename = os.path.basename(package_uri)
            package_storage = FileSystemStorage(
                os.path.dirname(package_uri))
            package_file = package_storage.open(basename)
        if not app_name:
            app_name = os.path.splitext(basename)[0]
        LOGGER.info("install %s to %s\n", package_uri, app_name)
        with zipfile.ZipFile(package_file, 'r') as zip_file:
            install_theme_fileobj(app_name, zip_file, force=force)
    finally:
        if hasattr(package_file, 'close'):
            package_file.close()


def install_theme_fileobj(theme_name, zip_file, force=False):
    """
    Extract resources and templates from an opened ``ZipFile``
    and install them at a place they can be picked by the multitier
    logic in ``template_loader.Loader.get_template_sources``.
    """
    #pylint:disable=too-many-statements,too-many-locals
    assert theme_name is not None
    LOGGER.info("install theme %s%s", theme_name, " (force)" if force else "")
    theme_dir = get_theme_dir(theme_name)
    public_dir = safe_join(settings.PUBLIC_ROOT, theme_name)
    templates_dir = safe_join(theme_dir, 'templates')

    if not force and os.path.exists(public_dir):
        LOGGER.warning("install theme '%s' but '%s' already exists.",
            theme_name, public_dir)
        raise PermissionDenied("Theme public assets already exists.")

    if not force and os.path.exists(templates_dir):
        LOGGER.warning("install theme '%s' but '%s' already exists.",
            theme_name, templates_dir)
        raise PermissionDenied("Theme templates already exists.")

    # We rely on the assumption that ``public_dir`` and ``templates_dir``
    # are on the same filesystem. We create a temporary directory on that
    # common filesystem, which guarentees that:
    #   1. If the disk is full, we will find on extract, not when we try
    #      to move the directory in place.
    #   2. If the filesystem is encrypted, we don't inadvertently leak
    #      information by creating "temporary" files.
    tmp_base = safe_join(
        os.path.commonprefix([public_dir, templates_dir]), '.cache')
    if not os.path.exists(tmp_base):
        os.makedirs(tmp_base)
    if not os.path.isdir(os.path.dirname(templates_dir)):
        os.makedirs(os.path.dirname(templates_dir))
    tmp_dir = tempfile.mkdtemp(dir=tmp_base)

    #pylint: disable=too-many-nested-blocks
    try:
        for info in zip_file.infolist():
            if info.file_size == 0:
                # Crude way to detect directories
                continue
            tmp_path = None
            test_parts = os.path.normpath(info.filename).split(os.sep)[1:]
            if test_parts:
                base = test_parts.pop(0)
                if base == 'public':
                    if settings.PUBLIC_WHITELIST is not None:
                        if (os.path.join(*test_parts)
                            in settings.PUBLIC_WHITELIST):
                            tmp_path = safe_join(tmp_dir, base, *test_parts)
                    else:
                        tmp_path = safe_join(tmp_dir, base, *test_parts)
                    if tmp_path:
                        if not os.path.isdir(os.path.dirname(tmp_path)):
                            os.makedirs(os.path.dirname(tmp_path))
                        with open(tmp_path, 'wb') as extracted_file:
                            extracted_file.write(zip_file.read(info.filename))
                elif base == 'templates':
                    relative_path = os.path.join(*test_parts)
                    if relative_path in settings.TEMPLATES_BLACKLIST:
                        continue
                    if settings.TEMPLATES_WHITELIST is not None:
                        if (os.path.join(*test_parts)
                            in settings.TEMPLATES_WHITELIST):
                            tmp_path = safe_join(tmp_dir, base, relative_path)
                    else:
                        tmp_path = safe_join(tmp_dir, base, relative_path)
                    if tmp_path:
                        if not os.path.isdir(os.path.dirname(tmp_path)):
                            os.makedirs(os.path.dirname(tmp_path))
                        template_string = zip_file.read(info.filename)
                        if hasattr(template_string, 'decode'):
                            template_string = template_string.decode('utf-8')
                        template_string = force_text(template_string)
                        try:
                            check_template(template_string)
                            with open(tmp_path, 'w') as extracted_file:
                                extracted_file.write(template_string)
                            try:
                                default_path = get_template_path(
                                    relative_path=relative_path)
                                if (default_path and
                                    not default_path.startswith(theme_dir)):
                                    cmdline = [
                                        'diff', '-u', default_path, tmp_path]
                                    cmd = subprocess.Popen(
                                        cmdline, stdout=subprocess.PIPE)
                                    lines = cmd.stdout.readlines()
                                    cmd.wait()
                                    # Non-zero error codes are ok here.
                                    # That's how diff indicates the files
                                    # are different.
                                    if not lines:
                                        LOGGER.info(
                                            "%s: no differences", relative_path)
                                        os.remove(tmp_path)
                            except TemplateDoesNotExist:
                                # We are installing a template which is not
                                # in the default theme, so no diff is ok.
                                pass
                        except TemplateSyntaxError as err:
                            LOGGER.info("error:%s: %s", relative_path, err)

        # Should be safe to move in-place at this point.
        # Templates are necessary while public resources (css, js)
        # are optional.
        tmp_public = safe_join(tmp_dir, 'public')
        tmp_templates = safe_join(tmp_dir, 'templates')
        mkdirs = []
        renames = []
        for paths in [(tmp_templates, templates_dir),
                     (tmp_public, public_dir)]:
            if os.path.exists(paths[0]):
                if not os.path.exists(os.path.dirname(paths[1])):
                    mkdirs += [os.path.exists(os.path.dirname(paths[1]))]
                renames += [paths]
        for path in mkdirs:
            os.makedirs(path)
        for paths in renames:
            if os.path.exists(paths[1]):
                LOGGER.info("remove previous path %s", paths[1])
                shutil.rmtree(paths[1])
            os.rename(paths[0], paths[1])
    finally:
        # Always delete the temporary directory, exception raised or not.
        shutil.rmtree(tmp_dir)


def remove_theme(theme_name):
    """
    Remove assets and templates directories.
    """
    try:
        FileNotFoundError
    except NameError:
        # py27 `rmtree` will raise an OSError executing `os.listdir(path)`
        # if the path is not present.
        FileNotFoundError = OSError
    theme_dir = get_theme_dir(theme_name)
    public_dir = safe_join(settings.PUBLIC_ROOT, theme_name)
    LOGGER.info("remove theme '%s', that is directories %s and %s.",
                   theme_name, theme_dir, public_dir)
    try:
        shutil.rmtree(theme_dir)
    except FileNotFoundError:
        pass
    try:
        shutil.rmtree(public_dir)
    except FileNotFoundError:
        pass
