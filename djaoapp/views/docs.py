# Copyright (c) 2019, DjaoDjin inc.
# see LICENSE

"""
Default start page for a djaodjin-hosted product.
"""

import json, logging, os, re, warnings
from collections import OrderedDict, defaultdict

from django.conf import settings
from django.http import HttpRequest
from django.http.response import Http404
from django.utils import six
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from django.views.generic import TemplateView
from docutils import core
from docutils import frontend
from docutils.writers.html5_polyglot import Writer
from rest_framework import exceptions, serializers
from rest_framework.compat import (URLPattern, URLResolver,
    get_original_route, uritemplate)
from rest_framework.fields import empty
from rest_framework.schemas.generators import EndpointEnumerator

try:
    from rest_framework.schemas.openapi import (
        AutoSchema as BaseAutoSchema, SchemaGenerator)
except ImportError: # drf < 3.10
    from rest_framework.schemas import (
        AutoSchema as BaseAutoSchema, SchemaGenerator)


LOGGER = logging.getLogger(__name__)


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


def format_examples(examples):
    """
    Returns an example is a structured format easily useable
    by mechanical tests.
    """
    # in_requestBody
    # in_respoonse
    IN_URL_STATE = 0
    IN_REQUESTBODY_STATE = 1
    IN_REQUESTBODY_EXAMPLE_STATE = 2
    IN_RESPONSE_STATE = 3
    IN_RESPONSE_EXAMPLE_STATE = 4

    formatted_examples = []
    state = IN_URL_STATE
    func = None
    path = None
    request_body = ""
    resp = ""
    for line in examples.splitlines():
        line = line.strip()
        look = re.match(r'(GET|POST|PUT|PATCH|DELETE)\s+(\S+)\s+HTTP', line)
        if look:
            func = look.group(1)
            path = look.group(2)
            request_body = ""
            resp = ""
            state = IN_REQUESTBODY_STATE
            continue
        look = re.match('responds', line)
        if look:
            state = IN_RESPONSE_STATE
            continue
        look = re.match('.. code-block::', line)
        if look:
            if state == IN_REQUESTBODY_STATE:
                state = IN_REQUESTBODY_EXAMPLE_STATE
            if state == IN_RESPONSE_STATE:
                state = IN_RESPONSE_EXAMPLE_STATE
            continue
        if state == IN_REQUESTBODY_EXAMPLE_STATE:
            if not request_body or line.strip():
                request_body += line
            else:
                state = IN_REQUESTBODY_STATE
        elif state == IN_RESPONSE_EXAMPLE_STATE:
            if not resp or line.strip():
                resp += line
            else:
                state = IN_RESPONSE_STATE
    formatted_example = {'func': func, 'path': path}
    if request_body:
        try:
            formatted_example.update({
                'requestBody': json.loads(request_body)})
        except json.JSONDecodeError:
            LOGGER.error("error: toJSON(%s)", request_body)
    if resp:
        try:
            formatted_example.update({'resp': json.loads(resp)})
        except json.JSONDecodeError:
            LOGGER.error("error: toJSON(%s)", resp)
    formatted_examples += [formatted_example]
    return formatted_examples


def format_json(obj):
    requestBodyJSON = json.dumps(
        obj, indent=2)
    requestBody = ".. code-block:: json\n\n"
    for line in requestBodyJSON.splitlines():
        requestBody += "    " + line + "\n"
    requestBody += "\n\n"
    return rst_to_html(requestBody)


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
    path, method, _, _ = endpoint
    method_priority = {
        'GET': 0,
        'POST': 1,
        'PUT': 2,
        'PATCH': 3,
        'DELETE': 4
    }.get(method, 5)
    return (path, method_priority)


def split_descr_and_examples(docstring, api_base_url=None):
    """
    Split a docstring written for API documentation into tags,
    a generic description and concrete examples.
    """
    sep = ""
    func_tags = None
    first_line = True
    in_examples = False
    summary = "(XXX no summary)"
    description = ""
    examples = ""
    for line in docstring.splitlines():
        line = transform_links(line.strip())
        look = re.match(r'\*\*Tags(\*\*)?:(.*)', line)
        if look:
            func_tags = set([tag.strip()
                for tag in look.group(2).split(',')])
        elif re.match(r'\*\*Example', line):
            in_examples = True
            sep = ""
        elif in_examples:
            for method in ('GET', 'POST', 'PUT', 'PATCH', 'DELETE'):
                look = re.match(r'.* (%s /api)' % method, line)
                if look:
                    line = line.replace(look.group(1),
                        '%s %s' % (method, api_base_url))
                    break
            examples += sep + line
            sep = "\n"
        elif first_line:
            summary = line
            first_line = False
        else:
            description += sep + line
            sep = "\n"
    return func_tags, summary, description, examples


class APIDocEndpointEnumerator(EndpointEnumerator):

    def get_api_endpoints(self, patterns=None, prefix='', app_name=None,
                          namespace=None, default_decorators=None):
        """
        Return a list of all available API endpoints by inspecting the URL conf.
        Copied from super and edited to look at decorators.
        """
        #pylint:disable=arguments-differ,too-many-arguments,too-many-locals
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
                except Exception: #pylint:disable=broad-except
                    LOGGER.warning('failed to enumerate view', exc_info=True)

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
                LOGGER.warning("unknown pattern type %s", type(pattern))

        api_endpoints = sorted(api_endpoints, key=endpoint_ordering)
        return api_endpoints


class AutoSchema(BaseAutoSchema):

    def get_operation(self, path, method):
        kwargs = {}
        method_obj = getattr(self.view, method.lower())
        docstring = method_obj.__doc__
        if not docstring:
            docstring = self.view.__doc__
        if docstring:
            docstring = docstring.strip()
            api_base_url = getattr(settings, 'API_BASE_URL', '/api')
            func_tags, summary, description, examples = \
                split_descr_and_examples(docstring, api_base_url=api_base_url)
            self.examples = format_examples(examples)
            kwargs['summary'] = summary
            kwargs['description'] = description
            kwargs['tags'] = list(func_tags) if func_tags else []
            kwargs['examples'] = self.examples
        operation = super(AutoSchema, self).get_operation(path, method)
        operation.update(kwargs)
        return operation

    def _validate_examples(self, path, method, examples,
                           serializer_class=None, example_key='resp'):
        view = self.view
        if not serializer_class:
            view.request = HttpRequest()
            view.request.method = method
            serializer_class = view.get_serializer_class()
        many = (method == 'GET' and hasattr(view, 'list'))
        if many:
            class APISerializer(serializers.Serializer):
                count = serializers.IntegerField(
                    help_text=_("Total number of items in the dataset"))
                previous = serializers.CharField(allow_null=True,
                    help_text=_("URL to previous page of results"))
                next = serializers.CharField(allow_null=True,
                    help_text=_("URL to next page of results"))
                results = serializer_class(many=hasattr(view, 'list'),
                    help_text=_("items in current page"))
            serializer_class = APISerializer

        serializer = None
        if examples:
            for example in examples:
                if example_key in example:
                    try:
                        serializer = serializer_class(
                            data=example[example_key],
                            context=view.get_serializer_context())
                        serializer.is_valid(raise_exception=True)
                    except (exceptions.ValidationError, Http404) as err:
                        warnings.warn(
                            '{}: {} {} invalid example for {}: {}, {}'.format(
                                view.__class__.__name__, method, path,
                                example_key, example, err))
                else:
                    warnings.warn(
                        '{}: {} {} has no {} ({})'.format(
                            view.__class__.__name__, method, path,
                            example_key, example))
        else:
            warnings.warn('{}: {} {} has no {} examples'.format(
                view.__class__.__name__, method, path, example_key))
            serializer = serializer_class(context=view.get_serializer_context())
        return serializer

    def _get_request_body(self, path, method):
        view = self.view

        if method not in ('PUT', 'PATCH', 'POST'):
            return {}

        serializer_class = None
        view_method = getattr(self.view, method.lower(), None)
        if view_method and hasattr(view_method, '_swagger_auto_schema'):
            data = view_method._swagger_auto_schema
            serializer_class = data.get('request_body', None)

        if not serializer_class and not hasattr(view, 'get_serializer_class'):
            return {}

        serializer = None
        try:
            if method.lower() != 'patch':
                # XXX We disable showing patch as they are so close
                # to put requests.
                serializer = self._validate_examples(path, method,
                    self.examples if hasattr(self, 'examples') else [],
                    serializer_class=serializer_class,
                    example_key='requestBody')
        except exceptions.APIException:
            serializer = None
            warnings.warn('{}: serializer_class() raised an exception during '
                          'schema generation. Serializer fields will not be '
                          'generated for {} {}.'
                          .format(view.__class__.__name__, method, path))

        if not isinstance(serializer, serializers.Serializer):
            return {}

        content = self._map_serializer(serializer)
        # No required fields for PATCH
        if method == 'PATCH':
            del content['required']
        # No read_only fields for request.
        for name, schema in content['properties'].copy().items():
            if 'readOnly' in schema:
                del content['properties'][name]

        return {
            'content': {
                ct: {'schema': content}
                for ct in self.content_types
            }
        }

    def _get_responses(self, path, method):
        # TODO: Handle multiple codes.
        content = {}
        view = self.view
        serializer = None

        if method in ('DELETE',):
            return {'204': {}}

        serializer_class = None
        view_method = getattr(self.view, method.lower(), None)
        if view_method and hasattr(view_method, '_swagger_auto_schema'):
            data = view_method._swagger_auto_schema
            for resp_code, resp in six.iteritems(data.get('responses', {})):
                serializer_class = resp.schema
                break # XXX only handles first schema response.

        if serializer_class or hasattr(view, 'get_serializer_class'):
            try:
                serializer = self._validate_examples(path, method,
                    self.examples if hasattr(self, 'examples') else [],
                    serializer_class=serializer_class)
            except exceptions.APIException:
                serializer = None
                warnings.warn('{}: serializer_class() raised an exception'
                    ' during '
                    'schema generation. Serializer fields will not be '
                    'generated for {} {}.'.format(
                        view.__class__.__name__, method, path))

            if isinstance(serializer, serializers.Serializer):
                content = self._map_serializer(serializer)
                # No write_only fields for response.
                for name, schema in content['properties'].copy().items():
                    if 'writeOnly' in schema:
                        del content['properties'][name]
                        content['required'] = [
                            f for f in content['required'] if f != name]

        return {
            '200': {
                'content': {
                    ct: {'schema': content}
                    for ct in self.content_types
                }
            }
        }


class APIDocGenerator(SchemaGenerator):

    endpoint_enumerator_class = APIDocEndpointEnumerator

    def get_endpoints(self, request):
        """Iterate over all the registered endpoints in the API and return
        a fake view with the right parameters.

        :param rest_framework.request.Request request: request to bind
        to the endpoint views
        :return: {path: (view_class, list[(http_method, view_instance)])
        :rtype: dict
        """
        enumerator = self.endpoint_enumerator_class(
            self._gen.patterns, self._gen.urlconf, request=request)
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


class APIDocView(TemplateView):

    template_name = 'docs/api.html'

    def get_context_data(self, **kwargs):
        #pylint:disable=too-many-locals,too-many-nested-blocks
        context = super(APIDocView, self).get_context_data(**kwargs)
        api_end_points = []
        api_base_url = getattr(settings, 'API_BASE_URL',
            self.request.build_absolute_uri(location='/api'))
        generator = APIDocGenerator()
        schema = generator.get_schema(request=None, public=True)
        tags = set([])
        count = 0
        paths = schema.get('paths', [])
        api_paths = OrderedDict()
        for path in sorted(paths):
            api_paths[path] = paths[path]
        for path, path_details in api_paths.items():
            for func, func_details in path_details.items():
                if func.lower() == 'patch':
                    # We merge PUT and PATCH together.
                    continue
                try:
                    examples = ""
                    if 'examples' in func_details:
                        examples = func_details['examples']
                        for example in examples:
                            if 'requestBody' in example:
                                example['requestBody'] = format_json(
                                    example['requestBody'])
                            if 'resp' in example:
                                example['resp'] = format_json(
                                    example['resp'])
                    func_details.update({
                        'func': func,
                        'path': '/api%s' % path,
                        'description': rst_to_html(func_details['description']),
                        'examples': examples
                    })
                    if 'tags' in func_details and func_details['tags']:
                        # /api retrieves version number and is not part
                        # of any groups.
                        func_details.update({
                            'tags': ''.join(func_details['tags'])})
                        api_end_points += [func_details]
                except AttributeError:
                    raise
#                    pass
        expanded_tags = OrderedDict({
            'auth': "Auth & credentials",
            'billing': "Billing",
            'metrics': "Metrics",
            'profile': "Profile",
            'rbac': "Roles & rules",
            'subscriptions': "Subscriptions",
            'themes': "Themes",
        })
        for tag in sorted(tags):
            if not tag in expanded_tags:
                expanded_tags.update({tag: ""})
        context.update({
            'definitions': {}, # XXX No schema.definitions in restframework,
            'api_base_url': api_base_url,
            'api_end_points': sorted(
                api_end_points, key=lambda val: val['tags']),
            'tags': expanded_tags})
        return context
