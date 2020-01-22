# Copyright (c) 2020, DjaoDjin inc.
# see LICENSE
from __future__ import absolute_import
from __future__ import unicode_literals

import logging
from functools import wraps

from django.db import DEFAULT_DB_ALIAS
from django.db.models import Q
from django.template.response import TemplateResponse
from django.utils.decorators import available_attrs
import jinja2.exceptions
from multitier.thread_locals import get_current_site
from pages.locals import (enable_instrumentation, disable_instrumentation,
    get_edition_tools_context_data)
from rules.perms import NoRuleMatch, check_matched
from rules.utils import get_current_app
from saas.decorators import (_has_valid_access,
    fail_authenticated as fail_authenticated_default,
    fail_direct as fail_direct_default,
    fail_provider as fail_provider_default,
    fail_provider_only as fail_provider_only_default,
    fail_self_provider as fail_self_provider_default)
from saas.models import RoleDescription
from saas.utils import get_organization_model, get_role_model
from signup.models import Contact
from signup.utils import has_invalid_password
from signup.decorators import fail_verified_email

from .compat import reverse
from .thread_locals import get_current_broker
from .edition_tools import inject_edition_tools as _inject_edition_tools

# This logger is really only useful for 'rules' in debug mode.
LOGGER = logging.getLogger('rules')

DEFAULT_PREFIXES = [
    '/api/accounts/', '/api/auth/', '/api/billing/', '/api/metrics/',
    '/api/profile/', '/api/themes', '/api/users/',
    '/billing/', '/metrics/', '/profile/', '/users/']


def inject_edition_tools(function=None):
    """
    Inject the edition tools into the HTML response.
    """
    def decorator(view_func):
        @wraps(view_func, assigned=available_attrs(view_func))
        def _wrapped_view(request, *args, **kwargs):
            enable_instrumentation()
            response = view_func(request, *args, **kwargs)
            disable_instrumentation()
            if isinstance(response, TemplateResponse):
                # We could use ``SingleTemplateResponse`` to catch both
                # django and restframework responses. Unfortunately
                # the content_type on restframework responses is set
                # very late (render), while at the same time django
                # defaults it to text/html until then.
                try:
                    response.render()
                except jinja2.exceptions.TemplateError as err:
                    response = TemplateResponse(
                        request=request,
                        template="400.html",
                        context={'messages': [str(err)]},
#                        using=view_func.template_engine,
                        status=400)
                    response.render()
                soup = _inject_edition_tools(response, request,
                    context=get_edition_tools_context_data())
                if soup:
                    # str(soup) instead of soup.prettify() to avoid
                    # trailing whitespace on a reformatted HTML textarea
                    response.content = str(soup)
            return response
        return _wrapped_view

    if function:
        return decorator(function)
    return decorator


def fail_active_roles(request):
    """
    User with active roles only
    """
    role_model = get_role_model()
    if not role_model.objects.filter(user=request.user).exists():
        # Find an organization with a matching e-mail domain.
        domain = request.user.email.split('@')[-1].lower()
        organization_model = get_organization_model()
        try:
            organization = organization_model.objects.filter(
                email__endswith=domain).get()
            # Find a RoleDescription we can implicitely grant to the user.
            try:
                role_descr = RoleDescription.objects.filter(
                    Q(organization__isnull=True) | Q(organization=organization),
                    implicit_create_on_none=True).get()
                # Create a granted role implicitely, but only if the e-mail
                # was verified.
                redirect_to = fail_verified_email(request)
                if redirect_to:
                    return redirect_to
                organization.add_role(request.user, role_descr,
                    request_user=request.user)
            except role_model.DoesNotExist:
                LOGGER.debug("'%s' does not have a role on any profile but"
                    " we cannot grant one implicitely because there is"
                    " no role description that permits it.",
                    request.user)
            except role_model.MultipleObjectsReturned:
                LOGGER.debug("'%s' does not have a role on any profile but"
                    " we cannot grant one implicitely because we have"
                    " multiple role description that permits it. Ambiguous.",
                    request.user)
        except organization_model.DoesNotExist:
            LOGGER.debug("'%s' does not have a role on any profile but"
                " we cannot grant one implicitely because there is"
                " no profiles with @%s e-mail domain.",
                request.user, domain)
        except organization_model.MultipleObjectsReturned:
            LOGGER.debug("'%s' does not have a role on any profile but"
                " we cannot grant one implicitely because @%s is"
                " ambiguous. Multiple profiles share that email domain.",
                request.user, domain)

    if role_model.objects.filter(
            user=request.user, grant_key__isnull=False).exists():
        # We have some invites pending so let's first stop
        # by the user accessibles page.
        redirect_to = reverse('saas_user_product_list', args=(request.user,))
        if request.path != redirect_to:
            # Prevents URL redirect loops
            return redirect_to

    return False


def fail_authenticated(request, verification_key=None):
    """
    Decorator for views that checks that the user is authenticated.

    ``django.contrib.auth.decorators.login_required`` will automatically
    redirect to the login page. We wante to redirect to the activation
    page when required, as well as raise a ``PermissionDenied``
    instead when Content-Type is showing we are dealing with an API request.
    """
    redirect = fail_authenticated_default(request)
    if redirect:
        if verification_key:
            contact = Contact.objects.filter(
                verification_key=verification_key).first()
            if not contact:
                # Not a `Contact`, let's try `Role`.
                role_model = get_role_model()
                try:
                    role = role_model.objects.filter(
                        Q(grant_key=verification_key)
                        | Q(request_key=verification_key)).get()
                    contact, _ = Contact.objects.update_or_create_token(
                        role.user)
                    verification_key = contact.verification_key
                except role_model.DoesNotExist:
                    pass
            if contact and has_invalid_password(contact.user):
                redirect = request.build_absolute_uri(
                    reverse('registration_activate',
                        args=(verification_key,)))
    return redirect


def fail_direct(request, organization=None, roledescription=None):
    try:
        app = get_current_app()
        #pylint:disable=unused-variable
        redirect, matched, session = check_matched(request, app,
            prefixes=DEFAULT_PREFIXES)
    except NoRuleMatch:
        redirect = fail_direct_default(request, organization=organization,
                roledescription=roledescription)
    return redirect


def fail_provider(request, organization=None, roledescription=None):
    """
    Same decorator as saas.requires_provider with the added permissions
    that managers of the site database itself are also able to access
    profiles of registered yet unsubscribed ``Organization``.
    """
    site = get_current_site()
    if site.db_name and site.db_name != DEFAULT_DB_ALIAS:
        # We have a separate database so it is OK for a manager
        # of the site to access registered ``Organization`` which
        # are not subscribed yet.
        if _has_valid_access(request, [get_current_broker()]):
            return False
    try:
        app = get_current_app()
        #pylint:disable=unused-variable
        redirect, matched, session = check_matched(request, app,
            prefixes=DEFAULT_PREFIXES)
    except NoRuleMatch:
        # By default, we are looking for provider.
        redirect = fail_provider_default(request,
            organization=organization, roledescription=roledescription)
    return redirect



def fail_provider_only(request, organization=None, roledescription=None):
    """
    Same decorator as saas.requires_provider with the added permissions
    that managers of the site database itself are also able to access
    profiles of registered yet unsubscribed ``Organization``.
    """
    site = get_current_site()
    if site.db_name and site.db_name != DEFAULT_DB_ALIAS:
        # We have a separate database so it is OK for a manager
        # of the site to access registered ``Organization`` which
        # are not subscribed yet.
        if _has_valid_access(request, [get_current_broker()]):
            return False
    try:
        app = get_current_app()
        #pylint:disable=unused-variable
        redirect, matched, session = check_matched(request, app,
            prefixes=DEFAULT_PREFIXES)
    except NoRuleMatch:
        # By default, we are looking for provider.
        redirect = fail_provider_only_default(request,
            organization=organization, roledescription=roledescription)
    return redirect


def fail_self_provider(request, user=None, roledescription=None):
    """
    Same decorator as saas.requires_self_provider with the added permissions
    that managers of the site database itself are also able to access
    profiles of registered yet unsubscribed ``Organization``.
    """
    site = get_current_site()
    if site.db_name and site.db_name != DEFAULT_DB_ALIAS:
        # We have a separate database so it is OK for a manager
        # of the site to access registered ``Organization`` which
        # are not subscribed yet.
        if _has_valid_access(request, [get_current_broker()]):
            return False
    try:
        app = get_current_app()
        #pylint:disable=unused-variable
        redirect, matched, session = check_matched(request, app,
            prefixes=DEFAULT_PREFIXES)
    except NoRuleMatch:
        # By default, we are looking for provider.
        redirect = fail_self_provider_default(request,
            user=user, roledescription=roledescription)
    return redirect
