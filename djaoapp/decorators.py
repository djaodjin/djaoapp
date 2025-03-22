# Copyright (c) 2023, DjaoDjin inc.
# see LICENSE
from __future__ import absolute_import
from __future__ import unicode_literals

import logging
from functools import wraps

from django.db.models import Q
from django.template.response import SimpleTemplateResponse
import jinja2.exceptions
from extended_templates.thread_locals import (
    enable_instrumentation, disable_instrumentation,
    get_edition_tools_context_data)
from saas.decorators import fail_authenticated as fail_authenticated_default
from saas.utils import get_role_model
from signup.helpers import has_invalid_password
from signup.models import Contact

from .compat import reverse, available_attrs
from .edition_tools import inject_edition_tools as _inject_edition_tools

# This logger is really only useful for 'rules' in debug mode.
LOGGER = logging.getLogger('rules')


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
            if isinstance(response, SimpleTemplateResponse):
                # We could use ``SingleTemplateResponse`` to catch both
                # django and restframework responses. Unfortunately
                # the content_type on restframework responses is set
                # very late (render), while at the same time django
                # defaults it to text/html until then.
                try:
                    response.render()
                except jinja2.exceptions.TemplateError as err:
                    response = SimpleTemplateResponse(
                        template="400.html",
                        context={'messages': [str(err)]},
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
                Q(email_verification_key=verification_key) |
                Q(phone_verification_key=verification_key)).first()
            if not contact:
                # Not a `Contact`, let's try `Role`.
                role_model = get_role_model()
                try:
                    role = role_model.objects.filter(
                        Q(grant_key=verification_key)
                        | Q(request_key=verification_key)).get()
                    contact, _ = Contact.objects.prepare_email_verification(
                        role.user.email, user=role.user)
                    verification_key = contact.email_verification_key
                except role_model.DoesNotExist:
                    pass
            if contact and has_invalid_password(contact.user):
                redirect = request.build_absolute_uri(
                    reverse('registration_activate',
                        args=(verification_key,)))
    return redirect
