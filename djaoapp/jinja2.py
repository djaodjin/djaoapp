# Copyright (c) 2018, DjaoDjin inc.
# see LICENSE

from __future__ import absolute_import

from django.conf import settings
import django.template.defaulttags
from django_assets.env import get_env
from deployutils.apps.django.management.commands import get_template_search_path
from deployutils.apps.django.templatetags import deployutils_extratags
from jinja2.sandbox import SandboxedEnvironment as Jinja2Environment
import multitier.templatetags.multitier_tags
from pages import signals as pages_signals
import saas.templatetags.saas_tags
from webassets.ext.jinja2 import AssetsExtension

from .compat import import_string, reverse
import djaoapp.assets
import djaoapp.templatetags.djaoapp_tags


class DjaoappEnvironment(Jinja2Environment):

    def get_template(self, name, parent=None, globals=None):
        #pylint:disable=redefined-builtin
        template = super(DjaoappEnvironment, self).get_template(
            name, parent=parent, globals=globals)
        pages_signals.template_loaded.send(sender=self, template=template)
        return template


def environment(**options):
    from django.contrib.auth import get_user_model
    from signup.models import ActivatedUserManager

    # Hack to install our create_user method.
    user_class = get_user_model()
    user_class.objects = ActivatedUserManager()
    user_class.objects.model = user_class

    assets_env = get_env()
    # If we don't force ``auto_reload`` to True, in DEBUG=0, the templates
    # would only be compiled on the first edit.
    options.update({'auto_reload': True})
    if 'loader' in options:
        options['loader'] = import_string(options['loader'])(
            get_template_search_path())
    env = DjaoappEnvironment(extensions=[AssetsExtension], **options)
    # Generic filters to render pages
    env.filters['host'] = deployutils_extratags.host
    env.filters['iterfields'] = djaoapp.templatetags.djaoapp_tags.iterfields
    env.filters['is_checkbox'] = djaoapp.templatetags.djaoapp_tags.is_checkbox
    env.filters['is_radio'] = djaoapp.templatetags.djaoapp_tags.is_radio
    env.filters['is_textarea'] = djaoapp.templatetags.djaoapp_tags.is_textarea
    env.filters['site_prefixed'] = \
        multitier.templatetags.multitier_tags.site_prefixed
    env.filters['asset'] = multitier.templatetags.multitier_tags.asset
    env.filters['absolute_uri'] = \
        multitier.templatetags.multitier_tags.absolute_uri
    env.filters['djasset'] = djaoapp.templatetags.djaoapp_tags.djasset
    env.filters['messages'] = djaoapp.templatetags.djaoapp_tags.messages
    env.filters['is_authenticated'] = \
        djaoapp.templatetags.djaoapp_tags.is_authenticated
    env.filters['pluralize'] = djaoapp.templatetags.djaoapp_tags.pluralize
    env.filters['no_cache'] = djaoapp.templatetags.djaoapp_tags.no_cache

    # Standard site pages
    env.filters['site_printable_name'] = \
        djaoapp.templatetags.djaoapp_tags.site_printable_name
    env.filters['url_app'] = djaoapp.templatetags.djaoapp_tags.url_app
    env.filters['url_contact'] = djaoapp.templatetags.djaoapp_tags.url_contact
    env.filters['url_home'] = djaoapp.templatetags.djaoapp_tags.url_home
    env.filters['url_login'] = djaoapp.templatetags.djaoapp_tags.url_login
    env.filters['url_logout'] = djaoapp.templatetags.djaoapp_tags.url_logout
    env.filters['url_pricing'] = djaoapp.templatetags.djaoapp_tags.url_pricing
    env.filters['url_profile'] = djaoapp.templatetags.djaoapp_tags.url_profile
    env.filters['url_register'] \
        = djaoapp.templatetags.djaoapp_tags.url_register
    # Specific to SaaS
    env.filters['isoformat'] = saas.templatetags.saas_tags.isoformat
    env.filters['short_date'] = saas.templatetags.saas_tags.short_date
    env.filters['humanize_money'] = saas.templatetags.saas_tags.humanize_money
    env.filters['humanize_period'] = saas.templatetags.saas_tags.humanize_period
    env.filters['date_in_future'] = saas.templatetags.saas_tags.date_in_future
    env.filters['md'] = saas.templatetags.saas_tags.md
    env.filters['describe'] = saas.templatetags.saas_tags.describe

    if settings.DEBUG:
        env.filters['addslashes'] = django.template.defaultfilters.addslashes
        env.globals.update({
            'FEATURES_DEBUG': settings.FEATURES_DEBUG,
            'url': reverse,
            'cycle': django.template.defaulttags.cycle
        })
    env.assets_environment = assets_env
    return env
