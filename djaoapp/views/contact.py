# Copyright (c) 2023, DjaoDjin inc.
# see LICENSE
from __future__ import unicode_literals

import logging, re, socket
from smtplib import SMTPException

from captcha.fields import ReCaptchaField
from captcha.widgets import ReCaptchaV2Checkbox
from deployutils.apps.django.compat import is_authenticated
from django import forms, http
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.views.generic import FormView
from rest_framework import serializers
from rules.utils import get_current_app
from saas.mixins import ProviderMixin
from saas.models import Organization
from saas.utils import full_name_natural_split, update_context_urls
from signup.auth import validate_redirect

from ..compat import gettext_lazy as _, reverse, six
from ..signals import contact_requested
from ..validators import validate_contact_form


LOGGER = logging.getLogger(__name__)


def validate_path_pattern(request):
    # The authentication URLs are anonymously accessible, hence
    # prime candidates for bots. These will POST to '/login/.' for
    # example because there is a `action="."` in the <form> tag
    # in login.html.
    # We cannot catch these by restricting the match pattern.
    # 1. '^login/$' will not match 'login/.' hence trigger the catch
    #    all pattern that might forward the HTTP request.
    # 2. 'login/(?P<extra>.*)' will through a missing argument
    #    exception in `reverse` calls.
    #pylint:disable=too-many-locals
    try:
        pat = (r'(?P<expected_path>%s)(?P<extra>.*)' %
            request.resolver_match.route)
        look = re.match(pat, request.path.lstrip('/'))
        if look:
            extra =  look.group('extra')
            if extra:
                raise serializers.ValidationError(
                    {'detail': _("Bot detection - incorrect inputs")})
    except AttributeError:
        pass # Django<=1.11 ResolverMatch does not have
             # a route attribute.


class ContactForm(forms.Form):

    provider = forms.CharField(
        widget=forms.HiddenInput(), required=False)
    full_name = forms.CharField(
        widget=forms.TextInput({'class':'form-control'}))
    email = forms.EmailField(
        widget=forms.TextInput({'class':'form-control'}))
    message = forms.CharField(required=False,
        widget=forms.Textarea(attrs={
            'class':'form-control', 'placeholder': ""}))

    def __init__(self, *args, **kwargs):
        super(ContactForm, self).__init__(*args, **kwargs)
        if not kwargs.get('initial', {}).get('email', None):
            if getattr(get_current_app(), 'contact_requires_recaptcha', False):
                self.fields['captcha'] = ReCaptchaField(
                    widget=ReCaptchaV2Checkbox(
                        attrs={
                            'data-theme': 'clean',
                            'data-size': 'compact',
                        }))

    def clean(self):
        try:
            validate_contact_form(
                self.cleaned_data.get('full_name'),
                self.cleaned_data.get('email'),
                self.cleaned_data.get('message'))
        except serializers.ValidationError as err:
            raise ValidationError(str(err))


class ContactView(ProviderMixin, FormView):

    form_class = ContactForm
    template_name = 'contact.html'

    def dispatch(self, request, *args, **kwargs):
        # First level for bot prevention
        validate_path_pattern(self.request)
        return super(ContactView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ContactView, self).get_context_data(**kwargs)
        update_context_urls(context, {
            'api_contact_us': reverse('api_contact_us')
        })
        return context

    def get_initial(self):
        kwargs = super(ContactView, self).get_initial()
        if is_authenticated(self.request):
            kwargs.update({
                'email': self.request.user.email,
                'full_name': self.request.user.get_full_name()})
        return kwargs

    def form_valid(self, form):
        if is_authenticated(self.request):
            user = self.request.user
        else:
            user_model = get_user_model()
            email = form.cleaned_data.get('email', None)
            try:
                user = user_model.objects.get(email=email)
            except user_model.DoesNotExist:
                #pylint:disable=unused-variable
                first_name, mid, last_name = full_name_natural_split(
                    form.cleaned_data.get('full_name', None))
                user = user_model(
                    email=email, first_name=first_name, last_name=last_name)
        message = form.cleaned_data.get('message', '')
        provider = form.cleaned_data.get('provider', self.provider)
        items = []
        for key, value in six.iteritems(form.data):
            if value and not (key in form.cleaned_data or
                key in ('captcha', 'g-recaptcha-response',
                    'csrfmiddlewaretoken')):
                items += [(key, value)]
        if message:
            items += [("Message", message)]
        if user.email:
            if provider:
                provider = get_object_or_404(Organization, slug=provider)
            else:
                provider = self.provider
            try:
                contact_requested.send(
                    sender=__name__, provider=provider,
                    user=user, reason=items, request=self.request)
                messages.info(self.request,
    _("Your request has been sent. We will reply within 24 hours. Thank you."))
            except (SMTPException, socket.error) as err:
                LOGGER.exception("%s on page %s",
                    err, self.request.get_raw_uri())
                messages.error(self.request,
    _("Sorry, there was an issue sending your request for information"\
    " to '%(full_name)s &lt;%(email)s&gt;'.") % {
        'full_name': provider.full_name, 'email': provider.email})
        else:
            messages.warning(self.request,
    _("Thank you for the feedback. Please feel free to leave your contact"\
" information next time so we can serve you better."))
        return http.HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        next_url = validate_redirect(self.request)
        if not next_url:
            next_url = reverse('contact')
        return next_url
