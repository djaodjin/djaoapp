# Copyright (c) 2020, DjaoDjin inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED
# TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
# OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
# OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
# ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

#pylint:disable=unused-argument

import markdown

from bs4 import BeautifulSoup
from django.template import loader
from django.views.generic import ListView, DetailView, TemplateView
from django.template.response import TemplateResponse

from ..compat import csrf, render_template, reverse
from ..locals import (enable_instrumentation, _add_editable_styles_context,
    get_edition_tools_context_data)
from ..mixins import AccountMixin, UploadedImageMixin
from ..models import PageElement


def inject_edition_tools(response, request=None, context=None,
                         body_top_template_name="pages/_body_top.html",
                         body_bottom_template_name="pages/_body_bottom.html",
                         edit_frame_template_name=None):
    #pylint:disable=too-many-arguments
    """
    Inject the edition tools into the html *content* and return
    a BeautifulSoup object of the resulting content + tools.
    """
    content_type = response.get('content-type', '')
    if not content_type.startswith('text/html'):
        return None
    if context is None:
        context = {}
    if 'urls' not in context:
        context.update({'urls': {
                'edit': {
                'api_less_overrides': reverse('pages_api_less_overrides'),
                'api_sitecss': reverse('edit_sitecss'),
                'api_sources': reverse('pages_api_sources'),
                'api_page_element_base': reverse('api_page_element',
                    kwargs={'path':''}),
                'api_medias': reverse('uploaded_media_elements',
                    kwargs={'path':''})}}})
    context.update(csrf(request))
    soup = None
    if body_top_template_name:
        template = loader.get_template(body_top_template_name)
        body_top = render_template(template, context, request).strip()
        if body_top:
            if not soup:
                soup = BeautifulSoup(response.content, 'html5lib')
            if soup and soup.body:
                # Implementation Note: we have to use ``.body.next`` here
                # because html5lib "fixes" our HTML by adding missing
                # html/body tags. Furthermore if we use
                #``soup.body.insert(1, BeautifulSoup(body_top, 'html.parser'))``
                # instead, later on ``soup.find_all(class_=...)`` returns
                # an empty set though ``soup.prettify()`` outputs the full
                # expected HTML text.
                soup.body.insert(1, BeautifulSoup(
                    body_top, 'html5lib').body.next)
    if body_bottom_template_name:
        template = loader.get_template(body_bottom_template_name)
        body_bottom = render_template(template, context, request).strip()
        if body_bottom:
            if not soup:
                soup = BeautifulSoup(response.content, 'html5lib')
            if soup and soup.body:
                soup.body.append(BeautifulSoup(body_bottom, 'html.parser'))

    if edit_frame_template_name:
        template = loader.get_template(edit_frame_template_name)
        edit_frame = render_template(template, context, request).strip()
        if edit_frame:
            if not soup:
                soup = BeautifulSoup(response.content, 'html5lib')
            edit_soup = BeautifulSoup(edit_frame, 'html5lib')
            soup = edit_soup

    return soup


class PageMixin(object):
    """
    Display or Edit a ``Page`` of a ``Project``.
    """
    body_bottom_template_name = "pages/_body_bottom.html"
    edit_frame_template_name = None

    def add_edition_tools(self, response, context=None):
        if context is None:
            context = {}
        context.update(get_edition_tools_context_data())
        return inject_edition_tools(
            response, request=self.request, context=context,
            body_bottom_template_name=self.body_bottom_template_name)

    @staticmethod
    def insert_formatted(editable, new_text):
        new_text = BeautifulSoup(new_text, 'html5lib')
        for image in new_text.find_all('img'):
            image['style'] = "max-width:100%"
        if editable.name == 'div':
            editable.clear()
            editable.append(new_text)
        else:
            editable.string = "ERROR : Impossible to insert HTML into \
                \"<%s></%s>\" element. It should be \"<div></div>\"." %\
                (editable.name, editable.name)
            editable['style'] = "color:red;"
            # Prevent edition of error notification
            editable['class'] = editable['class'].remove("editable")

    @staticmethod
    def insert_currency(editable, new_text):
        amount = float(new_text)
        editable.string = "$%.2f" % (amount/100)

    @staticmethod
    def insert_markdown(editable, new_text):
        new_text = markdown.markdown(new_text,)
        new_text = BeautifulSoup(new_text, 'html.parser')
        for image in new_text.find_all('img'):
            image['style'] = "max-width:100%"
        editable.name = 'div'
        editable.string = ''
        children_done = []
        for element in new_text.find_all():
            if element.name != 'html' and\
                element.name != 'body':
                if element.findChildren():
                    for sub_el in element.findChildren():
                        element.append(sub_el)
                        children_done += [sub_el]
                if not element in children_done:
                    editable.append(element)

    def get(self, request, *args, **kwargs):
        #pylint: disable=too-many-statements, too-many-locals
        enable_instrumentation()
        response = super(PageMixin, self).get(request, *args, **kwargs)
        if self.template_name and isinstance(response, TemplateResponse):
            response.render()
        soup = self.add_edition_tools(response)
        if not soup:
            content_type = response.get('content-type', '')
            if content_type.startswith('text/html'):
                soup = BeautifulSoup(response.content, 'html5lib')
        if soup:
            editable_ids = set([])
            for editable in soup.find_all(class_="editable"):
                try:
                    editable_ids |= set([editable['id']])
                except KeyError:
                    continue

            kwargs = {'slug__in': editable_ids}
            if self.account:
                kwargs.update({'account': self.account})
            for edit in PageElement.objects.filter(**kwargs):
                editable = soup.find(id=edit.slug)
                new_text = edit.text
                if editable:
                    if 'edit-formatted' in editable['class']:
                        self.insert_formatted(
                            editable, new_text)
                    elif 'edit-markdown' in editable['class']:
                        self.insert_markdown(editable, new_text)
                    elif 'edit-currency' in editable['class']:
                        self.insert_currency(editable, new_text)
                    elif 'droppable-image' in editable['class']:
                        editable['src'] = edit.text
                    else:
                        editable.string = new_text
            response.content = str(soup)
        return response


class PageView(PageMixin, AccountMixin, UploadedImageMixin, TemplateView):

    http_method_names = ['get']


class PageElementListView(ListView):
    model = PageElement
    tag = None

    def get_queryset(self):
        queryset = self.model.objects.all()
        if self.tag:
            queryset = queryset.filter(tag=self.tag)
        return queryset


class PageElementDetailView(DetailView):
    model = PageElement


class EditView(AccountMixin, TemplateView):

    inject_from_client = False
    template_name = 'pages/edit.html'

    def get_context_data(self, **kwargs):
        context = super(EditView, self).get_context_data(**kwargs)

        if self.request.path.startswith('/edit'):
            url = '/content%s' % self.request.path[5:]
        else:
            url = '/content%s' % self.request.path
        args = self.request.META.get('QUERY_STRING', '')
        if args and self.query_string:
            url = "%s?%s" % (url, args)

        context.update({
            'page': url,
            'inject_from_client': self.inject_from_client,
            'urls': {
                'edit': {
                    'api_sitecss': reverse('edit_sitecss'),
                    'api_less_overrides': reverse('pages_api_less_overrides'),
                    'api_sources': reverse('pages_api_sources'),
                    'api_page_element_base': reverse('api_page_element',
                        kwargs={'path':''}),
                    'api_medias': reverse('uploaded_media_elements',
                        kwargs={'path':''})}}})
        context = _add_editable_styles_context(context=context)
        return context
