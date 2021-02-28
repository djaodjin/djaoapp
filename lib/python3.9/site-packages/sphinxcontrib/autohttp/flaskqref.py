"""
    sphinxcontrib.autohttp.flaskqref
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    The sphinx.ext.autodoc-style HTTP API quick reference
    builder (from Flask)
    for sphinxcontrib.httpdomain.

    :copyright: Copyright 2011 by Hong Minhee
    :license: BSD, see LICENSE for details.

"""

from docutils import nodes
from docutils.statemachine import ViewList

from sphinxcontrib import httpdomain
from sphinx.util.nodes import nested_parse_with_titles

from .flask import AutoflaskBase


class QuickReferenceFlaskDirective(AutoflaskBase):


    header = [ '',
              '.. list-table::',
              '    :widths: 20 45 35',
              '    :header-rows: 1',
              '',
              '    * - Resource',
              '      - Operation',
              '      - Description'
            ]

    def run(self):
        node = nodes.section()
        node.document = self.state.document
        result = ViewList()
        for line in QuickReferenceFlaskDirective.header:
            result.append(line, '<qrefflask>')
        table={}
        table_sorted_names=[]

        for table_row in self.make_rst(qref=True):
            name = table_row['name']
            if table.get(name) is None:
                table[name]=[]
            table[name].append(table_row)
            if name not in table_sorted_names:
                table_sorted_names.append(name)

        table_sorted_names.sort()

        for name in table_sorted_names:
            # Keep table display clean by not repeating duplicate
            # resource names and descriptions
            display_name = name
            previous_description=None
            for row in table[name]:
                result.append('    * - %s' % display_name, '<qrefflask>')
                display_name =""
                result.append(row['operation'], '<qrefflask>')
                description = row['description']
                if previous_description is not None and previous_description == description:
                    description =""
                else:
                    previous_description = description

                result.append('      - %s' % description,  '<qrefflask>')

        result.append('', '<qrefflask>')
        nested_parse_with_titles(self.state, result, node)
        return node.children

def setup(app):
    app.setup_extension('sphinxcontrib.httpdomain')
    app.add_directive('qrefflask', QuickReferenceFlaskDirective)
