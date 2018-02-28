# Copyright (c) 2018, DjaoDjin inc.
# see LICENSE

from django.core.urlresolvers import reverse
from django.utils import six
from pages.locals import get_edition_tools_context_data
from rules.utils import get_current_app
from saas.decorators import fail_direct
from saas.models import Plan

from .edition_tools import fail_edit_perm, inject_edition_tools


class DjaoAppMixin(object):
    """
    Adds URL for next step in the wizard.
    """

    def add_edition_tools(self, response, context=None):
        """
        If the ``request.user`` has editable permissions, this method
        injects the edition tools into the html *content* and return
        a BeautifulSoup object of the resulting content + tools.

        If the response is editable according to the proxy rules, this
        method returns a BeautifulSoup object of the content such that
        ``PageMixin`` inserts the edited page elements.
        """
        if context is None:
            context = {}
        context.update(get_edition_tools_context_data())
        return inject_edition_tools(
            response, request=self.request, context=context)

    @property
    def edit_perm(self):
        if not hasattr(self, '_edit_perm'):
            self._edit_perm = not fail_edit_perm(self.request)
        return self._edit_perm

    def get_context_data(self, **kwargs):
        context = super(DjaoAppMixin, self).get_context_data(**kwargs)
        context.update({'edit_perm': self.edit_perm}) # XXX generic_navbar.html
        if self.organization:
            if not Plan.objects.filter(
                    organization=self.organization).exists():
                context.update({'next_url': reverse('saas_cart_plan_list')})
        # URLs for user
        if self.request.user.is_authenticated():
            urls = {'user': {
                'logout': reverse('logout'),
                'profile': reverse('users_profile', args=(self.request.user,)),
            }}
        else:
            urls = {'user': {
               'login': reverse('login'),
               'login_github': reverse('social:begin', args=('github',)),
               'login_google': reverse('social:begin', args=('google-oauth2',)),
               'login_twitter': reverse('social:begin', args=('twitter',)),
               'password_reset': reverse('password_reset'),
               'register': reverse('registration_register'),
            }}
        # URLs for provider
        app = get_current_app()
        # ``app.account`` is guarenteed to be in the same database as ``app``.
        # ``site.account`` is always in the *default* database, which is not
        # the expected database ``Organization`` are typically queried from.
        provider = app.account
        if not fail_direct(self.request, organization=provider):
            urls.update({'provider': {
                'dashboard': reverse('saas_dashboard', args=(provider,)),
            }})
        if 'urls' in context:
            for key, val in six.iteritems(urls):
                if key in context['urls']:
                    context['urls'][key].update(val)
                else:
                    context['urls'].update({key: val})
        else:
            context.update({'urls': urls})
        return context
