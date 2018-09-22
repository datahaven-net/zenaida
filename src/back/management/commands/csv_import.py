import os

from django.core.management.base import BaseCommand, CommandError

from zepp.csv_import import load_from_csv


class Command(BaseCommand):

    help = 'Import domains and contacts from .csv file to Zenaida DB'

    def add_arguments(self, parser):
        parser.add_argument('filename', type=str)
        parser.add_argument('--dry_run', action='store_true', dest='dry_run')

    def handle(self, filename, dry_run, *args, **options):
        filename = os.path.expanduser(filename)
        if not os.path.isfile(filename):
            raise CommandError('File not found "%s"' % filename)
        import_results = load_from_csv(filename, dry_run=dry_run)
        self.stdout.write('import results: {}\n'.format(str(import_results)))
        self.stdout.write(self.style.SUCCESS('Done'))
