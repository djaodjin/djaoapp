"""
    sphinxcontrib.autohttp.tornado
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    The sphinx.ext.autodoc-style HTTP API reference builder (from Tornado)
    for sphinxcontrib.httpdomain.

    :copyright: Copyright 2013 by Rodrigo Machado
    :license: BSD, see LICENSE for details.

"""

import inspect
import re
import six

from docutils import nodes
from docutils.parsers.rst import directives, Directive
from docutils.statemachine import ViewList

from sphinx.util import force_decode
from sphinx.util.nodes import nested_parse_with_titles
from sphinx.util.docstrings import prepare_docstring
from sphinx.pycode import ModuleAnalyzer

from sphinxcontrib import httpdomain
from sphinxcontrib.autohttp.common import http_directive, import_object


def translate_tornado_rule(app, rule):
    buf = six.StringIO()
    for name, filter, conf in app.router.parse_rule(rule):
        if filter:
            buf.write('(')
            buf.write(name)
            if filter != app.router.default_filter or conf:
                buf.write(':')
                buf.write(filter)
            if conf:
                buf.write(':')
                buf.write(conf)
            buf.write(')')
        else:
            buf.write(name)
    return buf.getvalue()


def _locate_regex(spec):
    if hasattr(spec, 'regex'):
        return spec.regex
    elif hasattr(spec, 'matcher'):
        return spec.matcher.regex
    else:
        raise RuntimeError('Could not determine route rules.')


def _locate_target(spec):
    if hasattr(spec, 'target'):
        return spec.target
    elif hasattr(spec, 'handler_class'):
        return spec.handler_class
    raise RuntimeError('get_routes cannot find target for {}'.format(spec))


def _locate_handlers(app):
    if hasattr(app, 'handlers'):  # tornado < 4.5
        return app.handlers[0][1]
    elif hasattr(app, 'wildcard_router'):  # tornado > 4.5
        return app.wildcard_router.rules
    else:  # unexpected changes
        raise RuntimeError('get_routes cannot find routes')


def get_routes(app):
    for spec in _locate_handlers(app):
        handler = _locate_target(spec)
        doc_methods = list(handler.SUPPORTED_METHODS)
        if 'HEAD' in doc_methods:
            doc_methods.remove('HEAD')
        if 'OPTIONS' in doc_methods:
            doc_methods.remove('OPTIONS')

        for method in doc_methods:
            maybe_method = getattr(handler, method.lower(), None)
            if (inspect.isfunction(maybe_method) or
                    inspect.ismethod(maybe_method)):
                regex = _locate_regex(spec)
                yield method.lower(), regex.pattern, handler


def normalize_path(path):
    if path.endswith('$'):
        path = path[:-1]
    return path


class AutoTornadoDirective(Directive):

    has_content = True
    required_arguments = 1
    option_spec = {'endpoints': directives.unchanged,
                   'undoc-endpoints': directives.unchanged,
                   'include-empty-docstring': directives.unchanged}

    @property
    def endpoints(self):
        endpoints = self.options.get('endpoints', None)
        if not endpoints:
            return None
        return frozenset(re.split(r'\s*,\s*', endpoints))

    @property
    def undoc_endpoints(self):
        undoc_endpoints = self.options.get('undoc-endpoints', None)
        if not undoc_endpoints:
            return frozenset()
        return frozenset(re.split(r'\s*,\s*', undoc_endpoints))

    def make_rst(self):
        app = import_object(self.arguments[0])
        for method, path, handler in get_routes(app):
            class_name = handler.__name__
            method_name = getattr(handler, method).__name__
            endpoint = '.'.join((class_name, method_name))

            if self.endpoints and endpoint not in self.endpoints:
                continue
            if endpoint in self.undoc_endpoints:
                continue

            docstring = getattr(handler, method).__doc__ or ''
            #if not isinstance(docstring, unicode):
            #    analyzer = ModuleAnalyzer.for_module(view.__module__)
            #    docstring = force_decode(docstring, analyzer.encoding)
            if not docstring and 'include-empty-docstring' not in self.options:
                continue
            docstring = prepare_docstring(docstring)
            for line in http_directive(method, normalize_path(path), docstring):
                yield line

    def run(self):
        node = nodes.section()
        node.document = self.state.document
        result = ViewList()
        for line in self.make_rst():
            result.append(line, '<autotornado>')
        nested_parse_with_titles(self.state, result, node)
        return node.children


def setup(app):
    app.setup_extension('sphinxcontrib.httpdomain')
    app.add_directive('autotornado', AutoTornadoDirective)
