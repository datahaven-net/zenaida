import time
import logging

from django.core.management.base import BaseCommand

from accounts import tasks as account_tasks
from back import tasks as back_tasks
from zen import zdomains
from billing import tasks as billing_tasks

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = 'Background process to execute regular tasks'

    def add_arguments(self, parser):
        parser.add_argument('--dry_run', action='store_true', dest='dry_run')
        parser.add_argument('--delay', type=int, default=10*60, dest='delay')

    def handle(self, dry_run, delay, *args, **options):
        iteration = 0
        while True:
            iteration += 1
            logger.info('# %d', iteration)

            # billing_tasks.retry_failed_orders()

            back_tasks.sync_expired_domains(dry_run=dry_run)

            account_tasks.check_notify_domain_expiring(
                dry_run=dry_run,
                min_days_before_expire=0,
                max_days_before_expire=2,
                subject='domain_expire_in_1_day',
            )

            account_tasks.check_notify_domain_expiring(
                dry_run=dry_run,
                min_days_before_expire=2,
                max_days_before_expire=5,
                subject='domain_expire_in_3_days',
            )

            account_tasks.check_notify_domain_expiring(
                dry_run=dry_run,
                min_days_before_expire=4,
                max_days_before_expire=7,
                subject='domain_expire_in_5_days',
            )

            account_tasks.check_notify_domain_expiring(
                dry_run=dry_run,
                min_days_before_expire=7,
                max_days_before_expire=30,
                subject='domain_expire_soon',
            )

            account_tasks.check_notify_domain_expiring(
                dry_run=dry_run,
                min_days_before_expire=31,
                max_days_before_expire=60,
                subject='domain_expiring',
            )

            back_tasks.auto_renew_expiring_domains(
                dry_run=dry_run,
                min_days_before_expire=61,
                max_days_before_expire=90,
            )

            # back_tasks.complete_back_end_auto_renewals(
            #     critical_days_before_delete=15,
            # )

            account_tasks.activations_cleanup()

            # Remove all inactive domains.
            zdomains.remove_inactive_domains(days=180)

            # Remove not completed orders.
            billing_tasks.remove_unfinished_orders(status='started', older_than_days=1)
            billing_tasks.remove_unfinished_orders(status='incomplete', older_than_days=2)
            billing_tasks.remove_unfinished_orders(status='cancelled', older_than_days=30)

            # Remove started but not completed payments after 60 days
            billing_tasks.remove_unfinished_payments()

            # TODO: other background periodical jobs to be placed here

            time.sleep(delay)
