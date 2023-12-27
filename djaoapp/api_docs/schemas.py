# Copyright (c) 2023, DjaoDjin inc.
# see LICENSE
"""
OpenAPI schema generator
"""
import json, logging, os, re, warnings

from django.conf import settings
from django.http import HttpRequest
from django.http.response import Http404
from django.utils.safestring import mark_safe
from docutils import core
from docutils import frontend
from docutils.writers.html5_polyglot import Writer
from rest_framework import exceptions, serializers
from rest_framework.generics import GenericAPIView
from rest_framework.schemas.generators import EndpointEnumerator
from saas.api.serializers import DatetimeValueTuple, NoModelSerializer
from saas.pagination import (BalancePagination, RoleListPagination,
    StatementBalancePagination, TotalPagination, TypeaheadPagination)

try:
    from drf_spectacular.openapi import AutoSchema as BaseAutoSchema
    from drf_spectacular.generators import SchemaGenerator
except ImportError: # We cannot find drf_spectacular.
    try:
        from rest_framework.schemas.openapi import (SchemaGenerator,
            AutoSchema as BaseAutoSchema)
    except ImportError: # drf < 3.10
        from rest_framework.schemas import (SchemaGenerator,
            AutoSchema as BaseAutoSchema)

from ..compat import gettext_lazy as _, URLPattern, URLResolver, six
from ..notifications import signals as notification_signals
from ..notifications.serializers import (ContactUsNotificationSerializer,
    UserNotificationSerializer,
    ExpireProfileNotificationSerializer,
    SubscriptionExpireNotificationSerializer,
    ChangeProfileNotificationSerializer, AggregatedSalesNotificationSerializer,
    ChargeNotificationSerializer,
    RenewalFailedNotificationSerializer, InvoiceNotificationSerializer,
    ClaimNotificationSerializer, ProcessorSetupNotificationSerializer,
    RoleRequestNotificationSerializer, RoleGrantNotificationSerializer,
    SubscriptionAcceptedNotificationSerializer,
    SubscriptionCreatedNotificationSerializer)


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
    #pylint:disable=invalid-name,too-many-statements
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
            if state in (IN_URL_STATE, IN_REQUESTBODY_STATE):
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
    request_body_json = json.dumps(
        obj, indent=2)
    request_body = ".. code-block:: json\n\n"
    for line in request_body_json.splitlines():
        request_body += "    " + line + "\n"
    request_body += "\n\n"
    return rst_to_html(request_body)


def rst_to_html(string):
    result = core.publish_string(string,
        writer=NoHeaderHTMLWriter())
    return mark_safe(result.decode('utf-8'))


def transform_links(line, api_base_url=""):
    look = True
    while look:
        look = re.search(r'(:doc:`([^`]+)<(\S+)>`)', line)
        if look:
            matched = look.group(1)
            text = look.group(2)
            endpoint = look.group(3)
            line = line.replace(matched,
            "`%s <http://djaodjin-saas.readthedocs.io/en/latest/%s.html>`_" % (
                text, endpoint))
            continue
        look = re.search(r'(:ref:`([^`]+)<(\S+)>`)', line)
        if look:
            matched = look.group(1)
            text = look.group(2)
            endpoint = look.group(3)
            # XXX find the id generated by OpenSpec from url name?
            line = line.replace(matched,
            "`%s <%s>`_" % (text, endpoint))
        look = re.search(r'(\{\{(\S+)\}\})', line)
        if look:
            key = look.group(2).strip()
            if key == 'PAGE_SIZE':
                value = '`page_size`'
            else:
                value = str(settings.SAAS.get(key,
                    settings.REST_FRAMEWORK.get(key,
                    api_base_url if key == 'api_base_url' else key)))
            line = line.replace(look.group(1), value)
    return line


def endpoint_ordering(endpoint):
    path = endpoint[APIDocEndpointEnumerator.PATH_IDX]
    method = endpoint[APIDocEndpointEnumerator.METHOD_IDX]
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
        line = transform_links(line.strip(), api_base_url=api_base_url)
        look = re.match(r'\*\*Tags(\*\*)?:(.*)', line)
        if look:
            func_tags = {tag.strip()
                for tag in look.group(2).split(',')}
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

    PATH_IDX = 0
    PATH_REGEX_IDX = 1
    METHOD_IDX = 2
    CALLBACK_IDX = 3

    def _insert_api_endpoint(self, api_endpoints, api_endpoint):
        found = False
        for endpoint in api_endpoints:
            if (endpoint[self.PATH_IDX] == api_endpoint[self.PATH_IDX] and
                endpoint[self.METHOD_IDX] == api_endpoint[self.METHOD_IDX]):
                LOGGER.debug("found duplicate: %s %s (%s vs. %s)",
                    endpoint[self.METHOD_IDX], endpoint[self.PATH_IDX],
                    endpoint[self.CALLBACK_IDX],
                    api_endpoint[self.CALLBACK_IDX])
                assert endpoint[self.CALLBACK_IDX].__name__.startswith(
                    'DjaoApp')
                found = True
                break
        if not found:
            api_endpoints.append(api_endpoint)

    def get_api_endpoints(self, patterns=None, prefix=''):
        """
        Return a list of all available API endpoints by inspecting the URL conf.
        """
        if patterns is None:
            patterns = self.patterns

        api_endpoints = []

        for pattern in patterns:
            path_regex = prefix + str(pattern.pattern)
            if isinstance(pattern, URLPattern):
                path = self.get_path_from_regex(path_regex)
                callback = pattern.callback
                if self.should_include_endpoint(path, callback):
                    for method in self.get_allowed_methods(callback):
                        endpoint = (path, path_regex, method, callback)
                        self._insert_api_endpoint(api_endpoints, endpoint)

            elif isinstance(pattern, URLResolver):
                nested_endpoints = self.get_api_endpoints(
                    patterns=pattern.url_patterns,
                    prefix=path_regex
                )
                for endpoint in nested_endpoints:
                    self._insert_api_endpoint(api_endpoints, endpoint)

        return sorted(api_endpoints, key=endpoint_ordering)


class APIDocGenerator(SchemaGenerator):

    endpoint_inspector_cls = APIDocEndpointEnumerator


class AutoSchema(BaseAutoSchema):

    def get_request_media_types(self):
        return ['application/json']
#XXX        return getattr(self, 'request_media_types',
#            getattr(self, 'content_types', []))

    def get_operation_id_base(self, path, method, action):
        # rest framework implementation will try to deduce the  name
        # from the model, serializer before using the view name. That
        # leads to duplicate `operationId`.
        # Always use the view name
        name = self.view.__class__.__name__
        if name.endswith('APIView'):
            name = name[:-7]
        elif name.endswith('View'):
            name = name[:-4]

        # Due to camel-casing of classes and `action` being lowercase,
        # apply title in order to find if action truly
        # comes at the end of the name
        if name.endswith(action.title()): # ListView, UpdateAPIView, etc.
            name = name[:-len(action)]

        return name


    def get_operation(self, path, path_regex, path_prefix, method, registry):
        self.path = path
        extra_fields = {}
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
            extra_fields['summary'] = summary
            extra_fields['description'] = description
#            if not description:
#                warnings.warn("%s %s: no description could be extracted"
#                    " from '%s'" % (method, path, docstring))
            extra_fields['tags'] = list(func_tags) if func_tags else []
            if not settings.OPENAPI_SPEC_COMPLIANT:
                extra_fields['examples'] = self.examples
        self.view.request = HttpRequest()
        self.view.request.path = path
        self.view.request.method = method
        operation = super(AutoSchema, self).get_operation(
            path, path_regex, path_prefix, method, registry)
        operation.update(extra_fields)
        return operation

    def _guess_serializer_class(self, method, serializer_class, many=False):
        view = self.view
        many = many or (method == 'GET' and hasattr(view, 'list'))
        if many:
            if issubclass(view.pagination_class, BalancePagination):
                class BalancePaginationAPISerializer(NoModelSerializer):
                    start_at = serializers.CharField(
                        help_text=_("Start of the date range for which"\
                        " the balance was computed"))
                    ends_at = serializers.CharField(
                        help_text=_("End of the date range for which"\
                        " the balance was computed"))
                    balance_amount = serializers.IntegerField(
                        help_text=_("Balance of all transactions in cents"\
                        " (i.e. 100ths) of unit"))
                    balance_unit = serializers.CharField(
                        help_text=_("Three-letter ISO 4217 code"\
                        " for currency unit (ex: usd)"))
                    count = serializers.IntegerField(
                        help_text=_("Total number of items in the dataset"))
                    previous = serializers.CharField(
                        required=False, allow_null=True,
                        help_text=_("URL to previous page of results"))
                    next = serializers.CharField(
                        required=False, allow_null=True,
                        help_text=_("URL to next page of results"))
                    results = serializer_class(many=hasattr(view, 'list'),
                        help_text=_("items in current page"))
                serializer_class = BalancePaginationAPISerializer

            elif issubclass(view.pagination_class, RoleListPagination):
                class RoleListPaginationAPISerializer(NoModelSerializer):
                    invited_count = serializers.IntegerField(
                        help_text=_("Number of user invited to have a role"))
                    requested_count = serializers.IntegerField(
                        help_text=_("Number of user requesting a role"))
                    count = serializers.IntegerField(
                        help_text=_("Total number of items in the dataset"))
                    previous = serializers.CharField(
                        required=False, allow_null=True,
                        help_text=_("URL to previous page of results"))
                    next = serializers.CharField(
                        required=False, allow_null=True,
                        help_text=_("URL to next page of results"))
                    results = serializer_class(many=hasattr(view, 'list'),
                        help_text=_("items in current page"))
                serializer_class = RoleListPaginationAPISerializer

            elif issubclass(view.pagination_class, StatementBalancePagination):
                class StatementBalancePaginationAPISerializer(NoModelSerializer):
                    start_at = serializers.CharField(
                        help_text=_("Start of the date range for which"\
                        " the balance was computed"))
                    ends_at = serializers.CharField(
                        help_text=_("End of the date range for which"\
                        " the balance was computed"))
                    balance_amount = serializers.IntegerField(
                        help_text=_("Balance of all transactions in cents"\
                        " (i.e. 100ths) of unit"))
                    balance_unit = serializers.CharField(
                        help_text=_("Three-letter ISO 4217 code"\
                        " for currency unit (ex: usd)"))
                    count = serializers.IntegerField(
                        help_text=_("Total number of items in the dataset"))
                    previous = serializers.CharField(
                        required=False, allow_null=True,
                        help_text=_("URL to previous page of results"))
                    next = serializers.CharField(
                        required=False, allow_null=True,
                        help_text=_("URL to next page of results"))
                    results = serializer_class(many=hasattr(view, 'list'),
                        help_text=_("items in current page"))
                serializer_class = StatementBalancePaginationAPISerializer

            elif issubclass(view.pagination_class, TotalPagination):
                class TotalPaginationAPISerializer(NoModelSerializer):
                    balance_amount = serializers.IntegerField(
                        help_text=_("The sum of all record amounts (in unit)"))
                    balance_unit = serializers.CharField(
                        help_text=_("Three-letter ISO 4217 code"\
                        " for currency unit (ex: usd)"))
                    count = serializers.IntegerField(
                        help_text=_("Total number of items in the dataset"))
                    previous = serializers.CharField(
                        required=False, allow_null=True,
                        help_text=_("URL to previous page of results"))
                    next = serializers.CharField(
                        required=False, allow_null=True,
                        help_text=_("URL to next page of results"))
                    results = serializer_class(many=hasattr(view, 'list'),
                        help_text=_("items in current page"))
                serializer_class = TotalPaginationAPISerializer

            elif issubclass(view.pagination_class, TypeaheadPagination):
                class TypeaheadPaginationAPISerializer(NoModelSerializer):
                    count = serializers.IntegerField(
                        help_text=_("Total number of items in the results"))
                    results = serializer_class(many=hasattr(view, 'list'),
                        help_text=_("items in the queryset"))
                serializer_class = TypeaheadPaginationAPISerializer

            else:
                class APISerializer(NoModelSerializer):
                    count = serializers.IntegerField(
                        help_text=_("Total number of items in the dataset"))
                    previous = serializers.CharField(
                        required=False, allow_null=True,
                        help_text=_("URL to previous page of results"))
                    next = serializers.CharField(
                        required=False, allow_null=True,
                        help_text=_("URL to next page of results"))
                    results = serializer_class(many=hasattr(view, 'list'),
                        help_text=_("items in current page"))
                serializer_class = APISerializer

        return serializer_class

    @staticmethod
    def _validate_against_schema(data, schema):
        errs = []
        for key, value in six.iteritems(data):
            if key not in schema.get('properties', []):
                errs += [exceptions.ValidationError({key: "unexpected field"})]
        if errs:
            raise exceptions.ValidationError(errs)


    def _validate_examples(self, examples, path, method,
                           serializer_class=None, schema=None,
                           example_key='resp'):
        #pylint:disable=too-many-arguments,too-many-locals,too-many-statements

        # prevents circular imports
        from saas.api.billing import CartItemUploadAPIView
        from saas.api.organizations import OrganizationPictureAPIView
        from signup.api.contacts import ContactPictureAPIView
        from signup.api.users import UserPictureAPIView

        view = self.view
        if isinstance(view, (CartItemUploadAPIView, ContactPictureAPIView,
                      OrganizationPictureAPIView, UserPictureAPIView)):
            return
        if examples:
            for example in examples:
                path_parts = path.split('/')
                if not example['path']:
                    warnings.warn('%s example has no path (%s)' % (
                        path, example['path']))
                else:
                    query_idx = example['path'].find('?')
                    if query_idx >= 0:
                        example_path_parts = example['path'][:query_idx].split(
                            '/')
                    else:
                        example_path_parts = example['path'].split('/')
                    if len(example_path_parts) != len(path_parts):
                        warnings.warn('%s has different parts from %s' % (
                            example['path'], path))
                    for path_part, example_path_part in zip(
                            path_parts, example_path_parts):
                        if path_part.startswith('{'):
                            continue
                        if example_path_part != path_part:
                            warnings.warn(
                                '%s does not match pattern %s ("%s"!="%s")' % (
                                example['path'], path,
                                example_path_part, path_part))
                            break
                if example_key in example:
                    if serializer_class is not None:
                        serializer_class = self._guess_serializer_class(
                            method, serializer_class)
                        try:
                            kwargs = {}
                            serializer = serializer_class(
                                data=example[example_key],
                                context=view.get_serializer_context(),
                                **kwargs)
                            serializer.is_valid(raise_exception=True)
                            self._validate_against_schema(
                                example[example_key], schema)

                        except (exceptions.ValidationError, Http404) as err:
                            # is_valid will also run `UniqueValidator` which
                            # is not what we want here, especially
                            # on GET requests.
                            warnings.warn('%(view)s(serializer_class='\
                                '%(serializer_class)s, schema=%(schema)s):'\
                                ' %(method)s %(path)s'\
                                ' invalid example for %(example_key)s:'\
                                ' %(example)s, err=%(err)s' % {
                                    'view': view.__class__.__name__,
                                    'serializer_class': serializer_class,
                                    'schema': schema,
                                    'method': method,
                                    'path': path,
                                    'example_key': example_key,
                                    'example': example,
                                    'err': err})
                    else:
                        warnings.warn('%(view)s: %(method)s %(path)s'\
                            ' example present but no serializer for'\
                            ' %(example_key)s: %(example)s' % {
                                'view': view.__class__.__name__,
                                'method': method,
                                'path': path,
                                'example_key': example_key,
                                'example': example})
                elif serializer_class is not None:
                    warnings.warn('%(view)s: %(method)s %(path)s'\
                        ' has no %(example_key)s: %(example)s' % {
                            'view': view.__class__.__name__,
                            'method': method,
                            'path': path,
                            'example_key': example_key,
                            'example': example})
        else:
            warnings.warn('%(view)s: %(method)s %(path)s has no examples' % {
                    'view': view.__class__.__name__,
                    'method': method,
                    'path': path})


    def get_request_serializer(self):
        path = self.view.request.path
        method = self.view.request.method
        view = self.view
        serializer_class = None

        if hasattr(view, 'get_serializer_class'):
            serializer_class = view.get_serializer_class()
        view_method = getattr(self.view, method.lower(), None)
        if view_method and hasattr(view_method, '_swagger_auto_schema'):
            #pylint:disable=protected-access
            data = view_method._swagger_auto_schema
            request_body_serializer_class = data.get('request_body', None)
            if request_body_serializer_class is not None:
                serializer_class = request_body_serializer_class
                if not issubclass(serializer_class, serializers.Serializer):
                    # We assume `request_body=no_body` here.
                    serializer_class = None

        if not serializer_class:
            return None

        serializer = serializer_class(context=view.get_serializer_context())
        component = self.resolve_serializer(serializer, 'request')
        schema = component.schema
        try:
            if method.lower() != 'patch':
                # XXX We disable showing patch as they are so close
                # to put requests.
                self._validate_examples(
                    self.examples if hasattr(self, 'examples') else [],
                    path, method,
                    serializer_class=serializer_class, schema=schema,
                    example_key='requestBody')
        except exceptions.APIException:
            serializer = None
            warnings.warn('{}: serializer_class() raised an exception during '
                          'schema generation. Serializer fields will not be '
                          'generated for {} {}.'
                          .format(view.__class__.__name__, method, path))

        return serializer

    def get_paginated_name(self, serializer_name):
        if issubclass(self.view.pagination_class, TypeaheadPagination):
            return 'Typeahead%sList' % serializer_name
        return super(AutoSchema, self).get_paginated_name(serializer_name)

    def get_response_serializers(self):
        schema = {}
        method = self.view.request.method
        path = self.view.request.path
        view = self.view

        if method == 'DELETE':
            return None

        serializer = self._get_serializer()
        if serializer:
            if isinstance(serializer, serializers.Serializer):
                responses = self._get_response_for_code(
                    serializer, '200', direction='response')
                schema = responses['content']['application/json']['schema']
                if '$ref' in schema:
                    key = schema['$ref'].split('/')[-1]
                    schema = self.registry[(key, 'schemas')].schema
            try:
                self._validate_examples(
                    self.examples if hasattr(self, 'examples') else [],
                    path, method,
                    serializer_class=serializer.__class__, schema=schema)
            except exceptions.APIException as err:
                serializer = None
                warnings.warn('{}: serializer_class() raised an exception'
                    ' during '
                    'schema generation. Serializer fields will not be '
                    'generated for {} {}.'.format(
                        view.__class__.__name__, method, path))

        return serializer


def populate_schema_from_docstring(schema, docstring, api_base_url=None):
    schema.update({
        'func': 'GET',
        'path': "",
    })
    if docstring:
        docstring = docstring.strip()
        func_tags, summary, description, examples = \
            split_descr_and_examples(docstring, api_base_url=api_base_url)
        examples = format_examples(examples)
        schema['summary'] = summary
        schema['description'] = description
        schema['tags'] = list(func_tags) if func_tags else []
        if not settings.OPENAPI_SPEC_COMPLIANT:
            schema['examples'] = [
                {'resp': example['requestBody']}
                for example in examples if 'requestBody' in example]
    return schema


def get_notification_schema(notification_slug, api_base_url=None):
    """
    Returns the summary, description and examples for a notification.
    """
    #pylint:disable=too-many-statements
    serializer = None
    docstring = None
    if notification_slug == 'user_contact':
        serializer = ContactUsNotificationSerializer()
        docstring = notification_signals.user_contact_notice.__doc__
    elif notification_slug == 'user_registered':
        serializer = UserNotificationSerializer()
        docstring = notification_signals.user_registered_notice.__doc__
    elif notification_slug == 'user_activated':
        serializer = UserNotificationSerializer()
        docstring = notification_signals.user_activated_notice.__doc__
    elif notification_slug == 'card_expires_soon':
        serializer = ExpireProfileNotificationSerializer()
        docstring = notification_signals.card_expires_soon_notice.__doc__
    elif notification_slug == 'expires_soon':
        serializer = SubscriptionExpireNotificationSerializer()
        docstring = notification_signals.expires_soon_notice.__doc__
    elif notification_slug == 'profile_updated':
        serializer = ChangeProfileNotificationSerializer()
        docstring = notification_signals.profile_updated_notice.__doc__
    elif notification_slug == 'card_updated':
        serializer = ChangeProfileNotificationSerializer()
        docstring = notification_signals.card_updated_notice.__doc__
    elif notification_slug == 'period_sales_report_created':
        serializer = AggregatedSalesNotificationSerializer()
        docstring = \
            notification_signals.period_sales_report_created_notice.__doc__
    elif notification_slug == 'charge_updated':
        serializer = ChargeNotificationSerializer()
        docstring = notification_signals.charge_updated_notice.__doc__
    elif notification_slug == 'order_executed':
        serializer = InvoiceNotificationSerializer()
        docstring = notification_signals.order_executed_notice.__doc__
    elif notification_slug == 'renewal_charge_failed':
        serializer = RenewalFailedNotificationSerializer()
        docstring = notification_signals.renewal_charge_failed_notice.__doc__
    elif notification_slug == 'claim_code_generated':
        serializer = ClaimNotificationSerializer()
        docstring = notification_signals.claim_code_generated_notice.__doc__
    elif notification_slug == 'processor_setup_error':
        serializer = ProcessorSetupNotificationSerializer()
        docstring = notification_signals.processor_setup_error_notice.__doc__
    elif notification_slug == 'role_grant_created':
        serializer = RoleGrantNotificationSerializer()
        docstring = notification_signals.role_grant_created_notice.__doc__
    elif notification_slug == 'role_request_created':
        serializer = RoleRequestNotificationSerializer()
        docstring = notification_signals.role_request_created_notice.__doc__
    elif notification_slug == 'role_grant_accepted':
        serializer = RoleGrantNotificationSerializer()
        docstring = notification_signals.role_grant_accepted_notice.__doc__
    elif notification_slug == 'subscription_grant_accepted':
        serializer = SubscriptionAcceptedNotificationSerializer()
        docstring = \
            notification_signals.subscription_grant_accepted_notice.__doc__
    elif notification_slug == 'subscription_grant_created':
        serializer = SubscriptionCreatedNotificationSerializer()
        docstring = \
            notification_signals.subscription_grant_created_notice.__doc__
    elif notification_slug == 'subscription_request_accepted':
        serializer = SubscriptionAcceptedNotificationSerializer()
        docstring = \
            notification_signals.subscription_request_accepted_notice.__doc__
    elif notification_slug == 'subscription_request_created':
        serializer = SubscriptionCreatedNotificationSerializer()
        docstring = \
            notification_signals.subscription_request_created_notice.__doc__

    generator = APIDocGenerator()
    inspector = AutoSchema()
    inspector.registry = generator.registry
    inspector.view = GenericAPIView()
    inspector.view.request = HttpRequest()
    inspector.method = 'GET'
    inspector.path = ''
    if serializer:
        responses = inspector._get_response_for_code(
            serializer, '200', direction='response')
        schema = responses['content']['application/json']['schema']
        if '$ref' in schema:
            key = schema['$ref'].split('/')[-1]
            schema = inspector.registry[(key, 'schemas')].schema
    else:
        schema = ""
    schema = {
        'operationId': notification_slug,
        'responses': {
            '200': {
                'content': {
                    'application/json': {
                        'schema': schema
                    }
                }
            }
        }
    }
    populate_schema_from_docstring(schema, docstring, api_base_url=api_base_url)
    return schema
