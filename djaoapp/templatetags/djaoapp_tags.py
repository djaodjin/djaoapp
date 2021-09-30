# Copyright (c) 2020, DjaoDjin inc.
# see LICENSE

from deployutils.apps.django.compat import (
    is_authenticated as base_is_authenticated)
from django import template
from django.conf import settings
from django.contrib.messages.api import get_messages
from django.forms import widgets, BaseForm
from django.template.defaultfilters import capfirst
from django.utils.encoding import force_text
from saas.templatetags.saas_tags import attached_organization

from ..compat import reverse, six, urljoin
from ..thread_locals import is_domain_site


register = template.Library()

@register.filter()
def no_cache(asset_url):
    pos = asset_url.rfind('?')
    if pos > 0:
        asset_url = asset_url[:pos]
    return asset_url

@register.filter()
def capitalize(text):
    return capfirst(text)


@register.filter()
def messages(obj):
    """
    Messages to be displayed to the current session.
    """
    if isinstance(obj, BaseForm):
        return obj.non_field_errors()
    return get_messages(obj)


@register.filter()
def pluralize(text):
    if text.endswith('s'):
        return text
    return text + 's'


@register.filter()
def site_printable_name(request):
    if hasattr(request, 'site') and is_domain_site(request.site):
        return request.site.printable_name
    return settings.APP_NAME


@register.filter()
def djasset(path):
    path_prefix = '/'
    return urljoin(path_prefix, path)


@register.simple_tag
def is_active(path, urls, *args, **kwargs): #pylint: disable=unused-argument
    if path in (reverse(urls, kwargs=kwargs) for url in urls.split()):
        return "active"
    return ""


@register.filter()
def is_authenticated(request):
    return base_is_authenticated(request)


@register.filter()
def is_checkbox(field):
    return isinstance(field.widget, widgets.CheckboxInput)


@register.filter()
def is_radio(field):
    return isinstance(field.widget, widgets.RadioSelect)


@register.filter()
def is_textarea(field):
    return isinstance(field.widget, widgets.Textarea)


@register.filter()
def iterfields(form):
    return six.iteritems(form.fields)


@register.filter()
def get_bounded_field(form, key):
    bounded_field = form[key]
    if bounded_field is None:
        raise KeyError("%s not found in form" % key)
    return bounded_field


@register.filter()
def value_attr(field):
    if hasattr(field, 'value'):
        value = field.value()
        if value is None:
            value = ""
        if value != "":
            return 'value=%s' % force_text(value)
    return ""


@register.filter()
def query_parameters(api_endpoint):
    results = []
    for param in api_endpoint.get('parameters', []):
        if param['in'] == 'query':
            param['type'] = param['schema']['type']
            results += [param]
    return results


@register.filter()
def request_body_parameters(api_endpoint, defs):
    if 'requestBody' in api_endpoint:
        results = []
        schema = \
            api_endpoint['requestBody']['content']['application/json']['schema']
        if 'properties' in schema:
            for prop_name, prop in schema['properties'].items():
                prop.update({'name': prop_name})
                if prop_name in schema.get('required', []):
                    prop.update({'required': True})
                if 'type' not in prop and 'enum' in prop:
                    prop.update({'type': "String"}) # XXX Country enum
                results += [prop]
            return results
    return []


@register.filter()
def responses_parameters(api_endpoint, defs):
    if 'responses' not in api_endpoint:
        return []
    results = {}
    for resp_code, param in api_endpoint['responses'].items():
        params = []
        if 'content' in param:
            schema = param['content']['application/json']['schema']
            if 'properties' in schema:
                for prop_name, prop in schema['properties'].items():
                    prop.update({'name': prop_name})
                    #if prop_name in schema.get('required', []):
                    #    prop.update({'required': True})
                    if 'type' not in prop and 'enum' in prop:
                        prop.update({'type': "String"}) # XXX Country enum
                    params += [prop]
        results.update({resp_code: params})
    return results


def schema_properties(schema, defs):
    params = []
    if schema['type'] == 'array':
        schema = schema.get('items', {})
    if 'properties' in schema:
        for prop_name, prop in schema['properties'].items():
            prop.update({'name': prop_name})
            if 'type' not in prop and 'enum' in prop:
                prop.update({'type': "String"}) # XXX Country enum
            params += [prop]
    return params


@register.filter()
def not_key(param_name):
    return not (param_name.lower() == 'password'
            or param_name.lower().endswith('_key')
            or param_name.lower().endswith('_password'))


@register.filter()
def url_app(request): #pylint:disable=unused-argument
    return reverse('product_default_start')

@register.filter()
def url_logout(request): #pylint:disable=unused-argument
    return reverse('logout')

@register.filter()
def url_contact(request): #pylint:disable=unused-argument
    return reverse('contact')

@register.filter()
def url_home(request): #pylint:disable=unused-argument
    return reverse('rules_page')

@register.filter()
def url_pricing(request): #pylint:disable=unused-argument
    return reverse('saas_cart_plan_list')

@register.filter()
def url_profile(request): #pylint:disable=unused-argument
    if base_is_authenticated(request):
        organization = attached_organization(request.user)
        if organization:
            return reverse('saas_organization_profile', args=(organization,))
        return reverse('users_profile', args=(request.user,))
    return None


@register.filter()
def url_login(request): #pylint:disable=unused-argument
    return reverse('login')

@register.filter()
def url_register(request): #pylint:disable=unused-argument
    return reverse('registration_register')
