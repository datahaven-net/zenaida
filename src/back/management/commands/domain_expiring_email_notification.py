import time

from django.core.management.base import BaseCommand

from accounts import notifications


class Command(BaseCommand):

    help = 'Prepare Email notifications to customers about any expiring domains'

    def add_arguments(self, parser):
        parser.add_argument('--dry_run', action='store_true', dest='dry_run')

    def handle(self, dry_run, *args, **options):
        started = time.time()
        notifications.check_notify_domain_expiring(dry_run=dry_run)
        self.stdout.write(self.style.SUCCESS('Done in %.3f seconds' % (time.time() - started)))
