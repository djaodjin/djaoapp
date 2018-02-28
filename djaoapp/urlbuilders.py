# Copyright (c) 2018, DjaoDjin inc.
# see LICENSE

from urldecorators import url
from saas.settings import ACCT_REGEX

def url_prefixed(regex, view, name=None):
    """
    Returns a urlpattern for public pages.
    """
    return url(regex, view, name=name,
        decorators=['djaoapp.decorators.inject_edition_tools'
        ])


def url_authenticated(regex, view, name=None):
    """
    Returns a urlpattern accessible to an authenticated user.
    """
    return url(regex % {
            "organization": r'(?P<organization>%s)' % ACCT_REGEX},
        view, name=name,
        decorators=['saas.decorators.requires_authenticated',
                    'djaoapp.decorators.inject_edition_tools'])


def url_active(regex, view, name=None):
    """
    Returns a urlpattern accessible to an active user.
    """
    return url(regex % {
            "organization": r'(?P<organization>%s)' % ACCT_REGEX},
        view, name=name,
        decorators=['saas.decorators.requires_authenticated',
                    'signup.decorators.active_required',
                    'saas.decorators.requires_agreement',
                    'djaoapp.decorators.inject_edition_tools'
        ])


def url_direct(regex, view, name=None):
    """
    Builds URLs for a direct decorator.
    """
    return url(regex % {
            "organization": r'(?P<organization>%s)' % ACCT_REGEX},
               view, name=name,
               decorators=['saas.decorators.requires_authenticated',
                           'signup.decorators.active_required',
                           'saas.decorators.requires_agreement',
                           'djaoapp.decorators.requires_direct',
                           'djaoapp.decorators.inject_edition_tools'
               ])


def url_dashboard(regex, view, name=None):
    """
    Same as ``url_direct``, yet override template loader behavior
    to force use of default templates. This is used for managers
    dashboard functionality, hence the name ``url_dashboard``.
    """
    return url(regex % {
            "app": r'(?P<app>%s)' % ACCT_REGEX},
               view, name=name,
               decorators=['saas.decorators.requires_authenticated',
                           'signup.decorators.active_required',
                           'saas.decorators.requires_agreement',
                           'djaoapp.decorators.requires_direct',
                           'djaoapp.decorators.inject_edition_tools'
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
               decorators=['saas.decorators.requires_authenticated',
                           'signup.decorators.active_required',
                           'saas.decorators.requires_agreement',
                           'djaoapp.decorators.requires_provider',
                           'djaoapp.decorators.inject_edition_tools'
               ])


def url_provider_only(regex, view, name=None):
    """
    Builds URLs for a provider-only decorator.
    """
    return url(regex % {
            "organization": r'(?P<organization>%s)' % ACCT_REGEX},
               view, name=name,
               decorators=['saas.decorators.requires_authenticated',
                           'signup.decorators.active_required',
                           'saas.decorators.requires_agreement',
                           'djaoapp.decorators.requires_provider_only',
                           'djaoapp.decorators.inject_edition_tools'
               ])


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
               decorators=['saas.decorators.requires_authenticated',
                           'signup.decorators.active_required',
                           'saas.decorators.requires_agreement',
                           'djaoapp.decorators.requires_self_provider',
                           'djaoapp.decorators.inject_edition_tools'
               ])


def url_frictionless_self_provider(regex, view, name=None):
    """
    This set of decorators is a little more relaxed than ``url_self_provider``.
    It will also let user (self) which have not activated their account through.
    """
    return url(regex % {
            "user": r'(?P<user>%s)' % ACCT_REGEX},
               view, name=name,
               decorators=['saas.decorators.requires_authenticated',
                           'djaoapp.decorators.requires_self_provider',
                           'djaoapp.decorators.inject_edition_tools'
               ])
