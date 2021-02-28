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

from django import template
from django.utils.safestring import mark_safe

from ..compat import six


register = template.Library()


@register.filter
def get_relationships(element, tag=None):
    return element.get_relationships(tag).all()

@register.simple_tag
def print_tree(tree, excludes=None):
    html = print_dict(tree, "<ul class=\"fa-ul\">", None, excludes) + "</ul>"
    if html == "<ul></ul>":
        html = "<em>No file yet.</em>"
    return mark_safe(html)

def print_dict(dictionary, html="", parent=None, excludes=None):
    for key, value in six.iteritems(dictionary):
        if value:
            if not excludes or (excludes and not key in excludes):
                html += "<li><i class=\"fa-li fa fa-folder\"></i> \
                    <a class=\"pages-show-file\"\"\
                    href=\"\">%s/</a></li>" % key
                if parent:
                    html += print_dict(
                        value, "<ul style=\"display:none;\"\
                        class=\"fa-ul\" data-folder=\"%s\">" % key, "%s/%s" %\
                        (parent, key), excludes) + "</ul>"
                else:
                    html += print_dict(
                        value, "<ul style=\"display:none;\"\
                        class=\"fa-ul\" data-folder=\"%s\">" %\
                        key, key, excludes) + "</ul>"
        else:
            if parent:
                html += "<li><i class=\"fa-li fa fa-file-code-o\"></i> \
                    <a class=\"pages-edit-file\"\"\
                    href=\"\" data-filepath=\"%s/%s\">%s</a></li>" %\
                    (parent, key, key)
            else:
                html += "<li><i class=\"fa-li fa fa-file-code-o\"></i> \
                    <a class=\"pages-edit-file\"\"\
                    href=\"\" data-filepath=\"%s\">%s</a></li>" %\
                    (key, key)
    return html
