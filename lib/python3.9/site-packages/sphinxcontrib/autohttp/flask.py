"""
    sphinxcontrib.autohttp.flask
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    The sphinx.ext.autodoc-style HTTP API reference builder (from Flask)
    for sphinxcontrib.httpdomain.

    :copyright: Copyright 2011 by Hong Minhee
    :license: BSD, see LICENSE for details.

"""
from __future__ import absolute_import

import re
import itertools
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

from .flask_base import AutoflaskBase

class AutoflaskDirective(AutoflaskBase):

    def run(self):
        node = nodes.section()
        node.document = self.state.document
        result = ViewList()
        for line in self.make_rst():
            result.append(line, '<autoflask>')
        nested_parse_with_titles(self.state, result, node)
        return node.children


def setup(app):
    app.setup_extension('sphinxcontrib.httpdomain')
    app.add_directive('autoflask', AutoflaskDirective)
