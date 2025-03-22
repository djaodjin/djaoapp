# Copyright (c) 2025, DjaoDjin inc.
# see LICENSE

from rules.urldecorators import re_path
from saas.decorators import (fail_active_roles, fail_agreement, fail_direct,
    fail_provider, fail_provider_only, fail_self_provider)
from saas.settings import PROFILE_URL_KWARG, SLUG_RE
from signup.decorators import fail_active

from .decorators import fail_authenticated, inject_edition_tools


def url_prefixed(regex, view, name=None):
    """
    Returns a urlpattern for public pages.
    """
    return re_path(regex, view, name=name, decorators=[inject_edition_tools])


def url_authenticated(regex, view, name=None):
    """
    Returns a urlpattern accessible to an authenticated user.
    """
    return re_path(regex % {
            PROFILE_URL_KWARG: r'(?P<%s>%s)' % (PROFILE_URL_KWARG, SLUG_RE)},
        view, name=name,
        redirects=[
            fail_authenticated
        ], decorators=[inject_edition_tools])


def url_agreement(regex, view, name=None):
    """
    Returns a urlpattern accessible to a user that signed the terms-of-use.
    """
    return re_path(regex % {
            PROFILE_URL_KWARG: r'(?P<%s>%s)' % (PROFILE_URL_KWARG, SLUG_RE)},
        view, name=name,
        redirects=[
            fail_authenticated,
            fail_agreement
        ], decorators=[inject_edition_tools])


def url_active(regex, view, name=None):
    """
    Returns a urlpattern accessible to an active user.
    """
    return re_path(regex % {
            PROFILE_URL_KWARG: r'(?P<%s>%s)' % (PROFILE_URL_KWARG, SLUG_RE)},
        view, name=name,
        redirects=[
            fail_authenticated,
            fail_active,
            fail_agreement
        ], decorators=[inject_edition_tools])


def url_direct(regex, view, name=None):
    """
    Builds URLs for a direct decorator.
    """
    return re_path(regex % {
            PROFILE_URL_KWARG: r'(?P<%s>%s)' % (PROFILE_URL_KWARG, SLUG_RE)},
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
    return re_path(regex % {
            PROFILE_URL_KWARG: r'(?P<%s>%s)' % (PROFILE_URL_KWARG, SLUG_RE)},
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
    return re_path(regex % {
            "app": r'(?P<app>%s)' % SLUG_RE},
               view, name=name,
               redirects=[
                   fail_authenticated,
                   fail_active,
                   fail_agreement,
                   fail_active_roles,
                   fail_direct
               ], decorators=[inject_edition_tools])


def url_provider(regex, view, name=None):
    """
    Direct managers for the organization and managers for a provider
    of a plan the organization is subscribed to have permission
    to access the urlpattern built from *regex*.
    """
    return re_path(regex % {
            PROFILE_URL_KWARG: r'(?P<%s>%s)' % (PROFILE_URL_KWARG, SLUG_RE)},
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
    return re_path(regex % {
            PROFILE_URL_KWARG: r'(?P<%s>%s)' % (PROFILE_URL_KWARG, SLUG_RE)},
               view, name=name,
               redirects=[
                   fail_authenticated,
                   fail_provider
               ], decorators=[inject_edition_tools])


def url_provider_only(regex, view, name=None):
    """
    Builds URLs for a provider-only decorator.
    """
    return re_path(regex % {
            PROFILE_URL_KWARG: r'(?P<%s>%s)' % (PROFILE_URL_KWARG, SLUG_RE)},
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
    return re_path(regex % {
            "user": r'(?P<user>%s)' % SLUG_RE},
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
    return re_path(regex % {
            "user": r'(?P<user>%s)' % SLUG_RE},
               view, name=name,
               redirects=[
                   fail_authenticated,
                   fail_self_provider
               ], decorators=[inject_edition_tools])


# XXX might be deprecated
def url_dashboard_iframe(regex, view, name=None):
    """
    Same as ``url_dashboard``, but without inject_edition_tools.
    Used in notifications template iframe
    """
    return re_path(regex % {
            "app": r'(?P<app>%s)' % SLUG_RE},
               view, name=name,
               redirects=[
                   fail_authenticated,
                   fail_active,
                   fail_agreement,
                   fail_active_roles,
                   fail_direct
               ])
