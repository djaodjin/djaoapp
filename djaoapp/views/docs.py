# Copyright (c) 2018, DjaoDjin inc.
# see LICENSE

"""
Default start page for a djaodjin-hosted product.
"""

import os, re
from collections import OrderedDict, defaultdict

from django.conf import settings
from django.utils.safestring import mark_safe
from django.views.generic import TemplateView
from docutils import core
from docutils import frontend
from docutils.writers.html5_polyglot import Writer
from rest_framework.compat import URLPattern, URLResolver, get_original_route
from rest_framework.schemas.generators import SchemaGenerator
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from drf_yasg.generators import OpenAPISchemaGenerator, EndpointEnumerator


OPENAPI_INFO = openapi.Info(
        title="DjaoApp API",
        default_version='v1',
        description="API to deploy apps on the djaodjin platform",
        terms_of_service="https://djaodjin.com/legal/terms-of-use/",
        contact=openapi.Contact(email=settings.DEFAULT_FROM_EMAIL),
        license=openapi.License(name="BSD License"),
    )

#pylint:disable=invalid-name
schema_view = get_schema_view(OPENAPI_INFO,
#    validators=['flex', 'ssv'],
    public=True,
)


class NoHeaderHTMLWriter(Writer):

    default_stylesheets = []
    default_stylesheet_dirs = ['.', os.path.abspath(os.path.dirname(__file__))]

    default_template = 'template.txt'
    default_template_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), default_template)

    settings_spec = (
        'HTML-Specific Options',
        None,
        (('Specify the template file (UTF-8 encoded).  Default is "%s".'
          % default_template_path,
          ['--template'],
          {'default': default_template_path, 'metavar': '<file>'}),
         ('Comma separated list of stylesheet URLs. '
          'Overrides previous --stylesheet and --stylesheet-path settings.',
          ['--stylesheet'],
          {'metavar': '<URL[,URL,...]>', 'overrides': 'stylesheet_path',
           'validator': frontend.validate_comma_separated_list}),
         ('Comma separated list of stylesheet paths. '
          'Relative paths are expanded if a matching file is found in '
          'the --stylesheet-dirs. With --link-stylesheet, '
          'the path is rewritten relative to the output HTML file. '
          'Default: "%s"' % ','.join(default_stylesheets),
          ['--stylesheet-path'],
          {'metavar': '<file[,file,...]>', 'overrides': 'stylesheet',
           'validator': frontend.validate_comma_separated_list,
           'default': default_stylesheets}),
         ('Embed the stylesheet(s) in the output HTML file.  The stylesheet '
          'files must be accessible during processing. This is the default.',
          ['--embed-stylesheet'],
          {'default': 1, 'action': 'store_true',
           'validator': frontend.validate_boolean}),
         ('Link to the stylesheet(s) in the output HTML file. '
          'Default: embed stylesheets.',
          ['--link-stylesheet'],
          {'dest': 'embed_stylesheet', 'action': 'store_false'}),
         ('Comma-separated list of directories where stylesheets are found. '
          'Used by --stylesheet-path when expanding relative path arguments. '
          'Default: "%s"' % default_stylesheet_dirs,
          ['--stylesheet-dirs'],
          {'metavar': '<dir[,dir,...]>',
           'validator': frontend.validate_comma_separated_list,
           'default': default_stylesheet_dirs}),
         ('Specify the initial header level.  Default is 1 for "<h1>".  '
          'Does not affect document title & subtitle (see --no-doc-title).',
          ['--initial-header-level'],
          {'choices': '1 2 3 4 5 6'.split(), 'default': '1',
           'metavar': '<level>'}),
         ('Format for footnote references: one of "superscript" or '
          '"brackets".  Default is "brackets".',
          ['--footnote-references'],
          {'choices': ['superscript', 'brackets'], 'default': 'brackets',
           'metavar': '<format>',
           'overrides': 'trim_footnote_reference_space'}),
         ('Format for block quote attributions: one of "dash" (em-dash '
          'prefix), "parentheses"/"parens", or "none".  Default is "dash".',
          ['--attribution'],
          {'choices': ['dash', 'parentheses', 'parens', 'none'],
           'default': 'dash', 'metavar': '<format>'}),
         ('Remove extra vertical whitespace between items of "simple" bullet '
          'lists and enumerated lists.  Default: enabled.',
          ['--compact-lists'],
          {'default': True, 'action': 'store_true',
           'validator': frontend.validate_boolean}),
         ('Disable compact simple bullet and enumerated lists.',
          ['--no-compact-lists'],
          {'dest': 'compact_lists', 'action': 'store_false'}),
         ('Remove extra vertical whitespace between items of simple field '
          'lists.  Default: enabled.',
          ['--compact-field-lists'],
          {'default': True, 'action': 'store_true',
           'validator': frontend.validate_boolean}),
         ('Disable compact simple field lists.',
          ['--no-compact-field-lists'],
          {'dest': 'compact_field_lists', 'action': 'store_false'}),
         ('Added to standard table classes. '
          'Defined styles: borderless, booktabs, '
          'align-left, align-center, align-right, colwidths-auto. '
          'Default: ""',
          ['--table-style'],
          {'default': ''}),
         ('Math output format (one of "MathML", "HTML", "MathJax", '
          'or "LaTeX") and option(s). '
          'Default: "HTML math.css"',
          ['--math-output'],
          {'default': 'HTML math.css'}),
         ('Prepend an XML declaration. (Thwarts HTML5 conformance.) '
          'Default: False',
          ['--xml-declaration'],
          {'default': False, 'action': 'store_true',
           'validator': frontend.validate_boolean}),
         ('Omit the XML declaration.',
          ['--no-xml-declaration'],
          {'dest': 'xml_declaration', 'action': 'store_false'}),
         ('Obfuscate email addresses to confuse harvesters while still '
          'keeping email links usable with standards-compliant browsers.',
          ['--cloak-email-addresses'],
          {'action': 'store_true', 'validator': frontend.validate_boolean}),))

def rst_to_html(string):
    result = core.publish_string(string,
        writer=NoHeaderHTMLWriter())
    return mark_safe(result.decode('utf-8'))


def transform_links(line):
    look = True
    while look:
        look = re.search(r'(:doc:`([^`]+)<(\S+)>`)', line)
        if look:
            line = line.replace(look.group(1),
            "`%s <http://djaodjin-saas.readthedocs.io/en/latest/%s.html>`_" % (
                look.group(2), look.group(3)))
            continue
        look = re.search(r'(:ref:`([^`]+)<(\S+)>`)', line)
        if look:
            line = line.replace(look.group(1),
            "`%s <http://djaodjin-saas.readthedocs.io/en/latest/%s.html>`_" % (
                look.group(2), look.group(3)))
    return line


def endpoint_ordering(endpoint):
    path, method, callback, decorators = endpoint
    method_priority = {
        'GET': 0,
        'POST': 1,
        'PUT': 2,
        'PATCH': 3,
        'DELETE': 4
    }.get(method, 5)
    return (path, method_priority)


class APIDocEndpointEnumerator(EndpointEnumerator):

    def get_api_endpoints(self, patterns=None, prefix='', app_name=None,
                          namespace=None, default_decorators=None):
        """
        Return a list of all available API endpoints by inspecting the URL conf.
        Copied from super and edited to look at decorators.
        """
        if patterns is None:
            patterns = self.patterns

        api_endpoints = []

        for pattern in patterns:
            path_regex = prefix + get_original_route(pattern)
            decorators = default_decorators
            if hasattr(pattern, 'decorators'):
                decorators = pattern.decorators
            if isinstance(pattern, URLPattern):
                try:
                    path = self.get_path_from_regex(path_regex)
                    callback = pattern.callback
                    url_name = pattern.name
                    if self.should_include_endpoint(path, callback,
                            app_name or '', namespace or '', url_name):
                        path = self.replace_version(path, callback)
                        for method in self.get_allowed_methods(callback):
                            endpoint = (path, method, callback, decorators)
                            api_endpoints.append(endpoint)
                except Exception:  # pragma: no cover
                    logger.warning('failed to enumerate view', exc_info=True)

            elif isinstance(pattern, URLResolver):
                nested_endpoints = self.get_api_endpoints(
                    patterns=pattern.url_patterns,
                    prefix=path_regex,
                    app_name="%s:%s" % (app_name,
                        pattern.app_name) if app_name else pattern.app_name,
                    namespace="%s:%s" % (namespace,
                        pattern.namespace) if namespace else pattern.namespace,
                    default_decorators=decorators
                )
                api_endpoints.extend(nested_endpoints)
            else:
                logger.warning("unknown pattern type {}".format(type(pattern)))

        api_endpoints = sorted(api_endpoints, key=endpoint_ordering)
        return api_endpoints


class APIDocGenerator(OpenAPISchemaGenerator):

    endpoint_enumerator_class = APIDocEndpointEnumerator

    def get_endpoints(self, request):
        """Iterate over all the registered endpoints in the API and return
        a fake view with the right parameters.

        :param rest_framework.request.Request request: request to bind
        to the endpoint views
        :return: {path: (view_class, list[(http_method, view_instance)])
        :rtype: dict
        """
        enumerator = self.endpoint_enumerator_class(self._gen.patterns, self._gen.urlconf, request=request)
        endpoints = enumerator.get_api_endpoints()
        view_paths = defaultdict(list)
        view_cls = {}
        for path, method, callback, decorators in reversed(endpoints):
            view = self.create_view(callback, method, request)
            path = self._gen.coerce_path(path, method, view)
            view_paths[path].append((method, view, decorators))
            view_cls[path] = callback.cls
        return {path: (view_cls[path], methods)
            for path, methods in view_paths.items()}

    def get_paths(self, endpoints, components, request, public):
        """Generate the Swagger Paths for the API from the given endpoints.

        :param dict endpoints: endpoints as returned by get_endpoints
        :param ReferenceResolver components: resolver/container for Swagger References
        :param Request request: the request made against the schema view; can be None
        :param bool public: if True, all endpoints are included regardless of access through `request`
        :returns: the :class:`.Paths` object and the longest common path prefix, as a 2-tuple
        :rtype: tuple[openapi.Paths,str]
        """
        if not endpoints:
            return openapi.Paths(paths={}), ''

        prefix = self.determine_path_prefix(list(endpoints.keys())) or ''
        assert '{' not in prefix, "base path cannot be templated in swagger 2.0"

        paths = OrderedDict()
        for path, (view_cls, methods) in sorted(endpoints.items()):
            operations = {}
            for method, view, decorators in methods:
                if not public and not self._gen.has_view_permissions(path, method, view):
                    continue

                operation = self.get_operation(view, path, prefix, method, components, request)
                if operation is not None:
                    operations[method.lower()] = operation

            if operations:
                # since the common prefix is used as the API basePath, it must be stripped
                # from individual paths when writing them into the swagger document
                path_suffix = path[len(prefix):]
                if not path_suffix.startswith('/'):
                    path_suffix = '/' + path_suffix
                paths[path_suffix] = self.get_path_item(path, view_cls, operations)

        return openapi.Paths(paths=paths), prefix



class APIDocView(TemplateView):

    template_name = 'docs/api.html'

    def get_context_data(self, **kwargs):
        #pylint:disable=too-many-locals,too-many-nested-blocks
        context = super(APIDocView, self).get_context_data(**kwargs)
        api_end_points = []
        api_base_url = self.request.build_absolute_uri(location='/api')
        generator = APIDocGenerator(info=OPENAPI_INFO, url=api_base_url)
        schema = generator.get_schema(request=None, public=True)
        tags = set([])
        for path, path_details in schema.paths.items():
            for func, func_details in path_details.items():
                if func.lower() == 'patch':
                    # We merge PUT and PATCH together.
                    continue
                try:
                    sep = ""
                    in_examples = False
                    tags |= set(func_details.tags)
                    description = ""
                    examples = ""
                    for line in func_details.description.splitlines():
                        line = transform_links(line)
                        if re.match(r'\*\*Example', line):
                            in_examples = True
                            sep = ""
                        elif in_examples:
                            for method in ('GET', 'POST', 'PUT', 'PATCH'):
                                look = re.match(r'.* (%s /api)' % method, line)
                                if look:
                                    line = line.replace(look.group(1),
                                        '%s %s' % (method, api_base_url))
                                    break
                            examples += sep + line
                            sep = "\n"
                        else:
                            description += sep + line
                            sep = "\n"
                    description = rst_to_html(description)
                    examples = rst_to_html(examples)
                    api_end_points += [{
                        'operationId': func_details.operationId,
                        'func': func,
                        'path': path,
                        'tags': ''.join(func_details.tags),
                        'description': description,
                        'parameters': func_details.parameters,
                        'responses': func_details.responses,
                        'examples': examples
                    }]
                except AttributeError:
                    pass
        context.update({
            'definitions': schema.definitions,
            'api_base_url': generator.url,
            'api_end_points': api_end_points,
            'tags': sorted([tag.capitalize() for tag in tags])})
        return context
