# Copyright (c) 2018, DjaoDjin inc.
# see LICENSE

"""
Default start page for a djaodjin-hosted product.
"""

import os, re

from django.conf import settings
from django.utils.safestring import mark_safe
from django.views.generic import TemplateView
from docutils import core
from docutils import frontend
from docutils.writers.html5_polyglot import Writer
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from drf_yasg.generators import OpenAPISchemaGenerator


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


class APIDocView(TemplateView):

    template_name = 'docs/api.html'

    def get_context_data(self, **kwargs):
        #pylint:disable=too-many-locals,too-many-nested-blocks
        context = super(APIDocView, self).get_context_data(**kwargs)
        api_end_points = []
        api_base_url = self.request.build_absolute_uri(location='/api')
        generator = OpenAPISchemaGenerator(
            info=OPENAPI_INFO, url=api_base_url)
        schema = generator.get_schema(request=None, public=True)
        tags = set([])
        for path, path_details in schema.paths.items():
            for func, func_details in path_details.items():
                if func.lower() == 'patch':
                    # We merge PUT and PATCH together.
                    continue
                try:
                    print("XXX %s" % str(func_details.operationId))
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
