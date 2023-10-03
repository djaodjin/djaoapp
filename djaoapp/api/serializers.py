# Copyright (c) 2023 DjaoDjin inc.
# see LICENSE

import logging, sys

from captcha import client
from captcha.constants import TEST_PRIVATE_KEY, TEST_PUBLIC_KEY
from django.conf import settings
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.utils.deconstruct import deconstructible
from rest_framework import serializers
from rules.api.serializers import AppSerializer as RulesAppSerializer
from saas.api.serializers import (
    OrganizationDetailSerializer as OrganizationBaseSerializer,
    OrganizationWithSubscriptionsSerializer,
    OrganizationWithEndsAtByPlanSerializer)
from saas.models import get_broker, Role, ChargeItem
from saas.api.serializers import EnumField
from signup.serializers import ActivitySerializer as UserActivitySerializer
from signup.serializers import UserCreateSerializer

from .. import __version__
from ..compat import gettext_lazy as _, six
from ..utils import get_contact_captcha_keys
from ..validators import validate_contact_form


LOGGER = logging.getLogger(__name__)


class NoModelSerializer(serializers.Serializer):

    def create(self, validated_data):
        raise RuntimeError('`create()` should not be called.')

    def update(self, instance, validated_data):
        raise RuntimeError('`update()` should not be called.')


class ProfileSerializer(OrganizationBaseSerializer):

    nick_name = serializers.CharField(read_only=True, required=False,
        help_text=_("Short casual name used to address the contact"\
            " (only available for 'personal' and 'user' accounts)"))
    lang = serializers.CharField(read_only=True, required=False,
        help_text=_("Preferred communication language"\
            " (only available for 'personal' and 'user' accounts)"))

    class Meta(OrganizationBaseSerializer.Meta):
        fields = OrganizationBaseSerializer.Meta.fields + (
            'nick_name', 'lang',)
        read_only_fields = OrganizationBaseSerializer.Meta.read_only_fields + (
            'nick_name', 'lang',)

    @staticmethod
    def get_printable_name(obj):
        if hasattr(obj, 'nick_name') and obj.nick_name:
            return obj.nick_name
        return obj.printable_name


class ProfileDetailSerializer(OrganizationWithSubscriptionsSerializer):

    nick_name = serializers.CharField(read_only=True, required=False,
        help_text=_("Short casual name used to address the contact"\
            " (only available for 'personal' and 'user' accounts)"))
    lang = serializers.CharField(read_only=True, required=False,
        help_text=_("Preferred communication language"\
            " (only available for 'personal' and 'user' accounts)"))
    activities = UserActivitySerializer(many=True, read_only=True,
        help_text=_("Activities related to the account"\
            " (only available for 'personal' and 'user' accounts)"))

    class Meta(OrganizationWithSubscriptionsSerializer.Meta):
        fields = OrganizationWithSubscriptionsSerializer.Meta.fields + (
            'nick_name', 'lang', 'activities')
        read_only_fields = OrganizationWithSubscriptionsSerializer\
.Meta.read_only_fields + (
            'nick_name', 'lang',)

    @staticmethod
    def get_printable_name(obj):
        if hasattr(obj, 'nick_name') and obj.nick_name:
            return obj.nick_name
        return obj.printable_name


class RegisterSerializer(UserCreateSerializer):

    organization_name = serializers.CharField(required=False,
        help_text=_("Organization name that owns the billing,"\
            " registered with the user as profile manager"))
    street_address = serializers.CharField(required=False,
        help_text=_("Street address for the billing profile"))
    locality = serializers.CharField(required=False,
        help_text=_("City/Town for the billing profile"))
    region = serializers.CharField(required=False,
        help_text=_("State/Province/County for the billing profile"))
    postal_code = serializers.CharField(required=False,
        help_text=_("Zip/Postal Code for the billing profile"))
    country = serializers.CharField(required=False,
        help_text=_("Country for the billing profile"))

    class Meta(UserCreateSerializer.Meta):
        fields = UserCreateSerializer.Meta.fields + (
            'organization_name', 'street_address', 'locality',
            'region', 'postal_code', 'country', 'type')

#pylint:disable=protected-access
RegisterSerializer._declared_fields["type"] = \
    EnumField(choices=ProfileSerializer.Meta.model.ACCOUNT_TYPE, required=False,
        help_text=_("Type of the accounts being registered"))


class SessionSerializer(serializers.ModelSerializer):

    last_visited = serializers.DateTimeField(required=False)
    username = serializers.SerializerMethodField()
    roles = serializers.SerializerMethodField()
    site = serializers.SerializerMethodField()
    invoice_keys = serializers.SerializerMethodField()
    session_key = serializers.SerializerMethodField()
    access_key = serializers.SerializerMethodField()
    secret_key = serializers.SerializerMethodField()
    security_token = serializers.SerializerMethodField()

    class Meta:
        model = get_user_model()
        fields = ('username', 'roles', 'site', 'last_visited', 'invoice_keys',
            'session_key', 'access_key', 'secret_key', 'security_token')
        read_only_fields = ('username', 'roles', 'site', 'last_visited',
            'invoice_keys',
            'session_key', 'access_key', 'secret_key', 'security_token')

    @staticmethod
    def get_username(request):
        return request.user.username

    @staticmethod
    def get_roles(request):
        results = {}
        role_key = None
        organizations = []
        prev_role_key = None
        serializer = OrganizationWithEndsAtByPlanSerializer(many=True)
        for role in Role.objects.valid_for(user=request.user).order_by(
                'role_description').select_related('role_description'):
            role_key = role.role_description.slug
            if not prev_role_key:
                prev_role_key = role_key
            elif role_key != prev_role_key:
                results[prev_role_key] = serializer.to_representation(
                    organizations)
                prev_role_key = role_key
                organizations = []
            organizations += [role.organization]
        if organizations:
            results[prev_role_key] = serializer.to_representation(organizations)
        return results

    @staticmethod
    def get_site(obj): #pylint:disable=unused-argument
        broker = get_broker()
        return {'slug': broker.slug, 'printable_name': broker.printable_name,
            'email': broker.email}

    def get_invoice_keys(self, request):
        rule = self.context.get('rule', None)
        if rule and rule.rule_op >= 1: # XXX Authenticated
            return [result['invoice_key']
                for result in ChargeItem.objects.to_sync(request.user).values(
                    'invoice_key').distinct()]
        return []

    @staticmethod
    def get_session_key(request):
        if hasattr(request, 'session'):
            return request.session.session_key
        return None

    @staticmethod
    def get_access_key(request):
        if hasattr(request, 'session'):
            return request.session.get('access_key', None)
        return None

    @staticmethod
    def get_secret_key(request):
        if hasattr(request, 'session'):
            return request.session.get('secret_key', None)
        return None

    @staticmethod
    def get_security_token(request):
        if hasattr(request, 'session'):
            return request.session.get('security_token', None)
        return None


class AppSerializer(RulesAppSerializer):

    class Meta(RulesAppSerializer.Meta):
        fields = RulesAppSerializer.Meta.fields + ('show_edit_tools',)


class RecentActivitySerializer(NoModelSerializer):
    """
    Serializer for recent activity on the site.
    """
    slug = serializers.SlugField(
        help_text=_("Unique identifier for the user or profile"))
    printable_name = serializers.CharField(
        help_text=_("Name that can be safely used for display in HTML pages"))
    descr = serializers.CharField(
        help_text=_("Description of the activity"))
    created_at = serializers.DateTimeField(
        help_text=_("Date/time of creation (in ISO format)"))

RecentActivitySerializer._declared_fields["type"] = \
    serializers.CharField(required=False, #pylint:disable=protected-access
    help_text=_("One of 'organization', 'personal' or 'user'"))


class DetailSerializer(NoModelSerializer):
    """
    Details on the result of an API call
    """
    detail = serializers.CharField(help_text=_("Describes the result of"\
        " the API call in plain text"))



@deconstructible
class ReCaptchaValidator(object):
    error_messages = {
        "captcha_invalid": _("Error verifying reCAPTCHA, please try again."),
        "captcha_error": _("Error verifying reCAPTCHA, please try again."),
    }

    def __init__(self, public_key=None, private_key=None, required_score=None):
        # reCAPTCHA fields are always required.
        self.required = True

        # Our score values need to be floats, as that is the expected
        # response from the Google endpoint. Rather than ensure that on
        # the widget, we do it on the field to better support user
        # subclassing of the widgets.
        self.required_score = float(required_score) if required_score else 0

        # Setup instance variables.
        self.private_key = private_key or getattr(
            settings, "RECAPTCHA_PRIVATE_KEY", TEST_PRIVATE_KEY)
        self.public_key = public_key or getattr(
            settings, "RECAPTCHA_PUBLIC_KEY", TEST_PUBLIC_KEY)

    @staticmethod
    def get_remote_ip():
        frm = sys._getframe() #pylint:disable=protected-access
        while frm:
            request = frm.f_locals.get("request")
            if request:
                remote_ip = request.META.get("REMOTE_ADDR", "")
                forwarded_ip = request.META.get("HTTP_X_FORWARDED_FOR", "")
                ip_addr = remote_ip if not forwarded_ip else forwarded_ip
                return ip_addr
            frm = frm.f_back

    def __call__(self, value):
        """
        Validate that the input contains a valid Re-Captcha value.
        """
        try:
            check_captcha = client.submit(
                recaptcha_response=value,
                private_key=self.private_key,
                remoteip=self.get_remote_ip(),
            )

        except six.moves.urllib.error.HTTPError:  # Catch timeouts, etc
            raise ValidationError(
                self.error_messages["captcha_error"],
                code="captcha_error"
            )

        if not check_captcha.is_valid:
            LOGGER.error(
                "ReCAPTCHA validation failed due to: %s",
                check_captcha.error_codes
            )
            raise ValidationError(
                self.error_messages["captcha_invalid"],
                code="captcha_invalid"
            )

        if self.required_score:
            # If a score was expected but non was returned, default to a 0,
            # which is the lowest score that it can return. This is to do our
            # best to assure a failure here, we can not assume that a form
            # that needed the threshold should be valid if we didn't get a
            # value back.
            score = float(check_captcha.extra_data.get("score", 0))

            if self.required_score > score:
                LOGGER.error(
                    "ReCAPTCHA validation failed due to its score of %s"
                    " being lower than the required amount.", score)
                raise ValidationError(
                    self.error_messages["captcha_invalid"],
                    code="captcha_invalid")


class ReCaptchaField(serializers.CharField):

    def __init__(self, public_key=None, private_key=None, **kwargs):
        super().__init__(**kwargs)
        validator = ReCaptchaValidator(
            public_key=public_key, private_key=private_key)
        self.validators.append(validator)


class ContactUsSerializer(NoModelSerializer):

    full_name = serializers.CharField(
        help_text=_("Full name the sender of the message wishes"\
        " to be addressed as"))
    email = serializers.EmailField(
        help_text=_("Email address to reply to the sender"))
    message = serializers.CharField(
        help_text=_("Description of the reason for contacting the provider"),
        required=False)

    def __init__(self, *args, **kwargs):
        super(ContactUsSerializer, self).__init__(*args, **kwargs)
        if not kwargs.get('initial', {}).get('email', None):
            captcha_keys = get_contact_captcha_keys()
            if captcha_keys:
                self.fields['g-recaptcha-response'] = ReCaptchaField(
                    public_key=captcha_keys['public_key'],
                    private_key=captcha_keys['private_key'])

    def validate(self, attrs):
        validate_contact_form(
            attrs.get('full_name'),
            attrs.get('email'),
            attrs.get('message'))
        return attrs


class VersionSerializer(NoModelSerializer):

    version = serializers.SerializerMethodField(read_only=True,
        help_text=_("Version of the API being used"))

    @staticmethod
    def get_version(obj):
        #pylint:disable=unused-argument
        return __version__

class PlacesSuggestionSerializer(NoModelSerializer):

    description = serializers.CharField(
        help_text=_("Human-readable address string"))
    place_id = serializers.CharField(
        help_text=_("Placed identifier used to retrieve more"\
            " details"))


class PlacesSuggestionsSerializer(NoModelSerializer):

    count = serializers.IntegerField(
        help_text=_("Number of place suggestions returned"))
    results = PlacesSuggestionSerializer(many=True,
        help_text=_("List of place suggestions"))


class PlacesDetailSerializer(NoModelSerializer):

    street_number = serializers.CharField(required=False,
        help_text=_("Street number"))
    route = serializers.CharField(required=False,
        help_text=_("Street name or route"))
    postal_code = serializers.CharField(required=False,
        help_text=_("Postal code"))
    sublocality = serializers.CharField(required=False,
        help_text=_("Sublocality"))
    locality = serializers.CharField(required=False,
        help_text=_("Locality"))
    state = serializers.CharField(required=False,
        help_text=_("State"))
    state_code = serializers.CharField(required=False,
        help_text=_("State code"))
    country = serializers.CharField(required=False,
        help_text=_("Country"))
    country_code = serializers.CharField(required=False,
        help_text=_("Country code"))

    def __init__(self, *args, **kwargs):
        if args and args[0]:
            components = args[0].get('address_components', [])
            if len(components) > 0:
                address = {}
                for component in components:
                    if 'street_number' in component['types']:
                        address['street_number'] = component['long_name']
                    elif 'route' in component['types']:
                        address['route'] = component['long_name']
                    elif 'locality' in component['types']:
                        address['locality'] = component['long_name']
                    elif 'sublocality' in component['types']:
                        address['sublocality'] = component['long_name']
                    elif 'postal_code' in component['types']:
                        address['postal_code'] = component['long_name']
                    elif 'administrative_area_level_1' in component['types']:
                        address['state'] = component['long_name']
                        address['state_code'] = component['short_name']
                    elif 'country' in component['types']:
                        address['country'] = component['long_name']
                        address['country_code'] = component['short_name']
                args = (address,) + args[1:]
        super(PlacesDetailSerializer, self).__init__(*args, **kwargs)