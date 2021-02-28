"""
    sphinxcontrib.autohttp.flask
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    The sphinx.ext.autodoc-style HTTP API reference builder (from Flask)
    for sphinxcontrib.httpdomain.

    :copyright: Copyright 2011 by Hong Minhee
    :license: BSD, see LICENSE for details.

"""

import re
import itertools
import six
import collections

from docutils.parsers.rst import directives, Directive

from sphinx.util import force_decode
from sphinx.util.docstrings import prepare_docstring
from sphinx.pycode import ModuleAnalyzer

from sphinxcontrib.autohttp.common import http_directive, import_object


def translate_werkzeug_rule(rule):
    from werkzeug.routing import parse_rule
    buf = six.StringIO()
    for conv, arg, var in parse_rule(rule):
        if conv:
            buf.write('(')
            if conv != 'default':
                buf.write(conv)
                buf.write(':')
            buf.write(var)
            buf.write(')')
        else:
            buf.write(var)
    return buf.getvalue()


def get_routes(app, endpoint=None, order=None):
    endpoints = []
    for rule in app.url_map.iter_rules(endpoint):
        url_with_endpoint = (
            six.text_type(next(app.url_map.iter_rules(rule.endpoint))),
            rule.endpoint
        )
        if url_with_endpoint not in endpoints:
            endpoints.append(url_with_endpoint)
    if order == 'path':
        endpoints.sort()
    endpoints = [e for _, e in endpoints]
    for endpoint in endpoints:
        methodrules = {}
        for rule in app.url_map.iter_rules(endpoint):
            methods = cleanup_methods(rule.methods)
            path = translate_werkzeug_rule(rule.rule)
            for method in methods:
                if method in methodrules:
                    methodrules[method].append(path)
                else:
                    methodrules[method] = [path]
        for method, paths in methodrules.items():
            yield method, paths, endpoint


def get_blueprint(app, view_func):
    for name, func in app.view_functions.items():
        if view_func is func:
            return name.split('.')[0]


def cleanup_methods(methods):
    autoadded_methods = frozenset(['OPTIONS', 'HEAD'])
    if methods <= autoadded_methods:
        return methods
    return methods.difference(autoadded_methods)


def quickref_directive(method, path, content, blueprint=None, auto=False):
    rcomp = re.compile("^\s*.. :quickref:\s*(?P<quick>.*)$")
    method = method.lower().strip()
    if isinstance(content, six.string_types):
        content = content.splitlines()
    description = ""
    name = ""
    ref = path.replace("<", "(").replace(">", ")") \
              .replace("/", "-").replace(":", "-")
    for line in content:
        qref = rcomp.match(line)
        if qref:
            quickref = qref.group("quick")
            parts = quickref.split(";", 1)
            if len(parts) > 1:
                name = parts[0]
                description = parts[1]
            else:
                description = quickref
            break

    if auto:
        if not description and content:
            description = content[0]
        if not name and blueprint:
            name = blueprint

    row = {}
    row['name'] = name
    row['operation'] = '      - `%s %s <#%s-%s>`_' % (
        method.upper(), path, method.lower(), ref)
    row['description'] = description

    return row


class AutoflaskBase(Directive):
    has_content = True
    required_arguments = 1
    option_spec = {'endpoints': directives.unchanged,
                   'blueprints': directives.unchanged,
                   'modules': directives.unchanged,
                   'order': directives.unchanged,
                   'groupby': directives.unchanged,
                   'undoc-endpoints': directives.unchanged,
                   'undoc-blueprints': directives.unchanged,
                   'undoc-modules': directives.unchanged,
                   'undoc-static': directives.unchanged,
                   'include-empty-docstring': directives.unchanged,
                   'autoquickref': directives.flag}

    @property
    def endpoints(self):
        endpoints = self.options.get('endpoints', None)
        if not endpoints:
            return None
        return re.split(r'\s*,\s*', endpoints)

    @property
    def undoc_endpoints(self):
        undoc_endpoints = self.options.get('undoc-endpoints', None)
        if not undoc_endpoints:
            return frozenset()
        return frozenset(re.split(r'\s*,\s*', undoc_endpoints))

    @property
    def blueprints(self):
        blueprints = self.options.get('blueprints', None)
        if not blueprints:
            return None
        return frozenset(re.split(r'\s*,\s*', blueprints))

    @property
    def undoc_blueprints(self):
        undoc_blueprints = self.options.get('undoc-blueprints', None)
        if not undoc_blueprints:
            return frozenset()
        return frozenset(re.split(r'\s*,\s*', undoc_blueprints))

    @property
    def modules(self):
        modules = self.options.get('modules', None)
        if not modules:
            return frozenset()
        return frozenset(re.split(r'\s*,\s*', modules))

    @property
    def undoc_modules(self):
        undoc_modules = self.options.get('undoc-modules', None)
        if not undoc_modules:
            return frozenset()
        return frozenset(re.split(r'\s*,\s*', undoc_modules))

    @property
    def order(self):
        order = self.options.get('order', None)
        if order not in (None, 'path'):
            raise ValueError('Invalid value for :order:')
        return order

    @property
    def groupby(self):
        groupby = self.options.get('groupby', None)
        if not groupby:
            return frozenset()
        return frozenset(re.split(r'\s*,\s*', groupby))

    def inspect_routes(self, app):
        """Inspects the views of Flask.

        :param app: The Flask application.
        :returns: 4-tuple like ``(method, paths, view_func, view_doc)``
        """
        if self.endpoints:
            routes = itertools.chain(*[get_routes(app, endpoint, self.order)
                                       for endpoint in self.endpoints])
        else:
            routes = get_routes(app, order=self.order)

        for method, paths, endpoint in routes:
            try:
                blueprint, _, endpoint_internal = endpoint.rpartition('.')
                if self.blueprints and blueprint not in self.blueprints:
                    continue
                if blueprint in self.undoc_blueprints:
                    continue
            except ValueError:
                pass  # endpoint is not within a blueprint

            if endpoint in self.undoc_endpoints:
                continue

            try:
                static_url_path = app.static_url_path  # Flask 0.7 or higher
            except AttributeError:
                static_url_path = app.static_path      # Flask 0.6 or under
            if ('undoc-static' in self.options and endpoint == 'static' and
                    static_url_path + '/(path:filename)' in paths):
                continue
            view = app.view_functions[endpoint]

            if self.modules and view.__module__ not in self.modules:
                continue

            if self.undoc_modules and view.__module__ in self.modules:
                continue

            view_class = getattr(view, 'view_class', None)
            if view_class is None:
                view_func = view
            else:
                view_func = getattr(view_class, method.lower(), None)

            view_doc = view.__doc__ or ''
            if view_func and view_func.__doc__:
                view_doc = view_func.__doc__

            if not isinstance(view_doc, six.text_type):
                analyzer = ModuleAnalyzer.for_module(view.__module__)
                view_doc = force_decode(view_doc, analyzer.encoding)

            if not view_doc and 'include-empty-docstring' not in self.options:
                continue

            yield (method, paths, view_func, view_doc)

    def groupby_view(self, routes):
        view_to_paths = collections.OrderedDict()
        for method, paths, view_func, view_doc in routes:
            view_to_paths.setdefault(
                (method, view_func, view_doc), []).extend(paths)
        for (method, view_func, view_doc), paths in view_to_paths.items():
            yield (method, paths, view_func, view_doc)

    def make_rst(self, qref=False):
        app = import_object(self.arguments[0])
        routes = self.inspect_routes(app)
        if 'view' in self.groupby:
            routes = self.groupby_view(routes)
        for method, paths, view_func, view_doc in routes:
            docstring = prepare_docstring(view_doc)
            if qref:
                auto = self.options.get("autoquickref", False) is None
                blueprint = get_blueprint(app, view_func)
                for path in paths:
                    row = quickref_directive(method, path, docstring,
                                             blueprint, auto=auto)
                    yield row
            else:
                for line in http_directive(method, paths, docstring):
                    yield line
