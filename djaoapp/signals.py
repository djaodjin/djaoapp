# Copyright (c) 2019, DjaoDjin inc.
# see LICENSE

import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import Signal, receiver
from django.utils.translation import ugettext_lazy as _
from extended_templates.backends import get_email_backend
from multitier.thread_locals import get_current_site
from saas import settings as saas_settings
from saas.models import CartItem, get_broker
from saas.signals import (charge_updated, claim_code_generated, card_updated,
    expires_soon, order_executed, organization_updated,
    user_relation_added, user_relation_requested, role_grant_accepted,
    subscription_grant_accepted, subscription_grant_created,
    subscription_request_accepted, subscription_request_created,
    weekly_sales_report_created)
from signup.settings import NOTIFICATIONS_OPT_OUT
from signup.models import Contact
from signup.signals import (user_registered, user_activated,
    user_reset_password, user_verification)
from signup.utils import (has_invalid_password,
    printable_name as user_printable_name)

from .compat import reverse
from .thread_locals import get_current_app

#pylint: disable=unused-argument
#pylint: disable=protected-access

LOGGER = logging.getLogger(__name__)
SEND_EMAIL = settings.SEND_EMAIL

contact_requested = Signal( #pylint:disable=invalid-name
    providing_args=["provider", "user", "reason"])


def _notified_recipients(organization, notification_slug, originated_by=None):
    """
    Returns the organization email or the managers email if the organization
    does not have an e-mail set.
    """

    managers = organization.with_role(saas_settings.MANAGER)
    if originated_by:
        managers = managers.exclude(email=originated_by.email)
    # checking whether those users are subscribed to the notification
    if NOTIFICATIONS_OPT_OUT:
        filtered = managers.exclude(notifications__slug=notification_slug)
    else:
        filtered = managers.filter(notifications__slug=notification_slug)
    recipients = [notified.email for notified in filtered]
    bcc = []
    return recipients, bcc


def get_user_context(user):
    if user:
        return {
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'printable_name': user_printable_name(user)
        }
    broker = get_broker()
    return {
        'username': broker.slug,
        'email': broker.email,
        'first_name': broker.full_name,
        'printable_name': broker.printable_name
    }


# We insure the method is only bounded once no matter how many times
# this module is loaded by using a dispatch_uid as advised here:
#   https://docs.djangoproject.com/en/dev/topics/signals/
@receiver(contact_requested, dispatch_uid="contact_requested_notice")
def contact_requested_notice(sender, provider, user, reason, **kwargs):
    """
    Someone requested information through the contact form.
    """
    if provider is None:
        provider = get_broker()
    app = get_current_app()
    context = {'broker': get_broker(), 'app': app,
        'provider': provider, 'user': get_user_context(user),
        'reason': reason}
    if user.pk is not None:
        context.update({'urls': {'user': {'profile':
            reverse('users_profile', args=(user,))}}})
    recipients, bcc = _notified_recipients(provider, "contact_requested_notice")
    # We are hanlding `recipients` a bit differently here because contact
    # requests are usually meant to be sent to a ticketing system.
    if provider.email:
        recipients = [provider.email]
        bcc = recipients + bcc
    LOGGER.debug("[signal] contact_requested_notice(provider=%s, user=%s)",
        provider, user)
    if SEND_EMAIL and recipients:
        site = get_current_site()
        get_email_backend(connection=site.get_email_connection()).send(
            from_email=site.get_from_email(), reply_to=user.email,
            recipients=recipients, bcc=bcc,
            template='notification/user_contact.eml',
            context=context)


# We insure the method is only bounded once no matter how many times
# this module is loaded by using a dispatch_uid as advised here:
#   https://docs.djangoproject.com/en/dev/topics/signals/
@receiver(user_registered, dispatch_uid="user_registered_notice")
def user_registered_notice(sender, user, **kwargs):
    """
    A new user has registered (frictionless or completely)
    """
    LOGGER.debug("[signal] user_registered_notice(user=%s)", user)
    if not SEND_EMAIL:
        return
    broker = get_broker()
    app = get_current_app()
    site = get_current_site()
    if hasattr(app, 'welcome_email') and app.welcome_email:
        back_url = site.as_absolute_uri()
        get_email_backend(connection=site.get_email_connection()).send(
            from_email=site.get_from_email(), recipients=[user.email],
            template='notification/user_welcome.eml',
            context={'broker': get_broker(), 'app': app,
                'user': get_user_context(user),
                'back_url': back_url})
    recipients, bcc = _notified_recipients(broker, "user_registered_notice")
    if recipients:
        get_email_backend(connection=site.get_email_connection()).send(
            from_email=site.get_from_email(), recipients=recipients, bcc=bcc,
            template='notification/user_registered.eml',
            context={'broker': get_broker(), 'app': app,
                'user': get_user_context(user)})


# We insure the method is only bounded once no matter how many times
# this module is loaded by using a dispatch_uid as advised here:
#   https://docs.djangoproject.com/en/dev/topics/signals/
@receiver(user_activated, dispatch_uid="user_activated_notice")
def user_activated_notice(sender, user, verification_key, request, **kwargs):
    """
    A new user has activated his account. We have a complete profile
    and active email address now.
    """
    broker = get_broker()
    recipients, bcc = _notified_recipients(broker, "user_activated_notice")
    LOGGER.debug("[signal] user_activated_notice(user=%s, verification_key=%s)",
        user, verification_key)
    if SEND_EMAIL and recipients:
        site = get_current_site()
        app = get_current_app()
        get_email_backend(connection=site.get_email_connection()).send(
            from_email=site.get_from_email(), recipients=recipients, bcc=bcc,
            template='notification/user_activated.eml',
            context={'request': request, 'broker': get_broker(),
                     'app': app, 'user': get_user_context(user),
                     'urls':{
                         'user': {
                             'profile': site.as_absolute_uri(reverse(
                                 'users_profile', args=(user,)))}}})

# We insure the method is only bounded once no matter how many times
# this module is loaded by using a dispatch_uid as advised here:
#   https://docs.djangoproject.com/en/dev/topics/signals/
@receiver(user_verification, dispatch_uid="user_verification_notice")
def user_verification_notice(
        sender, user, request, back_url, expiration_days, **kwargs):
    """
    A user has reset her password.
    """
    broker = get_broker()
    LOGGER.debug("[signal] user_verification_notice(user=%s, back_url=%s,"\
        " expiration_days=%s)", user, back_url, expiration_days)
    if SEND_EMAIL:
        app = get_current_app()
        site = get_current_site()
        get_email_backend(connection=site.get_email_connection()).send(
            from_email=site.get_from_email(), recipients=[user.email],
            template='notification/verification.eml',
            context={'request': request,
                # Without ``app`` we donot set the color correctly in
                # in notification/base.html, thus ending with an error
                # in premailer.
                'broker': get_broker(), 'app': app, 'provider': broker,
                'user': get_user_context(user),
                'back_url': back_url, 'expiration_days': expiration_days})

# We insure the method is only bounded once no matter how many times
# this module is loaded by using a dispatch_uid as advised here:
#   https://docs.djangoproject.com/en/dev/topics/signals/
@receiver(user_reset_password, dispatch_uid="user_reset_password_notice")
def user_reset_password_notice(
        sender, user, request, back_url, expiration_days, **kwargs):
    """
    A user has reset her password.
    """
    LOGGER.debug("[signal] user_reset_password_notice(user=%s, back_url=%s,"\
        " expiration_days=%s)", user, back_url, expiration_days)
    if SEND_EMAIL:
        app = get_current_app()
        site = get_current_site()
        get_email_backend(connection=site.get_email_connection()).send(
            from_email=site.get_from_email(), recipients=[user.email],
            template='notification/password_reset.eml',
            context={'request': request,
                'broker': get_broker(), 'app': app,
                'back_url': back_url, 'expiration_days': expiration_days,
                'user': get_user_context(user)})


# We insure the method is only bounded once no matter how many times
# this module is loaded by using a dispatch_uid as advised here:
#   https://docs.djangoproject.com/en/dev/topics/signals/
@receiver(charge_updated, dispatch_uid="charge_updated")
def charge_updated_notice(sender, charge, user, **kwargs):
    from saas.mixins import get_charge_context # Avoid import loop
    recipients, bcc = _notified_recipients(charge.customer, "charge_updated")
    if charge.is_paid:
        LOGGER.debug("[signal] charge_updated_notice(charge=%s, user=%s)",
            charge, user)
        if SEND_EMAIL and recipients:
            broker = charge.broker
            broker_recipients, broker_bcc = _notified_recipients(
                broker, "charge_updated")
            context = get_charge_context(charge)
            if user and charge.created_by != user:
                context.update({'email_by': get_user_context(user)})
            app = get_current_app()
            site = get_current_site()
            context.update({
                'broker': get_broker(), 'app': app,
                'urls': {'charge': {'created_by':
                    reverse('users_profile', args=(charge.created_by,))}}})
            kwargs = {}
            if broker.email and broker.email != site.get_from_email():
                kwargs = {'reply_to': broker.email}
            get_email_backend(connection=site.get_email_connection()).send(
                from_email=site.get_from_email(), recipients=recipients,
                bcc=bcc + broker_recipients + broker_bcc,
                template='notification/charge_receipt.eml',
                context=context, **kwargs)


@receiver(card_updated, dispatch_uid="card_updated")
def card_updated_notice(sender, organization, user,
                        old_card, new_card, **kwargs):
    recipients, bcc = _notified_recipients(organization, 'card_updated')
    LOGGER.debug("[signal] card_updated_notice(organization=%s, user=%s,"\
        "old_card=%s, new_card=%s)", organization, user, old_card, new_card)
    if SEND_EMAIL and recipients:
        broker = get_broker()
        broker_recipients, broker_bcc = _notified_recipients(broker,
            'card_updated')
        app = get_current_app()
        site = get_current_site()
        get_email_backend(connection=site.get_email_connection()).send(
            from_email=site.get_from_email(), recipients=recipients,
            bcc=bcc + broker_recipients + broker_bcc,
            template='notification/card_updated.eml',
            context={
                'broker': broker, 'app': app,
                'organization': organization, 'user': get_user_context(user),
                'old_card': old_card, 'new_card': new_card})


# We insure the method is only bounded once no matter how many times
# this module is loaded by using a dispatch_uid as advised here:
#   https://docs.djangoproject.com/en/dev/topics/signals/
@receiver(order_executed, dispatch_uid="order_executed")
def order_executed_notice(sender, invoiced_items, user, **kwargs):
    invoiced_items = list(invoiced_items)
    organization = (invoiced_items[0].dest_organization
        if invoiced_items else None)
    recipients, bcc = _notified_recipients(organization, 'order_executed')
    LOGGER.debug("[signal] order_executed_notice(invoiced_items=%s, user=%s)",
        [invoiced_item.pk for invoiced_item in invoiced_items], user)
    if SEND_EMAIL and recipients:
        broker = get_broker()
        broker_recipients, broker_bcc = _notified_recipients(broker,
            'order_executed')
        app = get_current_app()
        site = get_current_site()
        context = {'broker': broker, 'app': app, 'provider': broker,
            'organization': organization, 'invoiced_items': invoiced_items,
            'created_by': user}
        if user:
            context.update({'urls': {'order': {'created_by':
                reverse('users_profile', args=(user,))}}})
        kwargs = {}
        if broker.email and broker.email != site.get_from_email():
            kwargs = {'reply_to': broker.email}
        get_email_backend(connection=site.get_email_connection()).send(
            from_email=site.get_from_email(), recipients=recipients,
            bcc=bcc + broker_recipients + broker_bcc,
            template='notification/order_executed.eml',
            context=context, **kwargs)


@receiver(claim_code_generated, dispatch_uid="claim_code_generated")
def claim_code_notice(sender, subscriber, claim_code, user, **kwargs):
    cart_items = CartItem.objects.by_claim_code(claim_code)
    provider = CartItem.objects.provider(cart_items)
    LOGGER.debug("[signal] claim_code_notice(subscriber=%s, claim_code=%s,"\
        " user=%s)", subscriber, claim_code, user)
    if SEND_EMAIL:
        # XXX We don't use `_notified_recipients` here as an attempt
        # only have one person respnsible for using the claim code.
        site = get_current_site()
        app = get_current_app()
        get_email_backend(connection=site.get_email_connection()).send(
            from_email=site.get_from_email(), recipients=[subscriber.email],
            reply_to=user.email,
            template='notification/claim_code_generated.eml',
            context={
                'broker': get_broker(), 'app': app,
                'urls': {'cart': site.as_absolute_uri(reverse('saas_cart'))},
                'subscriber': subscriber, 'provider': provider,
                'claim_code': claim_code, 'cart_items': cart_items,
                'user': get_user_context(user)})


@receiver(organization_updated, dispatch_uid="organization_updated")
def organization_updated_notice(sender, organization, changes, user, **kwargs):
    if not changes:
        return
    recipients, _ = _notified_recipients(organization, 'organization_updated')
    LOGGER.info("%s updated", organization,
        extra={'event': 'update-fields', 'organization': str(organization),
               'changes': changes})
    if SEND_EMAIL and recipients:
        broker = get_broker()
        site = get_current_site()
        app = get_current_app()
        broker_recipients, broker_bcc = _notified_recipients(
        broker, 'organization_updated')
        kwargs = {}
        if broker.email and broker.email != site.get_from_email():
            kwargs = {'reply_to': broker.email}
        get_email_backend(connection=site.get_email_connection()).send(
            from_email=site.get_from_email(), recipients=recipients,
            bcc=broker_recipients + broker_bcc,
            template='notification/organization_updated.eml',
            context={
                'broker': broker, 'app': app,
                'user': get_user_context(user),
                'organization': organization, 'changes': changes,
                'urls':{
                    'user': {
                        'profile': site.as_absolute_uri(reverse(
                            'users_profile', args=(user,)))},
                    'organization': {
                        'profile': site.as_absolute_uri(reverse(
                            'saas_organization_profile', args=(organization,)))}
                }}, **kwargs)


# We insure the method is only bounded once no matter how many times
# this module is loaded by using a dispatch_uid as advised here:
#   https://docs.djangoproject.com/en/dev/topics/signals/
@receiver(user_relation_added, dispatch_uid="user_relation_added")
def user_relation_added_notice(sender, role, reason=None, **kwargs):
    user = role.user
    organization = role.organization
    if user.email != organization.email:
        if user.email:
            back_url = reverse('organization_app', args=(organization,))
            if role.grant_key:
                back_url = reverse('saas_role_grant_accept',
                    args=(role.grant_key,))
            if has_invalid_password(user):
                reason = _("You have been invited to create an account"\
                    " to join %(organization)s.") % {
                    'organization': role.organization.printable_name}
                Contact.objects.update_or_create_token(
                    user, reason=reason)
            site = get_current_site()
            app = get_current_app()
            context = {
                'broker': get_broker(), 'app': app,
                'back_url': site.as_absolute_uri(back_url),
                'organization': organization,
                'role': role.role_description.title,
                'reason': reason if reason is not None else "",
                'user': get_user_context(user)
            }
            reply_to = organization.email
            request_user = kwargs.get('request_user', None)
            if request_user:
                reply_to = request_user.email
                context.update({'request_user': get_user_context(request_user)})
            LOGGER.debug("[signal] user_relation_added_notice(role=%s,"\
                " reason=%s)", role, reason)
            if SEND_EMAIL:
                get_email_backend(connection=site.get_email_connection()).send(
                    from_email=site.get_from_email(), recipients=[user.email],
                    reply_to=reply_to,
                    template=[
                        ("notification/%s_role_added.eml"
                         % role.role_description.slug),
                        "notification/role_added.eml"],
                    context=context)
        else:
            LOGGER.warning(
                "%s will not be notified being added to %s"\
                " because e-mail address is invalid.", user, organization)


# We insure the method is only bounded once no matter how many times
# this module is loaded by using a dispatch_uid as advised here:
#   https://docs.djangoproject.com/en/dev/topics/signals/
@receiver(user_relation_requested, dispatch_uid="user_relation_requested")
def user_relation_requested_notice(sender, organization, user,
                                   reason=None, **kwargs):
    if user.email != organization.email:
        if user.email:
            site = get_current_site()
            app = get_current_app()
            LOGGER.debug("[signal] user_relation_requested_notice("\
                "organization=%s, user=%s, reason=%s)",
                organization, user, reason)
            if SEND_EMAIL:
                get_email_backend(connection=site.get_email_connection()).send(
                    from_email=site.get_from_email(),
                    recipients=[organization.email],
                    reply_to=user.email,
                    template='notification/user_relation_requested.eml',
                    context={
                        'broker': get_broker(), 'app': app,
                        'back_url': site.as_absolute_uri(
                            reverse('saas_role_list', args=(organization,))),
                        'organization': organization,
                        'reason': reason if reason is not None else "",
                        'user': get_user_context(user)})
        else:
            LOGGER.warning(
                "%s will not be notified of role request to %s"\
                " because e-mail address is invalid.", user, organization)


# We insure the method is only bounded once no matter how many times
# this module is loaded by using a dispatch_uid as advised here:
#   https://docs.djangoproject.com/en/dev/topics/signals/
@receiver(role_grant_accepted, dispatch_uid="role_grant_accepted")
def role_grant_accepted_notice(sender, role, grant_key, request=None, **kwargs):
    LOGGER.debug("[signal] role_grant_accepted_notice("\
        " role=%s, grant_key=%s)", role, grant_key)
    originated_by = request.user if request else None
    user_context = get_user_context(originated_by)
    recipients, bcc = _notified_recipients(
        role.organization, "role_grant_accepted_notice",
        originated_by=originated_by)
    if SEND_EMAIL and recipients:
        site = get_current_site()
        app = get_current_app()
        get_email_backend(connection=site.get_email_connection()).send(
            from_email=site.get_from_email(),
            recipients=recipients, bcc=bcc,
            reply_to=user_context['email'],
            template='notification/role_grant_accepted.eml',
            context={
                'broker': get_broker(), 'app': app,
                'back_url': site.as_absolute_uri(reverse('saas_role_detail',
                    args=(role.organization, role.role_description))),
                'organization': role.organization,
                'role': role.role_description.title,
                'user': user_context})


# We insure the method is only bounded once no matter how many times
# this module is loaded by using a dispatch_uid as advised here:
#   https://docs.djangoproject.com/en/dev/topics/signals/
@receiver(subscription_grant_accepted,
          dispatch_uid="subscription_grant_accepted")
def subscribe_grant_accepted_notice(sender, subscription, grant_key,
                                       request=None, **kwargs):
    provider = subscription.plan.organization
    originated_by = request.user if request else None
    recipients, bcc = _notified_recipients(provider,
        "subscribe_grant_accepted_notice",
        originated_by=originated_by)
    LOGGER.debug("[signal] subscribe_grant_accepted_notice("\
        " subscription=%s, grant_key=%s)", subscription, grant_key)
    if SEND_EMAIL and recipients:
        site = get_current_site()
        app = get_current_app()
        user_context = get_user_context(originated_by)
        get_email_backend(connection=site.get_email_connection()).send(
            from_email=site.get_from_email(),
            recipients=recipients, bcc=bcc,
            reply_to=user_context['email'],
            template='notification/subscription_grant_accepted.eml',
            context={
                'broker': get_broker(), 'app': app,
                'back_url': site.as_absolute_uri(reverse('organization_app',
                    args=(provider,))),
                'organization': subscription.organization,
                'plan': subscription.plan,
                'user': user_context})


# We insure the method is only bounded once no matter how many times
# this module is loaded by using a dispatch_uid as advised here:
#   https://docs.djangoproject.com/en/dev/topics/signals/
@receiver(subscription_grant_created, dispatch_uid="subscription_grant_created")
def subscribe_grant_created_notice(sender, subscription, reason=None,
                                   invite=False, request=None, **kwargs):
    #pylint:disable=too-many-locals
    if subscription.grant_key:
        user_context = get_user_context(request.user if request else None)
        organization = subscription.organization
        back_url_base = reverse('subscription_grant_accept',
            args=(organization, subscription.grant_key,))
        LOGGER.debug("[signal] subscribe_grant_created_notice("\
            " subscription=%s, reason=%s, invite=%s)",
            subscription, reason, invite)
        # We don't use `_notified_recipients` because
        #    1. We need the actual User object to update/create a Contact
        #    2. We should not send to the organization e-mail address
        #       because the e-mail there might not be linked to a manager.
        managers = organization.with_role(saas_settings.MANAGER)
        emails = kwargs.get('emails', None)
        if emails:
            managers = managers.filter(email__in=emails)
        if not managers:
            LOGGER.warning(
                "%s will not be notified of a subscription grant to %s"\
                " because there are no managers to send e-mails to.",
                organization, subscription.plan)
        for manager in managers:
            # The following line could as well be `if invite:`
            if has_invalid_password(manager):
                # The User is already in the system but the account
                # has never been activated.
                contact, _ = Contact.objects.update_or_create_token(manager)
                back_url = "%s?next=%s" % (reverse('registration_activate',
                    args=(contact.verification_key,)), back_url_base)
            else:
                back_url = back_url_base
            LOGGER.debug("[signal] would send subscribe_grant_created_notice"\
                " for subscription '%s' to '%s'", subscription, manager.email)
            if SEND_EMAIL:
                site = get_current_site()
                app = get_current_app()
                get_email_backend(connection=site.get_email_connection()).send(
                    from_email=site.get_from_email(),
                    recipients=[manager.email],
                    reply_to=user_context['email'],
                    template='notification/subscription_grant_created.eml',
                    context={
                        'broker': get_broker(), 'app': app,
                        'back_url': site.as_absolute_uri(back_url),
                        'organization': organization,
                        'plan': subscription.plan,
                        'reason': reason if reason is not None else "",
                        'invite': invite,
                        'user': user_context})


# We insure the method is only bounded once no matter how many times
# this module is loaded by using a dispatch_uid as advised here:
#   https://docs.djangoproject.com/en/dev/topics/signals/
@receiver(subscription_request_accepted,
          dispatch_uid="subscription_request_accepted")
def subscribe_req_accepted_notice(sender, subscription, request_key,
                                       request=None, **kwargs):
    subscriber = subscription.organization
    recipients, bcc = _notified_recipients(subscriber,
        "subscribe_req_accepted_notice")
    LOGGER.debug("[signal] subscribe_req_accepted_notice("\
        " subscription=%s, request_key=%s)", subscription, request_key)
    if SEND_EMAIL and recipients:
        site = get_current_site()
        app = get_current_app()
        user_context = get_user_context(request.user if request else None)
        get_email_backend(connection=site.get_email_connection()).send(
            from_email=site.get_from_email(),
            recipients=recipients, bcc=bcc,
            reply_to=user_context['email'],
            template='notification/subscription_request_accepted.eml',
            context={
                'broker': get_broker(), 'app': app,
                'back_url': site.as_absolute_uri(reverse('organization_app',
                    args=(subscriber,))),
                'organization': subscriber,
                'plan': subscription.plan,
                'user': user_context})


# We insure the method is only bounded once no matter how many times
# this module is loaded by using a dispatch_uid as advised here:
#   https://docs.djangoproject.com/en/dev/topics/signals/
@receiver(subscription_request_created,
          dispatch_uid="subscription_request_created")
def subscribe_req_created_notice(sender, subscription, reason=None,
                                      request=None, **kwargs):
    if subscription.request_key:
        user_context = get_user_context(request.user if request else None)
        organization = subscription.organization
        if organization.email:
            site = get_current_site()
            app = get_current_app()
            LOGGER.debug("[signal] subscribe_req_created_notice("\
                         " subscription=%s, reason=%s)", subscription, reason)
            if SEND_EMAIL:
                get_email_backend(connection=site.get_email_connection()).send(
                    from_email=site.get_from_email(),
                    recipients=[organization.email],
                    reply_to=user_context['email'],
                    template='notification/subscription_request_created.eml',
                    context={
                        'broker': get_broker(), 'app': app,
                        'back_url': site.as_absolute_uri(reverse(
                            'subscription_request_accept', args=(
                                organization, subscription.request_key,))),
                        'organization': organization,
                        'plan': subscription.plan,
                        'reason': reason if reason is not None else "",
                        'user': user_context})
        else:
            LOGGER.warning(
                "%s will not be notified of a subscription request to %s"\
                " because e-mail address is invalid.",
                organization, subscription.plan)


# We insure the method is only bounded once no matter how many times
# this module is loaded by using a dispatch_uid as advised here:
#   https://docs.djangoproject.com/en/dev/topics/signals/
@receiver(expires_soon, dispatch_uid="expires_soon")
def expires_soon_notice(sender, subscription, nb_days, **kwargs):
    LOGGER.debug("[signal] expires_soon_notice("\
                 " subscription=%s, nb_days=%s)", subscription, nb_days)
    recipients, bcc = _notified_recipients(subscription.organization,
        'expires_soon')
    if SEND_EMAIL and recipients:
        broker = get_broker()
        broker_recipients, broker_bcc = _notified_recipients(
            broker, 'expires_soon')
        site = get_current_site()
        app = get_current_app()
        back_url = "%s?plan=%s" % (site.as_absolute_uri(
            reverse('saas_organization_cart',
                args=(subscription.organization,))), subscription.plan)
        kwargs = {}
        if broker.email and broker.email != site.get_from_email():
            kwargs = {'reply_to': broker.email}
        get_email_backend(connection=site.get_email_connection()).send(
            from_email=site.get_from_email(),
            recipients=recipients,
            bcc=bcc + broker_recipients + broker_bcc,
            template='notification/expires_soon.eml',
            context={'broker': get_broker(), 'app': app,
                'back_url': back_url, 'nb_days': nb_days,
                'organization': subscription.organization,
                'plan': subscription.plan,
                'provider': subscription.plan.organization}, **kwargs)


# We insure the method is only bounded once no matter how many times
# this module is loaded by using a dispatch_uid as advised here:
#   https://docs.djangoproject.com/en/dev/topics/signals/
@receiver(weekly_sales_report_created,
          dispatch_uid="weekly_sales_report_created")
def weekly_sales_report_notice(sender, provider, dates, data, **kwargs):
    recipients, bcc = _notified_recipients(
        provider, "weekly_sales_report_created")
    if SEND_EMAIL and recipients:
        app = get_current_app()
        site = get_current_site()
        frm = site.get_from_email()
        # if from is empty the following command will fail
        if not frm:
            raise Exception(
                "Please fill the DEFAULT_FROM_EMAIL option in settings")

        prev_week, _ = dates
        last_sunday = prev_week[-1]
        date = last_sunday.strftime("%A %b %d, %Y")

        # XXX using the provider in templates is incorrect. "Any questions
        # or comments..." should show DjaoDjin support email address.
        get_email_backend(connection=site.get_email_connection()).send(
            from_email=frm, recipients=recipients,
            bcc=bcc, template='notification/weekly_sales_report_created.eml',
            context={'broker': get_broker(), 'provider': provider,
                # Without ``app`` we don't set the color correctly in
                # in notification/base.html, thus ending with an error
                # in premailer.
                'app': app, 'table': data, 'date': date})


@receiver(post_save, sender=get_user_model())
def on_user_post_save(sender, instance, created, raw, **kwargs):
    #pylint:disable=unused-argument
    if created and instance.is_superuser:
        get_broker().add_manager(instance)
