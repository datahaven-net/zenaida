import time
import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts import tasks as account_tasks
from back import tasks as back_tasks

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = 'Background process to execute regular tasks'

    def add_arguments(self, parser):
        parser.add_argument('--dry_run', action='store_true', dest='dry_run')
        parser.add_argument('--delay', type=int, default=5*60, dest='delay')

    def handle(self, dry_run, delay, *args, **options):
        iteration = 0
        while True:
            iteration += 1

            account_tasks.check_notify_domain_expiring(dry_run=dry_run)

            back_tasks.sync_expired_domains(dry_run=dry_run)

            account_tasks.activations_cleanup()

            # TODO: other background periodical jobs to be placed here

            logger.info('finished iteration %d at %r', iteration, timezone.now().isoformat())
            time.sleep(delay)
