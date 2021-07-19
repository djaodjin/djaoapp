# Copyright (c) 2021, DjaoDjin inc.
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
from django.utils.module_loading import import_string
from multitier.thread_locals import get_current_site
from multitier.mixins import build_absolute_uri
from pages.compat import render_template
from pages.views.pages import inject_edition_tools as pages_inject_edition_tools
from rules import settings as rules_settings
from rules.utils import get_current_app
from saas import settings as saas_settings
from saas.decorators import _valid_manager
from saas.models import get_broker, is_broker
from saas.utils import get_organization_model, get_role_model

from .compat import csrf, is_authenticated, reverse, six
from .thread_locals import is_domain_site


LOGGER = logging.getLogger(__name__)

TopAccessibleOrganization = namedtuple('TopAccessibleOrganization',
    ['slug', 'printable_name', 'settings_location', 'role_title',
     'app_location'])

def djaoapp_urls(request, account=None, base=None):
    if account is None:
        account = get_current_app().account
    urls = {
        'pricing': build_absolute_uri(request, location='/pricing/',
            site=settings.APP_NAME),
        'cart': build_absolute_uri(request,
            location='/billing/%s/cart/' % account,
            site=settings.APP_NAME)}
    if base:
        urls.update({'app':
            build_absolute_uri(request, location='/app/%s/' % base,
            site="%s-master" % settings.DB_NAME)}) # XXX Hack for correct domain
    return urls


def fail_edit_perm(request, account=None):
    """
    Returns ``True`` if the request user does not have edit permissions.
    """
    result = True
    # The context processor will be called from the e-mail sender
    # which might not be associated to a request.
    if request is not None:
        if account is None:
            account = get_current_app().account
        result = not bool(_valid_manager(request, [account]))
    return result


def has_bank_account(broker):
    return ((broker.slug == settings.APP_NAME and
             saas_settings.PROCESSOR.get('PUB_KEY') and
             saas_settings.PROCESSOR.get('PRIV_KEY'))
            or broker.has_bank_account)


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
    app = get_current_app()
    provider = app.account
    soup = None
    if app.show_edit_tools and get_role_model().objects.valid_for(
            organization=provider, user=request.user):
        edit_urls = {
            'api_medias': reverse(
                'uploaded_media_elements', kwargs={'path':''}),
            'api_sitecss': reverse('edit_sitecss'),
            'api_less_overrides': reverse('pages_api_less_overrides'),
            'api_sources': reverse('pages_api_sources'),
            'api_page_element_base': reverse('pages_api_edit_template_base'),
            'api_plans': reverse('saas_api_plans', args=(provider,)),
            'plan_update_base': reverse('saas_plan_base', args=(provider,))}
        try:
            # The following statement will raise an Exception
            # when we are dealing with a ``FileSystemStorage``.
            _ = get_storage_class().bucket_name
            edit_urls.update({
                'media_upload': reverse('api_credentials_organization')})
        except AttributeError:
            LOGGER.debug("doesn't look like we have a S3Storage.")
        # XXX sites which are hosted on a same domain shouldn't disable
        # all edit functionality, just the edition of base templates.
        site = get_current_site()
        enable_code_editor = is_domain_site(site)
        if enable_code_editor:
            dj_urls = djaoapp_urls(
                request, account=provider, base=site.as_base())
            body_bottom_template_name = "pages/_body_bottom_edit_tools.html"
        else:
            dj_urls = djaoapp_urls(request, account=provider)
            body_bottom_template_name = "pages/_body_bottom.html"

        context.update({
            'ENABLE_CODE_EDITOR': enable_code_editor,
            'FEATURE_DEBUG': settings.FEATURES_DEBUG,
            'urls':{
                'djaodjin': dj_urls,
                'edit': edit_urls}})
        context.update(csrf(request))
        soup = pages_inject_edition_tools(response, request, context=context,
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
        auth_user = soup.body.find(class_='header-menubar')
        user_menu_template = '_menubar.html'
        if auth_user and user_menu_template:
            serializer_class = import_string(rules_settings.SESSION_SERIALIZER)
            serializer = serializer_class(request)
            path_parts = reversed(request.path.split('/'))
            top_accessibles = []
            has_broker_role = False
            active_organization = None

            # Loads Organization models from database because we need
            # the `is_provider` flag.
            slugs = set([])
            for organization_list in six.itervalues(
                    serializer.data.get('roles', {})):
                for organization_dict in organization_list:
                    slugs.add(organization_dict.get('slug'))
            organizations = {}
            for organization in get_organization_model().objects.filter(
                    slug__in=slugs): # XXX Remove query.
                organizations[organization.slug] = organization

            for role, organization_list in six.iteritems(
                    serializer.data['roles']):
                for organization in organization_list:
                    if organization['slug'] == request.user.username:
                        # Personal Organization
                        continue
                    db_obj = organizations[organization['slug']]
                    if db_obj.is_provider:
                        settings_location = reverse('saas_dashboard',
                            args=(organization['slug'],))
                    else:
                        settings_location = reverse(
                            'saas_organization_profile',
                            args=(organization['slug'],))
                    app_location = reverse('organization_app',
                        args=(organization['slug'],))

                    if organization['slug'] in path_parts:
                        active_organization = TopAccessibleOrganization(
                            organization['slug'],
                            organization['printable_name'],
                            settings_location, role, app_location)
                    if is_broker(organization['slug']):
                        has_broker_role = True
                    top_accessibles += [TopAccessibleOrganization(
                        organization['slug'],
                        organization['printable_name'],
                        settings_location, role, app_location)]
            if not active_organization and has_broker_role:
                active_organization = get_broker()
            context.update({'active_organization':active_organization})
            context.update({'top_accessibles': top_accessibles})
            template = loader.get_template(user_menu_template)
            user_menu = render_template(template, context, request).strip()
            auth_user.clear()
            els = BeautifulSoup(user_menu, 'html5lib').body.ul.children
            for elem in els:
                auth_user.append(BeautifulSoup(str(elem), 'html5lib'))

    return soup
