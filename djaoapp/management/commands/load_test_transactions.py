# Copyright (c) 2018, DjaoDjin inc.
# see LICENSE

import datetime, logging, random

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.utils import IntegrityError
from django.template.defaultfilters import slugify
from django.utils.timezone import utc
from multitier.thread_locals import set_current_site
from multitier.utils import get_site_model
from saas.models import Transaction
from saas.utils import datetime_or_now
from saas.settings import PROCESSOR_ID

from ... import settings

# disabling email notifications
settings.SEND_EMAIL = False

LOGGER = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Load the database with random transactions (testing purposes)."

    USE_OF_SERVICE = 0
    PAY_BALANCE = 1
    REDEEM = 2
    REFUND = 3
    CHARGEBACK = 4
    WRITEOFF = 5

    FIRST_NAMES = (
        'Anthony',
        'Alexander',
        'Alexis',
        'Alicia',
        'Ashley',
        'Benjamin',
        'Bruce',
        'Chloe',
        'Christopher',
        'Daniel',
        'David',
        'Edward',
        'Emily',
        'Emma',
        'Ethan',
        'Grace',
        'Isabella',
        'Jacob',
        'James',
        'Jayden',
        'Jennifer',
        'John',
        'Julia',
        'Lily',
        'Lucie',
        'Luis',
        'Matthew',
        'Michael',
        'Olivia',
        'Ryan',
        'Samantha',
        'Samuel',
        'Scott',
        'Sophia',
        'Williom',
        )

    LAST_NAMES = (
        'Smith',
        'Johnson',
        'Williams',
        'Jones',
        'Brown',
        'Davis',
        'Miller',
        'Wilson',
        'Moore',
        'Taylor',
        'Anderson',
        'Thomas',
        'Jackson',
        'White',
        'Harris',
        'Martin',
        'Thompson',
        'Garcia',
        'Martinez',
        'Robinson',
        'Clark',
        'Rogriguez',
        'Lewis',
        'Lee',
        'Walker',
        'Hall',
        'Allen',
        'Young',
        'Hernandez',
        'King',
        'Wright',
        'Lopez',
        'Hill',
        'Green',
        'Baker',
        'Gonzalez',
        'Nelson',
        'Mitchell',
        'Perez',
        'Roberts',
        'Turner',
        'Philips',
        'Campbell',
        'Parker',
        'Collins',
        'Stewart',
        'Sanchez',
        'Morris',
        'Rogers',
        'Reed',
        'Cook',
        'Bell',
        'Cooper',
        'Richardson',
        'Cox',
        'Ward',
        'Peterson',
        )

    def add_arguments(self, parser):
        parser.add_argument('--database',
            action='store', dest='database', default=None,
            help='use the specified database')
        parser.add_argument('--provider',
            action='store', dest='provider', default=settings.APP_NAME,
            help='create sample subscribers on this provider')

    def handle(self, *args, **options):
        #pylint: disable=too-many-locals,too-many-statements
        from saas.managers.metrics import month_periods # avoid import loop
        from saas.models import (Charge, ChargeItem, Organization, Plan,
            Subscription)

        if 'database' in options:
            db_name = options['database']
            set_current_site(get_site_model().objects.get(
                slug=options['provider'], db_name=db_name), path_prefix='')
        else:
            db_name = 'default'
        now = datetime.datetime.utcnow().replace(tzinfo=utc)
        from_date = now
        from_date = datetime.datetime(
            year=from_date.year, month=from_date.month, day=1)
        if args:
            from_date = datetime.datetime.strptime(
                args[0], '%Y-%m-%d')
        # Create Income transactions that represents a growing bussiness.
        provider = Organization.objects.get(slug=options['provider'])
        processor = Organization.objects.get(pk=PROCESSOR_ID)
        for end_period in month_periods(from_date=from_date):
            nb_new_customers = random.randint(0, 9)
            for _ in range(nb_new_customers):
                queryset = Plan.objects.filter(
                    organization=provider, period_amount__gt=0)
                plan = queryset[random.randint(0, queryset.count() - 1)]
                created = False
                trials = 0
                while not created:
                    try:
                        first_name = self.FIRST_NAMES[random.randint(
                            0, len(self.FIRST_NAMES)-1)]
                        last_name = self.LAST_NAMES[random.randint(
                            0, len(self.LAST_NAMES)-1)]
                        full_name = '%s %s' % (first_name, last_name)
                        slug = slugify('demo%d' % random.randint(1, 1000))
                        customer, created = Organization.objects.get_or_create(
                                slug=slug, full_name=full_name)
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
                    ends_at=now + datetime.timedelta(days=31))
                Subscription.objects.filter(
                    pk=subscription.id).update(created_at=end_period)
            # Insert some churn in %
            churn_rate = 2
            all_subscriptions = Subscription.objects.filter(
                plan__organization=provider)
            nb_churn_customers = (all_subscriptions.count()
                * churn_rate // 100)
            subscriptions = random.sample(list(all_subscriptions),
                all_subscriptions.count() - nb_churn_customers)
            for subscription in subscriptions:
                nb_periods = random.randint(1, 6)
                transaction_item = Transaction.objects.new_subscription_order(
                    subscription, nb_natural_periods=nb_periods,
                    created_at=end_period)
                if transaction_item.dest_amount < 50:
                    continue
                transaction_item.orig_amount = transaction_item.dest_amount
                transaction_item.orig_unit = transaction_item.dest_unit
                transaction_item.save()
                charge = Charge.objects.create(
                    created_at=transaction_item.created_at,
                    amount=transaction_item.dest_amount,
                    customer=subscription.organization,
                    description='Charge for %d periods' % nb_periods,
                    last4=1241,
                    exp_date=datetime_or_now(),
                    processor=processor,
                    processor_key=transaction_item.pk,
# XXX We can't do that yet because of
# ``processor_backend.charge_distribution(self)``
#                    unit=transaction_item.dest_unit,
                    state=Charge.CREATED)
                charge.created_at = transaction_item.created_at
                charge.save()
                ChargeItem.objects.create(
                    invoiced=transaction_item, charge=charge)
                charge.payment_successful()
            churned = all_subscriptions.exclude(
                pk__in=[subscription.pk for subscription in subscriptions])
            for subscription in churned:
                subscription.ends_at = end_period
                subscription.save()
            self.stdout.write("%d new and %d churned customers at %s\n" % (
                nb_new_customers, nb_churn_customers, end_period))
