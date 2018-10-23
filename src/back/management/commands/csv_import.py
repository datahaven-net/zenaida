import os
import time

from django.core.management.base import BaseCommand, CommandError

from zepp.csv_import import load_from_csv


class Command(BaseCommand):

    help = 'Import domains and contacts from .csv file to Zenaida DB'

    def add_arguments(self, parser):
        parser.add_argument('filename', type=str)
        parser.add_argument('--dry_run', action='store_true', dest='dry_run')

    def handle(self, filename, dry_run, *args, **options):
        started = time.time()
        filename = os.path.expanduser(filename)
        if not os.path.isfile(filename):
            raise CommandError('File not found "%s"' % filename)
        import_results = load_from_csv(filename, dry_run=dry_run)
        if import_results < 0:
            self.stdout.write(self.style.ERROR('FAILED'))
            return
        self.stdout.write('import results: {}\n'.format(str(import_results)))
        self.stdout.write(self.style.SUCCESS('Done in %.3f seconds' % (time.time() - started)))
