# Copyright (c) 2018, DjaoDjin inc.
# see LICENSE
from __future__ import unicode_literals

import logging, socket
from smtplib import SMTPException

from captcha.fields import ReCaptchaField
from django import forms, http
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db.utils import ProgrammingError
from django.shortcuts import get_object_or_404
from django.utils import six
from django.utils.translation import ugettext_lazy as _
from saas.mixins import ProviderMixin
from saas.models import Organization, split_full_name
from signup.auth import validate_redirect
from survey.forms import ResponseCreateForm
from survey.models import SurveyModel
from survey.views.response import ResponseCreateView

from ..compat import reverse
from ..locals import get_current_app
from ..signals import contact_requested


LOGGER = logging.getLogger(__name__)

class ContactForm(ResponseCreateForm):

    provider = forms.CharField(
        widget=forms.HiddenInput(), required=False)
    full_name = forms.CharField(
        widget=forms.TextInput({'class':'form-control'}))
    email = forms.EmailField(
        widget=forms.TextInput({'class':'form-control'}))

    def __init__(self, *args, **kwargs):
        super(ContactForm, self).__init__(*args, **kwargs)
        question_fields = []
        for key in six.iterkeys(self.fields):
            if key.startswith('question-') or key.startswith('other-'):
                question_fields += [key]
        self.fields['message'] = forms.CharField(required=False,
            widget=forms.Textarea(attrs={'class':'form-control',
            'placeholder': kwargs.get('initial', {}).get('placeholder', "")}))
        if not kwargs.get('initial', {}).get('email', None):
            if getattr(get_current_app(), 'contact_requires_recaptcha', False):
                self.fields['captcha'] = ReCaptchaField(
                    attrs={'theme' : 'clean'})


class ContactView(ProviderMixin, ResponseCreateView):

    form_class = ContactForm
    template_name = 'contact.html'

    def get_interviewee(self):
        # Avoids 404s (see survey.mixins.IntervieweeMixin)
        if self.request.user.is_authenticated():
            return self.request.user
        return None

    def get_survey(self):
        try:
            survey = SurveyModel.objects.get(
                account=self.organization, slug='contact')
        except (SurveyModel.DoesNotExist, ProgrammingError):
            # ``ProgrammingError`` because we do not necessary
            # use the survey app.
            survey = None
        return survey

    def get_initial(self):
        kwargs = super(ContactView, self).get_initial()
        if self.request.user.is_authenticated():
            kwargs.update({
                'email': self.request.user.email,
                'full_name': self.request.user.get_full_name()})
        if self.survey:
            kwargs.update({
                'questions': self.survey.questions.order_by('rank')})
        return kwargs

    def form_valid(self, form):
        if self.get_survey():
            # If we end-up creating Response records but the account constraint
            # is different between the front-end proxy and app, that would blow
            # up, even when no survey is present.
            response = super(ContactView, self).form_valid(form)
        else:
            response = None
        if self.request.user.is_authenticated():
            user = self.request.user
        else:
            user_model = get_user_model()
            email = form.cleaned_data.get('email', None)
            try:
                user = user_model.objects.get(email=email)
            except user_model.DoesNotExist:
                first_name, last_name = split_full_name(
                    form.cleaned_data.get('full_name', None))
                user = user_model(
                    email=email, first_name=first_name, last_name=last_name)
        message = form.cleaned_data.get('message', '')
        provider = form.cleaned_data.get('provider', None)
        items = []
        if self.object:
            for answer in self.object.answers.order_by('rank'):
                if answer.text:
                    question = answer.question
                    items += [(question.text, answer.text)]
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
        if not response:
            response = http.HttpResponseRedirect(self.get_success_url())
        return response

    def get_success_url(self):
        next_url = validate_redirect(self.request)
        if not next_url:
            next_url = reverse('contact')
        return next_url
