# Copyright (c) 2025, DjaoDjin inc.
# see LICENSE

"""
Functions used to inject edition tools within an HTML response.
"""
import logging
from collections import namedtuple

from bs4 import BeautifulSoup
from django.conf import settings
from django.core.files.storage import get_storage_class
from django.template import loader
from extended_templates.compat import render_template
from extended_templates.models import get_show_edit_tools
from extended_templates.views.pages import (
    inject_edition_tools as inject_edition_tools_base)
from rules.utils import get_current_app
from saas.decorators import _valid_manager
from saas.models import get_broker, is_broker
from saas.templatetags.saas_tags import attached_organization
from saas.utils import get_role_model

from .compat import csrf, is_authenticated, reverse
from .api.serializers import PublicSessionSerializer


LOGGER = logging.getLogger(__name__)

TopAccessibleOrganization = namedtuple('TopAccessibleOrganization',
    ['slug', 'printable_name', 'settings_location', 'role_title',
     'app_location', 'org_picture'])


def fail_edit_perm(request, account=None):
    """
    Returns ``True`` if the request user does not have edit permissions.
    """
    result = True
    # The context processor will be called from the e-mail sender
    # which might not be associated to a request.
    if request is not None:
        if account is None:
            # The call to `get_current_app` here seems valid to check
            # if the user has permissions to edit pages under a path prefix.
            account = get_current_app(request).account
        result = not bool(_valid_manager(
            request.user if is_authenticated(request) else None,
            [account]))
    return result


def get_organization_picture(organization, default=None):
    picture = organization.get('picture')
    return picture if picture else default


def get_user_menu_context(user, context, request):
    #pylint:disable=too-many-locals
    path_parts = reversed(request.path.split('/')) if request else []
    has_broker_role = False
    active_organization = None

    user_profile_url = request.build_absolute_uri(
        reverse('users_profile', args=(user,)))
    organization = attached_organization(user)
    if organization:
        user_profile_url = request.build_absolute_uri(
            reverse('saas_organization_profile', args=(organization,)))

    nb_accessibles = 0
    top_accessibles = []
    accessibles = context.get('roles', [])
    nb_accessibles += len(accessibles)
    for role in accessibles:
        accessible = {}
        accessible.update(role['profile'])
        role_title = role['role_description']['title']
        profile_slug = role['profile']['slug']
        app_location = reverse('organization_app', args=(profile_slug,))
        settings_location = role['settings_url']
        accessible.update({
            'settings_location': settings_location,
            'app_location': app_location,
            'role_title': role_title
        })
        top_accessibles += [accessible]
        if profile_slug in path_parts:
            active_organization = accessible
        if is_broker(profile_slug):
            has_broker_role = True

    top_accessibles = top_accessibles[:settings.DYNAMIC_MENUBAR_ITEM_CUT_OFF]
    more_accessibles_url = (request.build_absolute_uri(
        reverse('saas_user_product_list', args=(user,))) if
        nb_accessibles > settings.DYNAMIC_MENUBAR_ITEM_CUT_OFF else None)

    if not active_organization and has_broker_role:
        active_organization = get_broker()

    context.update({
        'active_organization': active_organization,
        'top_accessibles': top_accessibles,
        'urls': {
            'user_profile': user_profile_url,
            'user_accessibles': more_accessibles_url
        }})
    return context


def inject_edition_tools(response, request, context=None,
                         body_top_template_name=None,
                         body_bottom_template_name=None):
    """
    If the ``request.user`` has editable permissions, this method
    injects the edition tools into the html *content* and return
    a BeautifulSoup object of the resulting content + tools.

    If the response is editable according to the proxy rules, this
    method returns a BeautifulSoup object of the content such that
    ``PageMixin`` inserts the edited page elements.
    """
    #pylint:disable=too-many-locals,too-many-nested-blocks,too-many-statements
    content_type = response.get('content-type', '')
    if not content_type.startswith('text/html'):
        return None

    if not is_authenticated(request):
        return None

    if context is None:
        context = {}

    # ``app.account`` is guarenteed to be in the same database as ``app``.
    # ``site.account`` is always in the *default* database, which is not
    # the expected database ``Organization`` are typically queried from.
    app = get_current_app(request)
    soup = None
    show_edit_tools = get_show_edit_tools(request)
    if show_edit_tools and not fail_edit_perm(request, account=app.account):
        edit_urls = {
            'api_medias': reverse(
                'extended_templates_api_uploaded_media_elements',
                kwargs={'path':''}),
            'api_sitecss': reverse(
                'extended_templates_api_edit_sitecss'),
            'api_less_overrides': reverse(
                'extended_templates_api_less_overrides'),
            'api_sources': reverse(
                'extended_templates_api_sources'),
            'api_page_element_base': reverse(
                'extended_templates_api_edit_template_base'),
            'api_plans': reverse('saas_api_plans', args=(app.account,)),
            'plan_update_base': reverse('saas_plan_base', args=(app.account,))}
        try:
            storage_class = get_storage_class()
            if storage_class.__name__.endswith('3Storage'):
                # Hacky way to test for `storages.backends.s3.S3Storage`
                # and `storages.backends.s3boto3.S3Boto3Storage`
                # without importing the optional package 'django-storages'.
                edit_urls.update({
                    'media_upload': reverse('api_credentials_organization')})
        except AttributeError:
            LOGGER.debug("doesn't look like we have a S3Storage.")
        body_bottom_template_name = \
            "extended_templates/_body_bottom_edit_tools.html"
        context.update({
            'ENABLE_CODE_EDITOR': show_edit_tools,
            'FEATURE_DEBUG': settings.FEATURES_DEBUG,
            'urls': {'edit': edit_urls}})
        context.update(csrf(request))
        soup = inject_edition_tools_base(response, request, context=context,
            body_top_template_name=body_top_template_name,
            body_bottom_template_name=body_bottom_template_name)

    # Insert the authenticated user information and roles on organization.
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
        auth_user = soup.body.find(attrs={'data-dj-menubar-user-item': True})
        user_menu_template = '_menubar.html'
        if auth_user and user_menu_template:
            request.user.roles = get_role_model().objects.valid_for(
                user=request.user).exclude(
                organization__slug=request.user.username).order_by(
                'role_description').select_related('role_description')
            serializer = PublicSessionSerializer(request.user, context={
                'request':request})
            cleaned_data = {}
            cleaned_data.update(serializer.data)
            cleaned_data = get_user_menu_context(
                request.user, cleaned_data, request)
            template = loader.get_template(user_menu_template)
            user_menu = render_template(template, cleaned_data, request).strip()
            # Removes 'data-dj-menubar-user-item' attribute
            # such that `djaodjin-menubar.js` does not attempt to reload
            # the dynamic menu item again when the browser parses the page.
            del auth_user.attrs['data-dj-menubar-user-item']
            auth_user.clear()
            els = BeautifulSoup(user_menu, 'html5lib').body.children
            for elem in els:
                auth_user.append(BeautifulSoup(str(elem), 'html5lib'))
    return soup
