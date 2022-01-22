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

            account_tasks.activations_cleanup()

            # Remove all inactive domains.
            zdomains.remove_inactive_domains(days=1)

            # Remove started but not completed orders after a day.
            billing_tasks.remove_started_orders(older_than_days=1)

            # TODO: other background periodical jobs to be placed here

            time.sleep(delay)
