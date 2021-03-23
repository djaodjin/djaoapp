# Copyright (c) 2020, DjaoDjin inc.
# see LICENSE

from rules.urldecorators import url
from saas.decorators import fail_agreement
from saas.settings import ACCT_REGEX
from signup.decorators import fail_active

from .decorators import (fail_active_roles, fail_authenticated,
    fail_direct, fail_provider, fail_provider_only, fail_self_provider,
    inject_edition_tools)


def url_prefixed(regex, view, name=None):
    """
    Returns a urlpattern for public pages.
    """
    return url(regex, view, name=name, decorators=[inject_edition_tools])


def url_authenticated(regex, view, name=None):
    """
    Returns a urlpattern accessible to an authenticated user.
    """
    return url(regex % {
            "organization": r'(?P<organization>%s)' % ACCT_REGEX},
        view, name=name,
        redirects=[
            fail_authenticated
        ], decorators=[inject_edition_tools])


def url_active(regex, view, name=None):
    """
    Returns a urlpattern accessible to an active user.
    """
    return url(regex % {
            "organization": r'(?P<organization>%s)' % ACCT_REGEX},
        view, name=name,
        redirects=[
            fail_authenticated,
            fail_active,
            fail_agreement
        ])


def url_direct(regex, view, name=None):
    """
    Builds URLs for a direct decorator.
    """
    return url(regex % {
            "organization": r'(?P<organization>%s)' % ACCT_REGEX},
               view, name=name,
               redirects=[
                   fail_authenticated,
                   fail_active,
                   fail_agreement,
                   fail_active_roles,
                   fail_direct
               ], decorators=[inject_edition_tools])


def url_frictionless_direct(regex, view, name=None):
    """
    Builds URLs for a direct decorator that does not require
    an activated account.
    """
    return url(regex % {
            "organization": r'(?P<organization>%s)' % ACCT_REGEX},
               view, name=name,
               redirects=[
                   fail_authenticated,
                   fail_direct
               ], decorators=[inject_edition_tools])


def url_dashboard(regex, view, name=None):
    """
    Same as ``url_direct``, yet override template loader behavior
    to force use of default templates. This is used for managers
    dashboard functionality, hence the name ``url_dashboard``.
    """
    return url(regex % {
            "app": r'(?P<app>%s)' % ACCT_REGEX},
               view, name=name,
               redirects=[
                   fail_authenticated,
                   fail_active,
                   fail_agreement,
                   fail_active_roles,
                   fail_direct
               ], decorators=[inject_edition_tools])


def url_dashboard_iframe(regex, view, name=None):
    """
    Same as ``url_dashboard``, but without inject_edition_tools.
    Used in notifications template iframe
    """
    return url(regex % {
            "app": r'(?P<app>%s)' % ACCT_REGEX},
               view, name=name,
               redirects=[
                   fail_authenticated,
                   fail_active,
                   fail_agreement,
                   fail_active_roles,
                   fail_direct
               ])


def url_provider(regex, view, name=None):
    """
    Direct managers for the organization and managers for a provider
    of a plan the organization is subscribed to have permission
    to access the urlpattern built from *regex*.
    """
    return url(regex % {
            "organization": r'(?P<organization>%s)' % ACCT_REGEX},
               view, name=name,
               redirects=[
                   fail_authenticated,
                   fail_active,
                   fail_agreement,
                   fail_active_roles,
                   fail_provider
               ], decorators=[inject_edition_tools])


def url_frictionless_provider(regex, view, name=None):
    """
    Direct managers for the organization and managers for a provider
    of a plan the organization is subscribed to have permission
    to access the urlpattern built from *regex*.

    The request user is not require to have activated their account yet.
    """
    return url(regex % {
            "organization": r'(?P<organization>%s)' % ACCT_REGEX},
               view, name=name,
               redirects=[
                   fail_authenticated,
                   fail_provider
               ], decorators=[inject_edition_tools])


def url_provider_only(regex, view, name=None):
    """
    Builds URLs for a provider-only decorator.
    """
    return url(regex % {
            "organization": r'(?P<organization>%s)' % ACCT_REGEX},
               view, name=name,
               redirects=[
                   fail_authenticated,
                   fail_active,
                   fail_agreement,
                   fail_active_roles,
                   fail_provider_only
               ], decorators=[inject_edition_tools])


def url_self_provider(regex, view, name=None):
    """
    The User authenticated by the request or a direct manager
    for an organization managed in common or a provider
    of a plan an organization managed in common is subscribed to,
    have permission to access the urlpattern built from *regex*.
    """
    return url(regex % {
            "user": r'(?P<user>%s)' % ACCT_REGEX},
               view, name=name,
               redirects=[
                   fail_authenticated,
                   fail_active,
                   fail_agreement,
                   fail_self_provider
               ], decorators=[inject_edition_tools])


def url_frictionless_self_provider(regex, view, name=None):
    """
    This set of decorators is a little more relaxed than ``url_self_provider``.
    It will also let user (self) which have not activated their account through.
    """
    return url(regex % {
            "user": r'(?P<user>%s)' % ACCT_REGEX},
               view, name=name,
               redirects=[
                   fail_authenticated,
                   fail_self_provider
               ], decorators=[inject_edition_tools])
