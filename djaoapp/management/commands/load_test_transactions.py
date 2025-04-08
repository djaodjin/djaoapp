# Copyright (c) 2025, DjaoDjin inc.
# see LICENSE

import datetime, logging, os, random
from collections import defaultdict

from django.conf import settings
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db.utils import IntegrityError
from django.template.defaultfilters import slugify
from faker import Faker
from multitier.thread_locals import set_current_site
from multitier.utils import get_site_model
from saas.models import (CartItem, Charge, ChargeItem, Coupon, Organization,
    Plan, Subscription, Transaction)
from saas import humanize, settings as saas_settings
from saas.utils import datetime_or_now, generate_random_slug
from saas import signals as saas_signals
from signup import signals as signup_signals

from ...compat import timezone_or_utc


LOGGER = logging.getLogger(__name__)


class DisableSignals(object):
    def __init__(self, disabled_signals):
        self.stashed_signals = defaultdict(list)
        self.disabled_signals = disabled_signals

    def __enter__(self):
        for signal in self.disabled_signals:
            self.disconnect(signal)

    def __exit__(self, exc_type, exc_val, exc_tb):
        for signal in list(self.stashed_signals):
            self.reconnect(signal)

    def disconnect(self, signal):
        self.stashed_signals[signal] = signal.receivers
        signal.receivers = []

    def reconnect(self, signal):
        signal.receivers = self.stashed_signals.get(signal, [])
        del self.stashed_signals[signal]


class Command(BaseCommand):
    help = "Load the database with random transactions (testing purposes)."

    USE_OF_SERVICE = 0
    PAY_BALANCE = 1
    REDEEM = 2
    REFUND = 3
    CHARGEBACK = 4
    WRITEOFF = 5

    def add_arguments(self, parser):
        parser.add_argument('--database',
            action='store', dest='database', default=None,
            help='use the specified database')
        parser.add_argument('--provider',
            action='store', dest='provider', default=settings.APP_NAME,
            help='create sample subscribers on this provider')
        parser.add_argument('--coupon',
            action='store', dest='coupon', default=None,
            help='create uses of the specified coupon')
        parser.add_argument('--profile-pictures',
            action='store', dest='profile_pictures', default=None,
            help='directory where random profile pictures are stored')

    def handle(self, *args, **options):
        sigs = [
            saas_signals.charge_updated,
            saas_signals.claim_code_generated,
            saas_signals.card_updated,
            saas_signals.expires_soon,
            saas_signals.order_executed,
            saas_signals.profile_updated,
            saas_signals.role_grant_created,
            saas_signals.role_request_created,
            saas_signals.role_grant_accepted,
            saas_signals.subscription_grant_accepted,
            saas_signals.subscription_grant_created,
            saas_signals.subscription_request_accepted,
            saas_signals.subscription_request_created,
            saas_signals.period_sales_report_created,
            signup_signals.user_registered,
            signup_signals.user_activated,
            signup_signals.user_reset_password
        ]
        # disabling email notifications
        with DisableSignals(sigs):
            self._handle(*args, **options)

    def _handle(self, *args, **options):
        # forces to use the fake processor. We don't want to take a lot
        # of time to go to Stripe to create test charges.
        settings.SAAS['PROCESSOR']['BACKEND'] = \
            'saas.backends.fake_processor.FakeProcessorBackend'

        db_name = options['database']
        if db_name:
            set_current_site(get_site_model().objects.get(
                db_name=db_name),
                path_prefix='')
        else:
            set_current_site(get_site_model().objects.get(
                slug=settings.APP_NAME),
                path_prefix='')
        now = datetime.datetime.utcnow().replace(tzinfo=timezone_or_utc())
        from_date = now
        from_date = datetime.datetime(
            year=from_date.year, month=from_date.month, day=1)
        if args:
            from_date = datetime.datetime.strptime(
                args[0], '%Y-%m-%d')
        provider = Organization.objects.get(slug=options['provider'])
        processor = Organization.objects.get(pk=saas_settings.PROCESSOR_ID)
        self.generate_optional_plans(provider)
        self.generate_coupons(provider)
        self.generate_transactions(provider, processor, from_date, now,
            profile_pictures_dir=options['profile_pictures'])
        subscriber = Organization.objects.filter(
            slug__startswith='demo').first()
        if subscriber:
            self.generate_subscriptions(subscriber, provider)
        coupon_code = options['coupon']
        if coupon_code:
            self.generate_coupon_uses(coupon_code, provider=provider)

    def demo_plans(self, provider):
        return Plan.objects.filter(
            organization=provider, period_amount__gt=0)

    def generate_optional_plans(self, provider):
        # Create a few standard ones that don't interfer
        # with the livedemo-db.json fixtures
        if not self.demo_plans(provider).exists():
            Plan.objects.create(
                slug='demo-basic', title="Basic", period_amount=2000,
                organization=provider)
            Plan.objects.create(
                slug='demo-premium', title="Premium", period_amount=5000,
                organization=provider)
            Plan.objects.create(
                slug='demo-deluxe', title="Deluxe", period_amount=12000,
                organization=provider)


    def generate_coupons(self, provider, nb_coupons=None):
        if nb_coupons is None:
            nb_coupons = settings.REST_FRAMEWORK['PAGE_SIZE'] * 4
        self.stdout.write("%d coupons\n" % nb_coupons)
        for _ in range(0, nb_coupons):
            coupon_percent = random.randint(1, 100)
            coupon_code = "%s%d" % ("".join([
                random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
                for _ in range(0, 3)]), coupon_percent)
            Coupon.objects.get_or_create(code=coupon_code,
                defaults={'discount_value': coupon_percent * 100,
                'organization': provider})

    def generate_coupon_uses(self, coupon_code, provider=None, nb_uses=None):
        user_model = get_user_model()
        if nb_uses is None:
            nb_uses = settings.REST_FRAMEWORK['PAGE_SIZE'] * 4
        self.stdout.write("%d uses of coupon %s\n" % (nb_uses, coupon_code))
        if provider:
            kwargs = {'organization': provider}
        coupon = Coupon.objects.filter(code=coupon_code, **kwargs).first()
        if coupon:
            plans = list(self.demo_plans(coupon.organization))
            for _ in range(0, nb_uses):
                try:
                    user = user_model.objects.get(
                        pk=random.randint(1, user_model.objects.count() - 1))
                    if len(plans) > 1:
                        plan = plans[random.randint(1, len(plans) - 1)]
                    else:
                        plan = plans[0]
                    CartItem.objects.create(
                        user=user, coupon=coupon, plan=plan, recorded=True)
                except user_model.DoesNotExist:
                    pass


    def generate_subscriptions(self, subscriber, provider,
                               nb_subscriptions=None, fake=None):
        at_time = datetime_or_now()
        if nb_subscriptions is None:
            nb_subscriptions = settings.REST_FRAMEWORK['PAGE_SIZE'] * 4
        self.stdout.write("%d subscriptions for %s (to check paginator)\n" % (
            nb_subscriptions, subscriber))
        nb_plans = self.demo_plans(provider).count()
        if not fake:
            fake = Faker()
        for _ in range(0, nb_subscriptions):
            rank = random.randint(1, nb_plans - 1)
            plan = self.demo_plans(provider).order_by('pk')[rank]
            created_at = datetime_or_now(fake.date_time_between_dates(
                datetime_start=at_time - datetime.timedelta(365),
                datetime_end=at_time + datetime.timedelta(365)))
            Subscription.objects.get_or_create(
                organization=subscriber, plan=plan,
                defaults={
                    'created_at': created_at,
                    'ends_at': created_at + datetime.timedelta(30)
                })

    def generate_transactions(self, provider, processor, from_date, ends_at,
                              fake=None, profile_pictures_dir=None):
        """
        Create Income transactions that represents a growing bussiness.
        """
        #pylint: disable=too-many-locals,too-many-arguments
        from saas.metrics.base import month_periods # avoid import loop
        if not fake:
            fake = Faker()
        user_model = get_user_model()
        at_time = datetime_or_now()
        # Load list of profile pcitures
        profile_pictures_males = []
        profile_pictures_females = []
        if profile_pictures_dir:
            for picture_name in os.listdir(profile_pictures_dir):
                if picture_name.startswith("1"):
                    profile_pictures_males += [
                        "/assets/img/profiles/%s" % picture_name]
                else:
                    profile_pictures_females += [
                        "/assets/img/profiles/%s" % picture_name]
        nb_plans = self.demo_plans(provider).count()
        plans = list(self.demo_plans(provider))
        for end_period in month_periods(from_date=from_date):
            #pylint:disable=too-many-nested-blocks
            nb_new_customers = random.randint(0, 9)
            for _ in range(nb_new_customers):
                plan = plans[random.randint(0, nb_plans - 1)]
                created = False
                trials = 0
                while not created:
                    try:
                        picture = None
                        if random.randint(0, 1):
                            first_name = fake.first_name_male()
                            if profile_pictures_males:
                                picture = profile_pictures_males[
                                    random.randint(
                                        0, len(profile_pictures_males) - 1)]
                        else:
                            first_name = fake.first_name_female()
                            if profile_pictures_females:
                                picture = profile_pictures_females[
                                    random.randint(
                                        0, len(profile_pictures_females) - 1)]
                        last_name = fake.last_name()
                        full_name = "%s %s" % (first_name, last_name)
                        slug = slugify('demo%d' % random.randint(1, 1000))
                        email = "%s@%s" % (slug, fake.domain_name())
                        customer, created = Organization.objects.get_or_create(
                            slug=slug,
                            full_name=full_name,
                            email=email,
                            phone=fake.phone_number(),
                            street_address=fake.street_address(),
                            locality=fake.city(),
                            postal_code=fake.postcode(),
                            region=fake.state_abbr(),
                            country=fake.country_code(),
                            picture=picture)
                        last_login = datetime_or_now(
                            fake.date_time_between_dates(
                              datetime_start=at_time - datetime.timedelta(365),
                              datetime_end=at_time))
                        user, created = user_model.objects.get_or_create(
                            username=slug,
                            email=email,
                            first_name=first_name,
                            last_name=last_name,
                            last_login=last_login)
                        customer.add_manager(user, at_time=end_period)
                    #pylint: disable=catching-non-exception
                    except IntegrityError:
                        trials = trials + 1
                        if trials > 10:
                            raise RuntimeError(
                         'impossible to create a new customer after 10 trials.')
                Organization.objects.filter(pk=customer.id).update(
                    created_at=end_period)
                subscription = Subscription.objects.create(
                    organization=customer, plan=plan,
                    ends_at=ends_at + datetime.timedelta(days=31))
                Subscription.objects.filter(
                    pk=subscription.id).update(created_at=end_period)
            # Insert some churn in %
            churn_rate = 2
            demo_subscriptions = Subscription.objects.filter(
                organization__slug__startswith='demo',
                plan__organization=provider)
            nb_churn_customers = (demo_subscriptions.count()
                * churn_rate // 100)
            subscriptions = random.sample(list(demo_subscriptions),
                demo_subscriptions.count() - nb_churn_customers)
            for subscription in subscriptions:
                nb_periods = random.randint(1, 6)
                subscription.ends_at = subscription.plan.end_of_period(
                    subscription.ends_at,
                    nb_periods=nb_periods)
                transaction_item = Transaction.objects.new_subscription_order(
                    subscription,
                    amount=subscription.plan.period_amount * nb_periods,
                    descr=humanize.describe_buy_periods(
                        subscription.plan, subscription.ends_at, nb_periods),
                    created_at=end_period)
                if transaction_item.dest_amount < 50:
                    continue
                subscription.save()
                transaction_item.orig_amount = transaction_item.dest_amount
                transaction_item.orig_unit = transaction_item.dest_unit
                transaction_item.save()
                charge = Charge.objects.create(
                    created_at=transaction_item.created_at,
                    amount=transaction_item.dest_amount,
                    customer=subscription.organization,
                    description=humanize.DESCRIBE_CHARGED_CARD % {
                        'charge': generate_random_slug(prefix='ch_'),
                        'organization': subscription.organization
                    },
                    last4=1241,
                    exp_date=datetime_or_now(),
                    processor=processor,
                    processor_key="ch_%s" % str(transaction_item.pk),
                    state=Charge.CREATED)
                charge.created_at = transaction_item.created_at
                charge.save()
                ChargeItem.objects.create(
                    invoiced=transaction_item, charge=charge)
                charge.payment_successful()
            churned = demo_subscriptions.exclude(
                pk__in=[subscription.pk for subscription in subscriptions])
            for subscription in churned:
                subscription.ends_at = end_period
                subscription.save()
            self.stdout.write("%d new and %d churned customers at %s\n" % (
                nb_new_customers, nb_churn_customers, end_period))
