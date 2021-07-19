# Copyright (c) 2021, DjaoDjin inc.
# see LICENSE
from __future__ import unicode_literals

from captcha.fields import ReCaptchaField
from captcha.widgets import ReCaptchaV2Checkbox
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordResetForm
from django.core.exceptions import NON_FIELD_ERRORS
from django.template.defaultfilters import slugify
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from django_countries import countries
from django_countries.fields import Country
from saas.forms import PostalFormMixin
from saas.models import Organization
from signup.forms import (ActivationForm as ActivationFormBase,
    FrictionlessSignupForm, PasswordConfirmMixin, AuthenticationForm,
    UserActivateForm as UserActivateFormBase)

from ..compat import six
from .fields import PhoneNumberField
from ..thread_locals import get_current_app


class MissingFieldsMixin(object):

    def _post_clean(self):
        """
        Since we allow sites to write their own form, we need a way
        to show the template developper that some form fields are missing.

        We use this internal hook for moving error messages around.
        """
        super(MissingFieldsMixin, self)._post_clean()
        missing = []
        for field_name in six.iterkeys(self._errors):
            if field_name != NON_FIELD_ERRORS:
                if not field_name in self.data and not isinstance(
                        self.fields[field_name], forms.BooleanField):
                    # BooleanField/Checkbox might not be sent by the browser
                    # when they are unchecked.
                    missing += [field_name]
        if missing:
            self.add_error(None, _("These input fields are missing: "\
                "%(identifiers)s.") % {'identifiers': ', '.join(missing)})


class ActivationForm(MissingFieldsMixin, ActivationFormBase):

    def __init__(self, *args, **kwargs):
        legal_agreement_url = kwargs['initial'].pop('legal_agreement_url', None)
        super(ActivationForm, self).__init__(*args, **kwargs)
        if legal_agreement_url:
            # BooleanField/Checkbox might not be sent by the browser
            # when they are unchecked which will lead to a generic
            # "field required" error message.
            # We add `required=False` here so that the error message
            # is generated in `clean_terms_of_use` instead.
            self.fields['terms_of_use'] = forms.BooleanField(
                label=mark_safe(_("I agree with <a href=\"%s\">terms and"\
                    " conditions</a>") % legal_agreement_url), required=False)

    def clean_terms_of_use(self):
        if not self.cleaned_data['terms_of_use']:
            raise forms.ValidationError(
                _("You must agree to terms and conditions."))
        return self.cleaned_data['terms_of_use']


class UserActivateForm(MissingFieldsMixin, UserActivateFormBase):

    pass


class PasswordForm(MissingFieldsMixin, PasswordResetForm):

    submit_title = _("Reset")

    email = forms.EmailField(widget=forms.TextInput(
            {'class':'input-block-level'}))


class SigninForm(MissingFieldsMixin, AuthenticationForm):

    submit_title = _("Sign in")
    hide_labels = True


class SignupForm(MissingFieldsMixin, PostalFormMixin, PasswordConfirmMixin,
                 FrictionlessSignupForm):
    """
    Form to Register a user and (optionally) a personal or organization
    profiles.

    All fields except for the full_name and e-mail are optional.
    """
    submit_title = _("Sign up")
    user_model = get_user_model()

    email2 = forms.EmailField(required=False,
        widget=forms.TextInput(attrs={'placeholder': _("Type e-mail again")}),
        label=_("E-mail confirmation"))
    username = forms.SlugField(required=False,
        widget=forms.TextInput(attrs={'placeholder': _("Username")}),
        max_length=30, label=_("Username"),
        error_messages={'invalid': _("Username may only contain letters,"\
" digits and -/_ characters. Spaces are not allowed.")})
    new_password = forms.CharField(required=False, strip=False,
        label=_("Password"),
        widget=forms.PasswordInput(attrs={'placeholder': _("Password")}))
    new_password2 = forms.CharField(required=False, strip=False,
        label=_("Confirm password"),
        widget=forms.PasswordInput(
            attrs={'placeholder': _("Type password again")}))

    organization_name = forms.CharField(required=False,
        label=_('Organization name'))

    street_address = forms.CharField(required=False, label=_("Street address"))
    locality = forms.CharField(required=False, label=_("City/Town"))
    region = forms.CharField(required=False, label=_("State/Province/County"))
    postal_code = forms.RegexField(required=False, regex=r'^[\w\s-]+$',
        label=_("Zip/Postal code"), max_length=30,
        error_messages={'invalid': _("The postal code may contain only"\
            " letters, digits, spaces and '-' characters.")})
    country = forms.RegexField(required=False, regex=r'^[a-zA-Z ]+$',
        widget=forms.widgets.Select(choices=countries), label=_("Country"))
    phone = PhoneNumberField(required=False, label=_('Phone number'))

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('instance', None)
        force_required = kwargs.pop('force_required', False)
        super(SignupForm, self).__init__(*args, **kwargs)
        self.fields['type'] = forms.ChoiceField(choices=[
            (slugify(choice[1]), choice[1])
            for choice in Organization.ACCOUNT_TYPE], required=False)
        if getattr(get_current_app(), 'registration_requires_recaptcha', False):
            # Default captcha field is already appended at the end of the list
            # of fields. We overwrite it here to set the theme.
            self.fields['captcha'] = ReCaptchaField(
                    widget=ReCaptchaV2Checkbox(
                        attrs={
                            'data-theme': 'clean',
                            'data-size': 'compact',
                        }))
        if 'country' in self.fields:
            # Country field is optional. We won't add a State/Province
            # in case it is omitted.
            if not ('country' in self.initial
                and self.initial['country']):
                self.initial['country'] = Country("US", None)
            country = self.initial.get('country', None)
            if not self.fields['country'].initial:
                self.fields['country'].initial = country.code
            self.add_postal_region(country=country)
        if force_required:
            for field_name, field in six.iteritems(self.fields):
                if field_name not in ('organization_name', 'type'):
                    field.required = True
        # Define  extra fields dynamically. These are never forced
        # to be required.
        for extra_field in self.initial.get('extra_fields', []):
            self.fields[extra_field[0]] = forms.CharField(
                label=_(extra_field[1]), required=extra_field[2])

    def clean(self):
        """
        Validates that both emails as well as both passwords respectively match.
        """
        self.cleaned_data = super(SignupForm, self).clean()
        if not ('email' in self._errors or 'email2' in self._errors):
            # If there are already errors reported for email or email2,
            # let's not override them with a confusing message here.
            if 'email' in self.data and 'email2' in self.data:
                # If `email2` wasn't passed in the POST request, we ignore it.
                email = self.cleaned_data['email']
                email2 = self.cleaned_data['email2']
                if email != email2:
                    self._errors['email'] = self.error_class([
                        _("This field does not match e-mail confirmation.")])
                    self._errors['email2'] = self.error_class([
                        _("This field does not match e-mail.")])
                    if 'email' in self.cleaned_data:
                        del self.cleaned_data['email']
                    if 'email2' in self.cleaned_data:
                        del self.cleaned_data['email2']
                    raise forms.ValidationError(
                        _("E-mail and e-mail confirmation do not match."))
        return self.cleaned_data

    def clean_email(self):
        """
        Normalizes emails in all lowercase.
        """
        if 'email' in self.cleaned_data:
            self.cleaned_data['email'] = self.cleaned_data['email'].lower()
        return self.cleaned_data['email']

    def clean_email2(self):
        """
        Normalizes emails in all lowercase.
        """
        if 'email2' in self.cleaned_data:
            self.cleaned_data['email2'] = self.cleaned_data['email2'].lower()
        return self.cleaned_data['email2']

    def clean_type(self):
        account_type = self.cleaned_data['type']
        if account_type:
            for type_choice in  Organization.ACCOUNT_TYPE:
                if account_type == slugify(type_choice[1]):
                    self.cleaned_data['type'] = type_choice[0]
                    return self.cleaned_data['type']
            raise forms.ValidationError(
                _("account type must be one of %(type)s") % {
                    'type': [type_choice[1]
                for type_choice in Organization.ACCOUNT_TYPE]})
        return Organization.ACCOUNT_UNKNOWN

    def clean_username(self):
        """
        Validate that the username is not already taken.
        """
        user = self.user_model.objects.filter(
            username__iexact=self.cleaned_data['username'])
        if user.exists():
            raise forms.ValidationError(
                _("A user with that %(username)s already exists.") % {
                    'username': self.fields['username'].label.lower()
                })
        organization = Organization.objects.filter(
            slug__iexact=self.cleaned_data['username'])
        if organization.exists():
            # If an `Organization` with slug == username exists,
            # it is bound to create problems later on.
            raise forms.ValidationError(
                _("A profile with that %(username)s already exists.") % {
                    'username': self.fields['username'].label.lower()
                })
        return self.cleaned_data['username']

    def clean_organization_name(self):
        """
        Validate that the username is not already taken.
        """
        if 'organization_name' in self.data:
            if not slugify(self.cleaned_data['organization_name']):
                raise forms.ValidationError(_("The organization name must"\
                " contain some alphabetical characters."))
#XXX disabled until we figure out why it raises a KeyError in production (!dev)
#XXX        user = self.user_model(email=self.cleaned_data['email'])
#XXX uses None in ``find_candidates`` for now.
            organization_name = self.cleaned_data['organization_name']
            candidates = Organization.objects.find_candidates(
                    organization_name, user=None)
            if candidates.exists():
                raise forms.ValidationError(
                    _("Your organization might already be registered."))
        return self.cleaned_data['organization_name']
