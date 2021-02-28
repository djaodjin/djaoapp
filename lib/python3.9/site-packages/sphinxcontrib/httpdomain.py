"""
    sphinxcontrib.httpdomain
    ~~~~~~~~~~~~~~~~~~~~~~~~

    The HTTP domain for documenting RESTful HTTP APIs.

    :copyright: Copyright 2011 by Hong Minhee
    :license: BSD, see LICENSE for details.

"""

import re

from docutils import nodes

from pygments.lexer import RegexLexer, bygroups
from pygments.lexers import get_lexer_by_name
from pygments.token import Literal, Text, Operator, Keyword, Name, Number
from pygments.util import ClassNotFound

from sphinx import addnodes
from sphinx.roles import XRefRole
from sphinx.domains import Domain, ObjType, Index
from sphinx.directives import ObjectDescription, directives
from sphinx.util.nodes import make_refnode
from sphinx.util.docfields import GroupedField, TypedField

# The env.get_doctree() lookup results in a pickle.load() call which is
# expensive enough to dominate the runtime entirely when the number of endpoints
# and references is large enough. The doctrees are generated during the read-
# phase and we can cache their lookup during the write-phase significantly
# improving performance.
# Currently sphinxcontrib-httpdomain does not declare to support parallel read
# support (parallel_read_safe is the default False) so we can simply use a
# module global to hold the cache.
_doctree_cache = {}


class DocRef(object):
    """Represents a reference to an abstract specification."""

    def __init__(self, base_url, anchor, section):
        self.base_url = base_url
        self.anchor = anchor
        self.section = section

    def __repr__(self):
        """Returns the URL onto related specification section for the related
        object."""
        return '{0}#{1}{2}'.format(self.base_url, self.anchor, self.section)


class RFC2616Ref(DocRef):
    """Represents a reference to RFC2616.
    In 2014, RFC2616 was replaced by multiple RFCs (7230-7237)."""

    def __init__(self, section):
        url = 'http://www.w3.org/Protocols/rfc2616/rfc2616-sec{0:d}.html'
        url = url.format(int(section))
        super(RFC2616Ref, self).__init__(url, 'sec', section)


class IETFRef(DocRef):
    """Represents a reference to the specific IETF RFC."""

    def __init__(self, rfc, section):
        url = 'https://tools.ietf.org/html/rfc{0:d}'.format(rfc)
        super(IETFRef, self).__init__(url, 'section-', section)


class EventSourceRef(DocRef):

    def __init__(self, section):
        url = 'http://www.w3.org/TR/eventsource/'
        super(EventSourceRef, self).__init__(url, section, '')


class CORSRef(DocRef):
    """Represents a reference to W3 Cross-Origin Resource Sharing recommendation."""

    def __init__(self, name, type):
        url = 'http://www.w3.org/TR/cors/'
        super(CORSRef, self).__init__(url, name, '-' + type)


#: Mapping from lowercase HTTP method name to :class:`DocRef` object which
#: maintains the URL which points to the section of the RFC which defines that
#: HTTP method.
METHOD_REFS = {
    'patch': IETFRef(5789, 2),
    'options': IETFRef(7231, '4.3.7'),
    'get': IETFRef(7231, '4.3.1'),
    'head': IETFRef(7231, '4.3.2'),
    'post': IETFRef(7231, '4.3.3'),
    'put': IETFRef(7231, '4.3.4'),
    'delete': IETFRef(7231, '4.3.5'),
    'trace': IETFRef(7231, '4.3.8'),
    'connect': IETFRef(7231, '4.3.6'),
    'copy': IETFRef(2518, 8.8),
    'any': ''
}


#: Mapping from HTTP header name to :class:`DocRef` object which
#: maintains the URL which points to the related section of the RFC.
HEADER_REFS = {
    'Accept': IETFRef(7231, '5.3.2'),
    'Accept-Charset': IETFRef(7231, '5.3.3'),
    'Accept-Encoding': IETFRef(7231, '5.3.4'),
    'Accept-Language': IETFRef(7231, '5.3.5'),
    'Accept-Ranges': IETFRef(7233, 2.3),
    'Age': IETFRef(7234, 5.1),
    'Allow': IETFRef(7231, '7.4.1'),
    'Authorization': IETFRef(7235, 4.2),
    'Cache-Control': IETFRef(7234, 5.2),
    'Connection': IETFRef(7230, 6.1),
    'Content-Encoding': IETFRef(7231, '3.1.2.2'),
    'Content-Language': IETFRef(7231, '3.1.3.2'),
    'Content-Length': IETFRef(7230, '3.3.2'),
    'Content-Location': IETFRef(7231, '3.1.4.2'),
    'Content-MD5': RFC2616Ref(14.15), # removed
    'Content-Range': IETFRef(7233, 4.2),
    'Content-Type': IETFRef(7231, '3.1.1.5'),
    'Cookie': IETFRef(2109, '4.3.4'), # also RFC6265 section 5.4
    'Date': IETFRef(7231, '7.1.1.2'),
    'Destination': IETFRef(2518, 9.3),
    'ETag': IETFRef(7232, 2.3),
    'Expect': IETFRef(7231, '5.1.1'),
    'Expires': IETFRef(7234, 5.3),
    'From': IETFRef(7231, '5.5.2'),
    'Host': IETFRef(7230, 5.4),
    'If-Match': IETFRef(7232, 3.1),
    'If-Modified-Since': IETFRef(7232, 3.3),
    'If-None-Match': IETFRef(7232, 3.2),
    'If-Range': IETFRef(7233, 3.2),
    'If-Unmodified-Since': IETFRef(7232, 3.4),
    'Last-Event-ID': EventSourceRef('last-event-id'),
    'Last-Modified': IETFRef(7232, 2.2),
    'Link': IETFRef(5988, '5'),
    'Location': IETFRef(7231, '7.1.2'),
    'Max-Forwards': IETFRef(7231, '5.1.2'),
    'Pragma': IETFRef(7234, 5.4),
    'Proxy-Authenticate': IETFRef(7235, 4.3),
    'Proxy-Authorization': IETFRef(7235, 4.4),
    'Range': IETFRef(7233, 3.1),
    'Referer': IETFRef(7231, '5.5.2'),
    'Retry-After': IETFRef(7231, '7.1.3'),
    'Server': IETFRef(7231, '7.4.2'),
    'Set-Cookie': IETFRef(2109, '4.2.2'),
    'TE': IETFRef(7230, 4.3),
    'Trailer': IETFRef(7230, 4.4),
    'Transfer-Encoding': IETFRef(7230, '3.3.1'),
    'Upgrade': IETFRef(7230, 6.7),
    'User-Agent': IETFRef(7231, '5.5.3'),
    'Vary': IETFRef(7231, '7.1.4'),
    'Via': IETFRef(7230, '5.7.1'),
    'Warning': IETFRef(7234, 5.5),
    'WWW-Authenticate': IETFRef(7235, 4.1),
    'Access-Control-Allow-Origin': CORSRef('access-control-allow-origin',
                                           'response-header'),
    'Access-Control-Allow-Credentials': CORSRef('access-control-allow-credentials',
                                                'response-header'),
    'Access-Control-Expose-Headers': CORSRef('access-control-expose-headers',
                                             'response-header'),
    'Access-Control-Max-Age': CORSRef('access-control-max-age',
                                      'response-header'),
    'Access-Control-Allow-Methods': CORSRef('access-control-allow-methods',
                                            'response-header'),
    'Access-Control-Allow-Headers': CORSRef('access-control-allow-headers',
                                            'response-header'),
    'Origin': CORSRef('origin', 'request-header'),
    'Access-Control-Request-Method': CORSRef('access-control-request-method',
                                             'response-header'),
    'Access-Control-Request-Headers': CORSRef('access-control-request-headers',
                                              'response-header'),
}


HTTP_STATUS_CODES = {
    100: 'Continue',
    101: 'Switching Protocols',
    102: 'Processing',
    200: 'OK',
    201: 'Created',
    202: 'Accepted',
    203: 'Non Authoritative Information',
    204: 'No Content',
    205: 'Reset Content',
    206: 'Partial Content',
    207: 'Multi Status',
    226: 'IM Used',              # see RFC 3229
    300: 'Multiple Choices',
    301: 'Moved Permanently',
    302: 'Found',
    303: 'See Other',
    304: 'Not Modified',
    305: 'Use Proxy',
    307: 'Temporary Redirect',
    400: 'Bad Request',
    401: 'Unauthorized',
    402: 'Payment Required',     # unused
    403: 'Forbidden',
    404: 'Not Found',
    405: 'Method Not Allowed',
    406: 'Not Acceptable',
    407: 'Proxy Authentication Required',
    408: 'Request Timeout',
    409: 'Conflict',
    410: 'Gone',
    411: 'Length Required',
    412: 'Precondition Failed',
    413: 'Request Entity Too Large',
    414: 'Request URI Too Long',
    415: 'Unsupported Media Type',
    416: 'Requested Range Not Satisfiable',
    417: 'Expectation Failed',
    418: "I'm a teapot",        # see RFC 2324
    422: 'Unprocessable Entity',
    423: 'Locked',
    424: 'Failed Dependency',
    426: 'Upgrade Required',
    429: 'Too Many Requests',
    449: 'Retry With',           # proprietary MS extension
    451: 'Unavailable For Legal Reasons',
    500: 'Internal Server Error',
    501: 'Not Implemented',
    502: 'Bad Gateway',
    503: 'Service Unavailable',
    504: 'Gateway Timeout',
    505: 'HTTP Version Not Supported',
    507: 'Insufficient Storage',
    510: 'Not Extended'
}

WEBDAV_STATUS_CODES = [207, 422, 423, 424, 507]

http_sig_param_re = re.compile(r'\((?:(?P<type>[^:)]+):)?(?P<name>[\w_]+)\)',
                               re.VERBOSE)


def sort_by_method(entries):
    def cmp(item):
        order = ['HEAD', 'GET', 'POST', 'PUT', 'DELETE', 'PATCH',
                 'OPTIONS', 'TRACE', 'CONNECT', 'COPY', 'ANY']
        method = item[0].split(' ', 1)[0]
        if method in order:
            return order.index(method)
        return 100
    return sorted(entries, key=cmp)


def http_resource_anchor(method, path):
    path = re.sub(r'[{}]', '', re.sub(r'[<>:/]', '-', path))
    return method.lower() + '-' + path


class HTTPResource(ObjectDescription):

    doc_field_types = [
        TypedField('parameter', label='Parameters',
                   names=('param', 'parameter', 'arg', 'argument'),
                   typerolename='obj', typenames=('paramtype', 'type')),
        TypedField('jsonparameter', label='JSON Parameters',
                   names=('jsonparameter', 'jsonparam', 'json'),
                   typerolename='obj', typenames=('jsonparamtype', 'jsontype')),
        TypedField('requestjsonobject', label='Request JSON Object',
                   names=('reqjsonobj', 'reqjson', '<jsonobj', '<json'),
                   typerolename='obj', typenames=('reqjsonobj', '<jsonobj')),
        TypedField('requestjsonarray', label='Request JSON Array of Objects',
                   names=('reqjsonarr', '<jsonarr'),
                   typerolename='obj',
                   typenames=('reqjsonarrtype', '<jsonarrtype')),
        TypedField('responsejsonobject', label='Response JSON Object',
                   names=('resjsonobj', 'resjson', '>jsonobj', '>json'),
                   typerolename='obj', typenames=('resjsonobj', '>jsonobj')),
        TypedField('responsejsonarray', label='Response JSON Array of Objects',
                   names=('resjsonarr', '>jsonarr'),
                   typerolename='obj',
                   typenames=('resjsonarrtype', '>jsonarrtype')),
        TypedField('queryparameter', label='Query Parameters',
                   names=('queryparameter', 'queryparam', 'qparam', 'query'),
                   typerolename='obj',
                   typenames=('queryparamtype', 'querytype', 'qtype')),
        GroupedField('formparameter', label='Form Parameters',
                     names=('formparameter', 'formparam', 'fparam', 'form')),
        GroupedField('requestheader', label='Request Headers',
                     rolename='header',
                     names=('<header', 'reqheader', 'requestheader')),
        GroupedField('responseheader', label='Response Headers',
                     rolename='header',
                     names=('>header', 'resheader', 'responseheader')),
        GroupedField('statuscode', label='Status Codes',
                     rolename='statuscode',
                     names=('statuscode', 'status', 'code'))
    ]

    option_spec = {
        'deprecated': directives.flag,
        'noindex': directives.flag,
        'synopsis': lambda x: x,
    }

    method = NotImplemented

    def handle_signature(self, sig, signode):
        method = self.method.upper() + ' '
        signode += addnodes.desc_name(method, method)
        offset = 0
        path = None
        for match in http_sig_param_re.finditer(sig):
            path = sig[offset:match.start()]
            signode += addnodes.desc_name(path, path)
            params = addnodes.desc_parameterlist()
            typ = match.group('type')
            if typ:
                typ += ': '
                params += addnodes.desc_annotation(typ, typ)
            name = match.group('name')
            params += addnodes.desc_parameter(name, name)
            signode += params
            offset = match.end()
        if offset < len(sig):
            path = sig[offset:len(sig)]
            signode += addnodes.desc_name(path, path)
        assert path is not None, 'no matches for sig: %s' % sig
        fullname = self.method.upper() + ' ' + path
        signode['method'] = self.method
        signode['path'] = sig
        signode['fullname'] = fullname
        return (fullname, self.method, sig)

    def needs_arglist(self):
        return False

    def add_target_and_index(self, name_cls, sig, signode):
        signode['ids'].append(http_resource_anchor(*name_cls[1:]))
        if 'noindex' not in self.options:
            self.env.domaindata['http'][self.method][sig] = (
                self.env.docname,
                self.options.get('synopsis', ''),
                'deprecated' in self.options)

    def get_index_text(self, modname, name):
        return ''


class HTTPOptions(HTTPResource):

    method = 'options'


class HTTPHead(HTTPResource):

    method = 'head'


class HTTPPatch(HTTPResource):

    method = 'patch'


class HTTPPost(HTTPResource):

    method = 'post'


class HTTPGet(HTTPResource):

    method = 'get'


class HTTPPut(HTTPResource):

    method = 'put'


class HTTPDelete(HTTPResource):

    method = 'delete'


class HTTPTrace(HTTPResource):

    method = 'trace'


class HTTPConnect(HTTPResource):

    method = 'connect'


class HTTPCopy(HTTPResource):

    method = 'copy'


class HTTPAny(HTTPResource):

    method = 'any'


class HTTPXRefRole(XRefRole):

    def __init__(self, method, **kwargs):
        XRefRole.__init__(self, **kwargs)
        self.method = method

    def process_link(self, env, refnode, has_explicit_title, title, target):
        if not has_explicit_title:
            title = self.method.upper() + ' ' + title
        return title, target


class HTTPXRefMethodRole(XRefRole):

    def result_nodes(self, document, env, node, is_ref):
        method = node[0][0].lower()
        rawsource = node[0].rawsource
        config = env.domains['http'].env.config
        if method not in METHOD_REFS:
            if not config['http_strict_mode']:
                return [nodes.emphasis(method, method)], []
            reporter = document.reporter
            msg = reporter.error('%s is not valid HTTP method' % method,
                                 line=node.line)
            prb = nodes.problematic(method, method)
            return [prb], [msg]
        url = str(METHOD_REFS[method])
        if not url:
            return [nodes.emphasis(method, method)], []
        node = nodes.reference(rawsource, method.upper(), refuri=url)
        return [node], []


class HTTPXRefStatusRole(XRefRole):

    def result_nodes(self, document, env, node, is_ref):
        def get_code_status(text):
            if text.isdigit():
                code = int(text)
                return code, HTTP_STATUS_CODES.get(code)
            else:
                try:
                    code, status = re.split(r'\s', text.strip(), 1)
                    code = int(code)
                except ValueError:
                    return None, None
                known_status = HTTP_STATUS_CODES.get(code)
                if known_status is None:
                    return code, None
                elif known_status.lower() != status.lower():
                    return code, None
                else:
                    return code, status

        def report_unknown_code():
            if not config['http_strict_mode']:
                return [nodes.emphasis(text, text)], []
            reporter = document.reporter
            msg = reporter.error('%d is unknown HTTP status code' % code,
                                 line=node.line)
            prb = nodes.problematic(text, text)
            return [prb], [msg]

        def report_invalid_code():
            if not config['http_strict_mode']:
                return [nodes.emphasis(text, text)], []
            reporter = document.reporter
            msg = reporter.error(
                'HTTP status code must be an integer (e.g. `200`) or '
                'start with an integer (e.g. `200 OK`); %r is invalid' %
                text,
                line=node.line
            )
            prb = nodes.problematic(text, text)
            return [prb], [msg]

        text = node[0][0]
        rawsource = node[0].rawsource
        config = env.domains['http'].env.config

        code, status = get_code_status(text)
        if code is None:
            return report_invalid_code()
        elif status is None:
            return report_unknown_code()
        elif code == 226:
            url = 'http://www.ietf.org/rfc/rfc3229.txt'
        elif code == 418:
            url = 'http://www.ietf.org/rfc/rfc2324.txt'
        elif code == 429:
            url = 'http://tools.ietf.org/html/rfc6585#section-4'
        elif code == 449:
            url = 'http://msdn.microsoft.com/en-us/library/dd891478(v=prot.10).aspx'
        elif code == 451:
            url = 'http://www.ietf.org/rfc/rfc7725.txt'
        elif code in WEBDAV_STATUS_CODES:
            url = 'http://tools.ietf.org/html/rfc4918#section-11.%d' % (WEBDAV_STATUS_CODES.index(code) + 1)
        elif code in HTTP_STATUS_CODES:
            url = 'http://www.w3.org/Protocols/rfc2616/rfc2616-sec10.html' \
                  '#sec10.' + ('%d.%d' % (code // 100, 1 + code % 100))
        else:
            url = ''
        node = nodes.reference(rawsource, '%d %s' % (code, status), refuri=url)
        return [node], []


class HTTPXRefHeaderRole(XRefRole):

    def result_nodes(self, document, env, node, is_ref):
        header = node[0][0]
        rawsource = node[0].rawsource
        if header not in HEADER_REFS:
            _header = '-'.join(map(lambda i: i.title(), header.split('-')))
            if _header not in HEADER_REFS:
                return [nodes.emphasis(header, header)], []
        url = str(HEADER_REFS[header])
        node = nodes.reference(rawsource, header, refuri=url)
        return [node], []


class HTTPIndex(Index):

    name = 'routingtable'
    localname = 'HTTP Routing Table'
    shortname = 'routing table'

    def __init__(self, *args, **kwargs):
        super(HTTPIndex, self).__init__(*args, **kwargs)

        self.ignore = [
            [l for l in x.split('/') if l]
            for x in self.domain.env.config['http_index_ignore_prefixes']]
        self.ignore.sort(reverse=True)

        # During HTML generation these values pick from class,
        # not from instance so we have a little hack the system
        cls = self.__class__
        cls.shortname = self.domain.env.config['http_index_shortname']
        cls.localname = self.domain.env.config['http_index_localname']

    def grouping_prefix(self, path):
        letters = [x for x in path.split('/') if x]
        for prefix in self.ignore:
            if letters[:len(prefix)] == prefix:
                return '/' + '/'.join(letters[:len(prefix) + 1])
        return '/%s' % (letters[0] if letters else '',)

    def generate(self, docnames=None):
        content = {}
        items = ((method, path, info)
                 for method, routes in self.domain.routes.items()
                 for path, info in routes.items())
        items = sorted(items, key=lambda item: item[1])
        for method, path, info in items:
            entries = content.setdefault(self.grouping_prefix(path), [])
            entries.append([
                method.upper() + ' ' + path, 0, info[0],
                http_resource_anchor(method, path),
                '', 'Deprecated' if info[2] else '', info[1]
            ])
        items = sorted(
            (path, sort_by_method(entries))
            for path, entries in content.items()
        )
        return (items, True)


class HTTPDomain(Domain):
    """HTTP domain."""

    name = 'http'
    label = 'HTTP'

    object_types = {
        'options': ObjType('options', 'options', 'obj'),
        'head': ObjType('head', 'head', 'obj'),
        'post': ObjType('post', 'post', 'obj'),
        'get': ObjType('get', 'get', 'obj'),
        'put': ObjType('put', 'put', 'obj'),
        'patch': ObjType('patch', 'patch', 'obj'),
        'delete': ObjType('delete', 'delete', 'obj'),
        'trace': ObjType('trace', 'trace', 'obj'),
        'connect': ObjType('connect', 'connect', 'obj'),
        'copy': ObjType('copy', 'copy', 'obj'),
        'any': ObjType('any', 'any', 'obj')
    }

    directives = {
        'options': HTTPOptions,
        'head': HTTPHead,
        'post': HTTPPost,
        'get': HTTPGet,
        'put': HTTPPut,
        'patch': HTTPPatch,
        'delete': HTTPDelete,
        'trace': HTTPTrace,
        'connect': HTTPConnect,
        'copy': HTTPCopy,
        'any': HTTPAny
    }

    roles = {
        'options': HTTPXRefRole('options'),
        'head': HTTPXRefRole('head'),
        'post': HTTPXRefRole('post'),
        'get': HTTPXRefRole('get'),
        'put': HTTPXRefRole('put'),
        'patch': HTTPXRefRole('patch'),
        'delete': HTTPXRefRole('delete'),
        'trace': HTTPXRefRole('trace'),
        'connect': HTTPXRefRole('connect'),
        'copy': HTTPXRefRole('copy'),
        'any': HTTPXRefRole('any'),
        'statuscode': HTTPXRefStatusRole(),
        'method': HTTPXRefMethodRole(),
        'header': HTTPXRefHeaderRole()
    }

    initial_data = {
        'options': {},  # path: (docname, synopsis)
        'head': {},
        'post': {},
        'get': {},
        'put': {},
        'patch': {},
        'delete': {},
        'trace': {},
        'connect': {},
        'copy': {},
        'any': {}
    }

    indices = [HTTPIndex]

    @property
    def routes(self):
        return dict((key, self.data[key]) for key in self.object_types)

    def clear_doc(self, docname):
        for typ, routes in self.routes.items():
            for path, info in list(routes.items()):
                if info[0] == docname:
                    del routes[path]

    def resolve_xref(self, env, fromdocname, builder, typ, target,
                     node, contnode):
        try:
            info = self.data[str(typ)][target]
        except KeyError:
            text = contnode.rawsource
            role = self.roles.get(typ)
            if role is None:
                return None

            if fromdocname not in _doctree_cache:
                _doctree_cache[fromdocname] = env.get_doctree(fromdocname)
            doctree = _doctree_cache[fromdocname]

            resnode = role.result_nodes(doctree, env, node, None)[0][0]
            if isinstance(resnode, addnodes.pending_xref):
                text = node[0][0]
                reporter = doctree.reporter
                reporter.warning('Cannot resolve reference to %r' % text,
                                 line=node.line)
                return None
            return resnode
        else:
            anchor = http_resource_anchor(typ, target)
            title = typ.upper() + ' ' + target
            return make_refnode(builder, fromdocname, info[0], anchor,
                                contnode, title)

    def resolve_any_xref(self, env, fromdocname, builder, target, node, contnode):
        """Resolve the pending_xref *node* with the given *target*.

        The reference comes from an "any" or similar role, which means that Sphinx
        don't know the type.

        For now sphinxcontrib-httpdomain doesn't resolve any xref nodes.

        :return:
           list of tuples ``('domain:role', newnode)``, where ``'domain:role'``
           is the name of a role that could have created the same reference,
        """
        return []

    def get_objects(self):
        for method, routes in self.routes.items():
            for path, info in routes.items():
                anchor = http_resource_anchor(method, path)
                yield (path, path, method, info[0], anchor, 1)


class HTTPLexer(RegexLexer):
    """Lexer for HTTP sessions."""

    name = 'HTTP'
    aliases = ['http']

    flags = re.DOTALL

    def header_callback(self, match):
        if match.group(1).lower() == 'content-type':
            content_type = match.group(5).strip()
            if ';' in content_type:
                content_type = content_type[:content_type.find(';')].strip()
            self.content_type = content_type
        yield match.start(1), Name.Attribute, match.group(1)
        yield match.start(2), Text, match.group(2)
        yield match.start(3), Operator, match.group(3)
        yield match.start(4), Text, match.group(4)
        yield match.start(5), Literal, match.group(5)
        yield match.start(6), Text, match.group(6)

    def continuous_header_callback(self, match):
        yield match.start(1), Text, match.group(1)
        yield match.start(2), Literal, match.group(2)
        yield match.start(3), Text, match.group(3)

    def content_callback(self, match):
        content_type = getattr(self, 'content_type', None)
        content = match.group()
        offset = match.start()
        if content_type:
            from pygments.lexers import get_lexer_for_mimetype
            try:
                lexer = get_lexer_for_mimetype(content_type)
            except ClassNotFound:
                pass
            else:
                for idx, token, value in lexer.get_tokens_unprocessed(content):
                    yield offset + idx, token, value
                return
        yield offset, Text, content

    tokens = {
        'root': [
            (r'(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS|TRACE|COPY)( +)([^ ]+)( +)'
             r'(HTTPS?)(/)(1\.[01])(\r?\n|$)',
             bygroups(Name.Function, Text, Name.Namespace, Text,
                      Keyword.Reserved, Operator, Number, Text),
             'headers'),
            (r'(HTTPS?)(/)(1\.[01])( +)(\d{3})( +)([^\r\n]+)(\r?\n|$)',
             bygroups(Keyword.Reserved, Operator, Number, Text, Number,
                      Text, Name.Exception, Text),
             'headers'),
        ],
        'headers': [
            (r'([^\s:]+)( *)(:)( *)([^\r\n]+)(\r?\n|$)', header_callback),
            (r'([\t ]+)([^\r\n]+)(\r?\n|$)', continuous_header_callback),
            (r'\r?\n', Text, 'content')
        ],
        'content': [
            (r'.+', content_callback)
        ]
    }


def setup(app):
    app.add_domain(HTTPDomain)

    try:
        get_lexer_by_name('http')
    except ClassNotFound:
        app.add_lexer('http', HTTPLexer())
    app.add_config_value('http_index_ignore_prefixes', [], None)
    app.add_config_value('http_index_shortname', 'routing table', True)
    app.add_config_value('http_index_localname', 'HTTP Routing Table', True)
    app.add_config_value('http_strict_mode', True, None)
    app.add_config_value('http_headers_ignore_prefixes', ['X-'], None)
