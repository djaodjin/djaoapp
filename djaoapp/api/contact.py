# Copyright (c) 2020, DjaoDjin inc.
# see LICENSE
from __future__ import unicode_literals

import logging, socket, sys
from smtplib import SMTPException

from captcha import client
from captcha.constants import TEST_PRIVATE_KEY, TEST_PUBLIC_KEY
from deployutils.apps.django.compat import is_authenticated
from django.conf import settings
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.utils import six
from django.utils.deconstruct import deconstructible
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers
from rest_framework.generics import CreateAPIView
from rest_framework.response import Response
from saas.api.serializers import NoModelSerializer
from saas.mixins import ProviderMixin
from saas.models import Organization
from saas.utils import full_name_natural_split

from ..signals import contact_requested
from ..thread_locals import get_current_app


LOGGER = logging.getLogger(__name__)


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
        frm = sys._getframe()
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

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        validator = ReCaptchaValidator()
        self.validators.append(validator)


class ContactUsSerializer(NoModelSerializer):

    full_name = serializers.CharField()
    email = serializers.EmailField()
    message = serializers.CharField(required=False)

    def __init__(self, *args, **kwargs):
        super(ContactUsSerializer, self).__init__(*args, **kwargs)
        if not kwargs.get('initial', {}).get('email', None):
            if getattr(get_current_app(), 'contact_requires_recaptcha', False):
                self.fields['g-recaptcha-response'] = ReCaptchaField()


class ContactUsAPIView(ProviderMixin, CreateAPIView):
    """
    Sends a contact-us message

    Emails a free form contact-us message from a customer to the provider

    **Tags: auth

    **Example

    .. code-block:: http

        POST /api/contact/ HTTP/1.1

    .. code-block:: json

        {
          "email": "joe+1@example.com",
          "full_name": "Joe Card1",
          "message": "Can I request a demo?"
        }

    responds

    .. code-block:: json

        {
            "details": "Your request has been sent. We will reply within\
24 hours. Thank you."
        }
    """
    serializer_class = ContactUsSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if is_authenticated(self.request):
            user = self.request.user
        else:
            user_model = get_user_model()
            email = serializer.validated_data.get('email', None)
            try:
                user = user_model.objects.get(email=email)
            except user_model.DoesNotExist:
                #pylint:disable=unused-variable
                first_name, mid, last_name = full_name_natural_split(
                    serializer.validated_data.get('full_name', None))
                user = user_model(
                    email=email, first_name=first_name, last_name=last_name)
        message = serializer.validated_data.get('message', '')
        provider = serializer.validated_data.get('provider', self.provider)
        items = []
        for key, value in six.iteritems(serializer.data):
            if value and not (key in serializer.validated_data or
                key in ('captcha', 'g-recaptcha-response',
                    'csrfmiddlewaretoken')):
                items += [(key, value)]
        if message:
            items += [("Message", message)]
        if not user.email:
            return Response({"details":
    _("Thank you for the feedback. Please feel free to leave your contact"\
" information next time so we can serve you better.")})
        if provider:
            provider = get_object_or_404(Organization, slug=provider)
        else:
            provider = self.provider
        try:
            contact_requested.send(
                sender=__name__, provider=provider,
                user=user, reason=items, request=self.request)
            return Response({"details":
_("Your request has been sent. We will reply within 24 hours. Thank you.")})
        except (SMTPException, socket.error) as err:
            LOGGER.exception("%s on page %s",
                err, self.request.get_raw_uri())
            return Response({"details":
_("Sorry, there was an issue sending your request for information"\
" to '%(full_name)s &lt;%(email)s&gt;'.") % {
    'full_name': provider.full_name, 'email': provider.email}})
