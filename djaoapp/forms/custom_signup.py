# Copyright (c) 2018, DjaoDjin inc.
# see LICENSE

from captcha.fields import ReCaptchaField
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordResetForm
from django.core.exceptions import NON_FIELD_ERRORS
from django.utils import six
from django.utils.translation import ugettext_lazy as _
from django_countries import countries
from saas.forms import OrganizationForm
from saas.models import Organization
from signup.backends.auth import UsernameOrEmailAuthenticationForm
from signup.forms import NameEmailForm

from djaoapp.forms.fields import PhoneNumberField

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
        for field_name, _ in six.iteritems(self._errors):
            if field_name != NON_FIELD_ERRORS:
                if not field_name in self.data:
                    missing += [field_name]
        if missing:
            self.add_error(None, "These input fields are missing: %s."
                % ', '.join(missing))


class FrictionlessSignupForm(MissingFieldsMixin, NameEmailForm):
    """
    Ask for minimal information to start registration (i.e. name and email).
    """
    submit_title = "Sign up"


class SignupForm(MissingFieldsMixin, NameEmailForm):
    """
    Register a user account.
    """
    submit_title = "Register"
    user_model = get_user_model()

    username = forms.SlugField(widget=forms.TextInput(
        attrs={'placeholder': 'Username'}),
        max_length=30, label=_("Username"),
        error_messages={'invalid': _("username may only contain letters,"\
" numbers and -/_ characters. Spaces are not allowed.")})
    new_password1 = forms.CharField(widget=forms.PasswordInput(
        attrs={'placeholder': 'Password'}), label=_("Password"))
    new_password2 = forms.CharField(widget=forms.PasswordInput(
        attrs={'placeholder': 'Type Password Again'}),
        label=_("Password confirmation"))
    captcha = ReCaptchaField(attrs={'theme' : 'clean'})

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
                _("A user with that email address already exists."))
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
                    "This field does not match Password confirmation."])
                self._errors['new_password2'] = self.error_class([
                    "This field does not match Password."])
                if 'new_password1' in self.cleaned_data:
                    del self.cleaned_data['new_password1']
                if 'new_password2' in self.cleaned_data:
                    del self.cleaned_data['new_password2']
                raise forms.ValidationError(
                    _("Password and Password confirmation do not match."))
        return self.cleaned_data


class SigninForm(MissingFieldsMixin, UsernameOrEmailAuthenticationForm):

    submit_title = "Sign in"
    hide_labels = True


class PasswordForm(MissingFieldsMixin, PasswordResetForm):

    submit_title = "Reset"

    email = forms.EmailField(widget=forms.TextInput(
            {'class':'input-block-level'}))


class EmailListSignupForm(MissingFieldsMixin, forms.Form):
    """
    Sign up form typically used on e-mail list sign up forms.
    This form asks for an e-mail, first name, last name and
    a password/confirmation pair.
    """

    email = forms.EmailField(
        widget=forms.TextInput(attrs={'placeholder':'Email', 'maxlength': 75}),
        label=_("E-mail"))
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
        widget=forms.PasswordInput, label=_("Password confirmation"))

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
                    "This field does not match Password confirmation."])
                self._errors['new_password2'] = self.error_class([
                    "This field does not match Password."])
                if 'new_password1' in self.cleaned_data:
                    del self.cleaned_data['new_password1']
                if 'new_password2' in self.cleaned_data:
                    del self.cleaned_data['new_password2']
                raise forms.ValidationError(
                    _("Password and Password confirmation do not match."))
        return self.cleaned_data


class TogetherRegistrationForm(MissingFieldsMixin, OrganizationForm):
    """
    Form to register a user and organization at the same time.
    """
    submit_title = "Register"
    user_model = get_user_model()
    full_name = forms.CharField(label=_('Organization name'))

    class Meta: # duplicate of in OrganizationForm.Meta. Is it needed?
        model = Organization
        fields = ('full_name', 'email', 'phone', 'country',
                  'region', 'locality', 'street_address', 'postal_code')
        widgets = {'country': forms.widgets.Select(choices=countries)}

    user_full_name = forms.RegexField(NAME_RE,
        label=_('Full name'), min_length=2, max_length=30,
        error_messages={'invalid': _("Full name may only contain letters"\
            " and dot (.) or apostrophe (') characters.")})
    username = forms.SlugField(
        label=_("Username"), max_length=30,
        error_messages={'invalid': _("username may only contain letters,"\
            " numbers and -/_ characters. Spaces are not allowed.")})
    email = forms.EmailField(
        widget=forms.TextInput(attrs={'maxlength': 75}),
        label=_("Email address"))
    new_password1 = forms.CharField(
        widget=forms.PasswordInput, label=_("Password"))
    new_password2 = forms.CharField(
        widget=forms.PasswordInput, label=_("Password confirmation"))

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
                    "This field does not match Password confirmation."])
                self._errors['new_password2'] = self.error_class([
                    "This field does not match Password."])
                if 'new_password1' in self.cleaned_data:
                    del self.cleaned_data['new_password1']
                if 'new_password2' in self.cleaned_data:
                    del self.cleaned_data['new_password2']
                raise forms.ValidationError(
                    _("Password and Password confirmation do not match."))
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
                _("A user with that email already exists."))
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

    def clean_full_name(self):
        """
        Validate that the username is not already taken.
        """
#XXX disabled until we figure out why it raises a KeyError in production (!dev)
#XXX        user = self.user_model(email=self.cleaned_data['email'])
#XXX uses None in ``find_candidates`` for now.
        organization_name = self.cleaned_data['full_name']
        candidates = Organization.objects.find_candidates(
                organization_name, user=None)
        if candidates.exists():
            raise forms.ValidationError(
                _("Your organization might already be registered."))
        return self.cleaned_data['full_name']



class PersonalRegistrationForm(MissingFieldsMixin, OrganizationForm):
    """
    Form to register a user and organization at the same time with the added
    constraint that both will behave as a single billing profile.
    """
    submit_title = "Register"
    user_model = get_user_model()

    class Meta:
        model = Organization
        fields = ('email', 'phone', 'street_address',
                  'locality', 'region', 'postal_code',
                  'country', 'phone')
        widgets = {'country': forms.widgets.Select(choices=countries)}

    username = forms.SlugField(
        label=_("Username"), max_length=30,
        error_messages={'invalid': _("username may only contain letters,"\
            " numbers and -/_ characters. Spaces are not allowed.")})
    email = forms.EmailField(
        widget=forms.TextInput(attrs={'maxlength': 75}), label=_("E-mail"))
    email2 = forms.EmailField(
        widget=forms.TextInput(attrs={'maxlength': 75}),
        label=_("E-mail confirmation"))
    new_password1 = forms.CharField(
        widget=forms.PasswordInput, label=_("Password"))
    new_password2 = forms.CharField(
        widget=forms.PasswordInput, label=_("Password confirmation"))
    first_name = forms.RegexField(NAME_RE,
        label=_('First name'), min_length=2, max_length=30,
        error_messages={'invalid': _("First name may only contain letters"\
            " and dot (.) or apostrophe (') characters.")})
    last_name = forms.RegexField(NAME_RE,
        label=_('Last name'), min_length=2, max_length=30,
        error_messages={'invalid': _("Last name may only contain letters"\
            " and dot (.) or apostrophe (') characters.")})
    street_address = forms.CharField(label=_('Street address'))
    locality = forms.CharField(label=_('City'))
    region = forms.CharField(label=_('State/Province'))
    postal_code = forms.RegexField(regex=r'^[\w\s-]+$',
        label=_('Postal code'), max_length=30,
        error_messages={'invalid': _("The postal code may contain only"\
            " letters, numbers, spaces and '-' characters.")})
    country = forms.RegexField(regex=r'^[a-zA-Z ]+$',
        widget=forms.widgets.Select(choices=countries), label='Country')
    phone = PhoneNumberField(label=_('Phone'))

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
                self._errors['email'] = self.error_class(["This field does"\
    " not match E-mail confirmation."])
                self._errors['email2'] = self.error_class(["This field does"\
    " not match E-mail."])
                if 'email' in self.cleaned_data:
                    del self.cleaned_data['email']
                if 'email2' in self.cleaned_data:
                    del self.cleaned_data['email2']
                raise forms.ValidationError(
                    _("Email and E-mail confirmation do not match."))
        if not ('new_password1' in self._errors
            or 'new_password2' in self._errors):
            new_password1 = self.cleaned_data.get('new_password1', False)
            new_password2 = self.cleaned_data.get('new_password2', True)
            if new_password1 != new_password2:
                self._errors['new_password1'] = self.error_class([
                    "This field does not match Password confirmation."])
                self._errors['new_password2'] = self.error_class([
                    "This field does not match Password."])
                if 'new_password1' in self.cleaned_data:
                    del self.cleaned_data['new_password1']
                if 'new_password2' in self.cleaned_data:
                    del self.cleaned_data['new_password2']
                raise forms.ValidationError(
                    _("Password and Password confirmation do not match."))
        if not ('first_name' in self._errors or 'last_name' in self._errors):
            first_name = self.cleaned_data.get('first_name', False)
            last_name = self.cleaned_data.get('last_name', False)
            if first_name == last_name:
                self._errors['first_name'] = self.error_class([
                    "The first name is identical to last name."])
                self._errors['last_name'] = self.error_class([
                    "The last name is identical to first name."])
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
                _("A user with that email already exists."))
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
                _("A profile with that username already exists."))
        return self.cleaned_data['username']
