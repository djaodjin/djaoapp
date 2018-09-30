# Copyright (c) 2018, DjaoDjin inc.
# see LICENSE
from __future__ import unicode_literals

from captcha.fields import ReCaptchaField
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordResetForm
from django.core.exceptions import NON_FIELD_ERRORS
from django.utils.safestring import mark_safe
from django.utils import six
from django.utils.translation import ugettext_lazy as _
from django_countries import countries
from saas.forms import OrganizationForm
from saas.models import Organization
from signup.backends.auth import UsernameOrEmailAuthenticationForm
from signup.forms import ActivationForm as ActivationFormBase, NameEmailForm

from .fields import PhoneNumberField
from ..locals import get_current_app

NAME_RE = r"^([^\W\d_]|[ \.\'\-])+$"


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


class FrictionlessSignupForm(MissingFieldsMixin, NameEmailForm):
    """
    Ask for minimal information to start registration (i.e. name and email).
    """
    submit_title = _("Sign up")


class SignupForm(MissingFieldsMixin, NameEmailForm):
    """
    Register a user account.
    """
    submit_title = _("Register")
    user_model = get_user_model()

    username = forms.SlugField(widget=forms.TextInput(
        attrs={'placeholder': _("Username")}),
        max_length=30, label=_("Username"),
        error_messages={'invalid': _("Username may only contain letters,"\
" digits and -/_ characters. Spaces are not allowed.")})
    new_password1 = forms.CharField(widget=forms.PasswordInput(
        attrs={'placeholder': _("Password")}), label=_("Password"))
    new_password2 = forms.CharField(widget=forms.PasswordInput(
        attrs={'placeholder': _("Type password again")}),
        label=_("Confirm password"))

    def __init__(self, *args, **kwargs):
        super(SignupForm, self).__init__(*args, **kwargs)
        if getattr(get_current_app(), 'requires_recaptcha', False):
            # Default captcha field is already appended at the end of the list
            # of fields. We overwrite it here to set the theme.
            self.fields['captcha'] = ReCaptchaField(attrs={'theme' : 'clean'})

    def clean_username(self):
        """
        Validate that the username is not already taken.
        """
        user = self.user_model.objects.filter(
            username__iexact=self.cleaned_data['username'])
        if user.exists():
            raise forms.ValidationError(
                _("A user with that username already exists."))
        return self.cleaned_data['username']

    def clean_email(self):
        user = self.user_model.objects.filter(
            email__iexact=self.cleaned_data['email'])
        if user.exists():
            raise forms.ValidationError(
                _("A user with that e-mail address already exists."))
        return self.cleaned_data['email']

    def clean(self):
        """
        Validates that both passwords respectively match.
        """
        if not ('new_password1' in self._errors
            or 'new_password2' in self._errors):
            new_password1 = self.cleaned_data.get('new_password1', False)
            new_password2 = self.cleaned_data.get('new_password2', True)
            if new_password1 != new_password2:
                self._errors['new_password1'] = self.error_class([
                    _("This field does not match password confirmation.")])
                self._errors['new_password2'] = self.error_class([
                    _("This field does not match password.")])
                if 'new_password1' in self.cleaned_data:
                    del self.cleaned_data['new_password1']
                if 'new_password2' in self.cleaned_data:
                    del self.cleaned_data['new_password2']
                raise forms.ValidationError(
                    _("Password and password confirmation do not match."))
        return self.cleaned_data


class SigninForm(MissingFieldsMixin, UsernameOrEmailAuthenticationForm):

    submit_title = _("Sign in")
    hide_labels = True


class PasswordForm(MissingFieldsMixin, PasswordResetForm):

    submit_title = _("Reset")

    email = forms.EmailField(widget=forms.TextInput(
            {'class':'input-block-level'}))


class EmailListSignupForm(MissingFieldsMixin, forms.Form):
    """
    Sign up form typically used on e-mail list sign up forms.
    This form asks for an e-mail, first name, last name and
    a password/confirmation pair.
    """

    email = forms.EmailField(
        widget=forms.TextInput(attrs={
            'placeholder': _("E-mail address"), 'maxlength': 75}),
        label=_("E-mail address"))
    first_name = forms.RegexField(NAME_RE,
        label=_('First name'), min_length=2, max_length=30,
        error_messages={'invalid': _("First name may only contain letters"\
            " and dot (.) or apostrophe (') characters.")})
    last_name = forms.RegexField(NAME_RE,
        label=_('Last name'), min_length=2, max_length=30,
        error_messages={'invalid': _("Last name may only contain letters"\
            " and dot (.) or apostrophe (') characters.")})
    new_password1 = forms.CharField(
        widget=forms.PasswordInput, label=_("Password"))
    new_password2 = forms.CharField(
        widget=forms.PasswordInput, label=_("Confirm password"))

    def clean(self):
        """
        Validates that both passwords respectively match.
        """
        if not ('new_password1' in self._errors
            or 'new_password2' in self._errors):
            new_password1 = self.cleaned_data.get('new_password1', False)
            new_password2 = self.cleaned_data.get('new_password2', True)
            if new_password1 != new_password2:
                self._errors['new_password1'] = self.error_class([
                    _("This field does not match password confirmation.")])
                self._errors['new_password2'] = self.error_class([
                    _("This field does not match password.")])
                if 'new_password1' in self.cleaned_data:
                    del self.cleaned_data['new_password1']
                if 'new_password2' in self.cleaned_data:
                    del self.cleaned_data['new_password2']
                raise forms.ValidationError(
                    _("Password and password confirmation do not match."))
        return self.cleaned_data


class TogetherRegistrationForm(MissingFieldsMixin, OrganizationForm):
    """
    Form to register a user and organization at the same time.
    """
    submit_title = _("Register")
    user_model = get_user_model()
    organization_name = forms.CharField(label=_('Organization name'))

    class Meta: # duplicate of in OrganizationForm.Meta. Is it needed?
        model = Organization
        fields = ('full_name', 'email', 'phone', 'country',
                  'region', 'locality', 'street_address', 'postal_code')
        widgets = {'country': forms.widgets.Select(choices=countries)}

    # full_name is overridden from OrganizationForm to mean user full_name
    full_name = forms.RegexField(NAME_RE,
        label=_("Full name"), min_length=2, max_length=30,
        error_messages={'invalid': _("Full name may only contain letters"\
            " and dot (.) or apostrophe (') characters.")})
    username = forms.SlugField(
        label=_("Username"), max_length=30,
        error_messages={'invalid': _("Username may only contain letters,"\
            " digits and -/_ characters. Spaces are not allowed.")})
    email = forms.EmailField(
        widget=forms.TextInput(attrs={'maxlength': 75}),
        label=_("E-mail address"))
    new_password1 = forms.CharField(
        widget=forms.PasswordInput, label=_("Password"))
    new_password2 = forms.CharField(
        widget=forms.PasswordInput, label=_("Confirm password"))

    def __init__(self, *args, **kwargs):
        #call our superclasse's initializer
        super(TogetherRegistrationForm, self).__init__(*args, **kwargs)
        for extra_field in self.initial['extra_fields']:
            # define extra fields dynamically:
            self.fields[extra_field[0]] = forms.CharField(
                label=_(extra_field[1]), required=extra_field[2])

    def clean(self):
        """
        Validates that both passwords respectively match.
        """
        if not ('new_password1' in self._errors
            or 'new_password2' in self._errors):
            new_password1 = self.cleaned_data.get('new_password1', False)
            new_password2 = self.cleaned_data.get('new_password2', True)
            if new_password1 != new_password2:
                self._errors['new_password1'] = self.error_class([
                    _("This field does not match password confirmation.")])
                self._errors['new_password2'] = self.error_class([
                    _("This field does not match password.")])
                if 'new_password1' in self.cleaned_data:
                    del self.cleaned_data['new_password1']
                if 'new_password2' in self.cleaned_data:
                    del self.cleaned_data['new_password2']
                raise forms.ValidationError(
                    _("Password and password confirmation do not match."))
        return self.cleaned_data

    def clean_email(self):
        """
        Normalizes emails in all lowercase.
        """
        if 'email' in self.cleaned_data:
            self.cleaned_data['email'] = self.cleaned_data['email'].lower()
        user = self.user_model.objects.filter(
            email__iexact=self.cleaned_data['email'])
        if user.exists():
            raise forms.ValidationError(
                _("A user with that e-mail address already exists."))
        return self.cleaned_data['email']

    def clean_username(self):
        """
        Validate that the username is not already taken.
        """
        user = self.user_model.objects.filter(
            username__iexact=self.cleaned_data['username'])
        if user.exists():
            raise forms.ValidationError(
                _("A user with that username already exists."))
        return self.cleaned_data['username']

    def clean_organization_name(self):
        """
        Validate that the username is not already taken.
        """
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


class PersonalRegistrationForm(MissingFieldsMixin, OrganizationForm):
    """
    Form to register a user and organization at the same time with the added
    constraint that both will behave as a single billing profile.
    """
    submit_title = _("Register")
    user_model = get_user_model()

    class Meta:
        model = Organization
        fields = ('email', 'phone', 'street_address',
                  'locality', 'region', 'postal_code',
                  'country', 'phone')
        widgets = {'country': forms.widgets.Select(choices=countries)}

    username = forms.SlugField(
        label=_("Username"), max_length=30,
        error_messages={'invalid': _("Username may only contain letters,"\
            " digits and -/_ characters. Spaces are not allowed.")})
    email = forms.EmailField(
        widget=forms.TextInput(attrs={'maxlength': 75}),
        label=_("E-mail address"))
    email2 = forms.EmailField(
        widget=forms.TextInput(attrs={'maxlength': 75}),
        label=_("E-mail confirmation"))
    new_password1 = forms.CharField(
        widget=forms.PasswordInput, label=_("Password"))
    new_password2 = forms.CharField(
        widget=forms.PasswordInput, label=_("Confirm password"))
    first_name = forms.RegexField(NAME_RE,
        label=_("First name"), min_length=2, max_length=30,
        error_messages={'invalid': _("First name may only contain letters"\
            " and dot (.) or apostrophe (') characters.")})
    last_name = forms.RegexField(NAME_RE,
        label=_("Last name"), min_length=2, max_length=30,
        error_messages={'invalid': _("Last name may only contain letters"\
            " and dot (.) or apostrophe (') characters.")})
    street_address = forms.CharField(label=_("Street address"))
    locality = forms.CharField(label=_("City/Town"))
    region = forms.CharField(label=_("State/Province/County"))
    postal_code = forms.RegexField(regex=r'^[\w\s-]+$',
        label=_("Zip/Postal code"), max_length=30,
        error_messages={'invalid': _("The postal code may contain only"\
            " letters, digits, spaces and '-' characters.")})
    country = forms.RegexField(regex=r'^[a-zA-Z ]+$',
        widget=forms.widgets.Select(choices=countries), label=_("Country"))
    phone = PhoneNumberField(label=_('Phone number'))

    def clean(self):
        """
        Validates that both emails as well as both passwords respectively match.
        """
        if not ('email' in self._errors or 'email2' in self._errors):
            # If there are already errors reported for email or email2,
            # let's not override them with a confusing message here.
            email = self.cleaned_data.get('email', 'A')
            email2 = self.cleaned_data.get('email2', 'B')
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
        if not ('new_password1' in self._errors
            or 'new_password2' in self._errors):
            new_password1 = self.cleaned_data.get('new_password1', False)
            new_password2 = self.cleaned_data.get('new_password2', True)
            if new_password1 != new_password2:
                self._errors['new_password1'] = self.error_class([
                    _("This field does not match password confirmation.")])
                self._errors['new_password2'] = self.error_class([
                    _("This field does not match password.")])
                if 'new_password1' in self.cleaned_data:
                    del self.cleaned_data['new_password1']
                if 'new_password2' in self.cleaned_data:
                    del self.cleaned_data['new_password2']
                raise forms.ValidationError(
                    _("Password and password confirmation do not match."))
        if not ('first_name' in self._errors or 'last_name' in self._errors):
            first_name = self.cleaned_data.get('first_name', False)
            last_name = self.cleaned_data.get('last_name', False)
            if first_name == last_name:
                self._errors['first_name'] = self.error_class([
                    _("The first name is identical to last name.")])
                self._errors['last_name'] = self.error_class([
                    _("The last name is identical to first name.")])
                if 'first_name' in self.cleaned_data:
                    del self.cleaned_data['first_name']
                if 'last_name' in self.cleaned_data:
                    del self.cleaned_data['last_name']
                raise forms.ValidationError(
                    _("First and last names should not be identical."))
        return self.cleaned_data

    def clean_email(self):
        """
        Normalizes emails in all lowercase.
        """
        if 'email' in self.cleaned_data:
            self.cleaned_data['email'] = self.cleaned_data['email'].lower()
        user = self.user_model.objects.filter(
            email__iexact=self.cleaned_data['email'])
        if user.exists():
            raise forms.ValidationError(
                _("A user with that e-mail address already exists."))
        return self.cleaned_data['email']

    def clean_email2(self):
        """
        Normalizes emails in all lowercase.
        """
        if 'email2' in self.cleaned_data:
            self.cleaned_data['email2'] = self.cleaned_data['email2'].lower()
        return self.cleaned_data['email2']

    def clean_first_name(self):
        """
        Normalizes first names by capitalizing them.
        """
        if 'first_name' in self.cleaned_data:
            self.cleaned_data['first_name'] \
                = self.cleaned_data['first_name'].capitalize()
        return self.cleaned_data['first_name']

    def clean_last_name(self):
        """
        Normalizes first names by capitalizing them.
        """
        if 'last_name' in self.cleaned_data:
            self.cleaned_data['last_name'] \
                = self.cleaned_data['last_name'].capitalize()
        return self.cleaned_data['last_name']

    def clean_username(self):
        """
        Validate that the username is not already taken.
        """
        user = self.user_model.objects.filter(
            username__iexact=self.cleaned_data['username'])
        if user.exists():
            raise forms.ValidationError(
                _("A user with that username already exists."))
        organization = Organization.objects.filter(
            slug=self.cleaned_data['username'])
        if organization.exists():
            raise forms.ValidationError(
                # XXX use username_label? profile vs. User?
                _("A profile with that identifier already exists."))
        return self.cleaned_data['username']
