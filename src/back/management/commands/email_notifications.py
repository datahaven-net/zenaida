import os
import time

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):

    help = 'Sending Email notifications to customers'

    def add_arguments(self, parser):
        parser.add_argument('--dry_run', action='store_true', dest='dry_run')

    def handle(self, dry_run, *args, **options):
        started = time.time()

        # TODO: to be implemented


        self.stdout.write(self.style.SUCCESS('Done in %.3f seconds' % (time.time() - started)))
