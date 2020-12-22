import os
import time
import logging

from io import StringIO

from django.core.management.base import BaseCommand, CommandError

from back.csv_import import load_from_csv
from board.models.csv_file_sync import CSVFileSync


class Command(BaseCommand):

    help = 'Import domains and contacts from .csv file to Zenaida DB'

    def add_arguments(self, parser):
        parser.add_argument('--record_id', type=int, default=-1)
        parser.add_argument('--filename', type=str, default='')
        parser.add_argument('--dry_run', action='store_true', dest='dry_run')

    def handle(self, record_id, filename, dry_run, *args, **options):
        started = time.time()
        log_stream = None
        if record_id >= 0:
            csv_sync_record = CSVFileSync.executions.filter(id=record_id).first()
            if not csv_sync_record:
                raise CommandError('Record not found "%s"' % record_id)

            filename = csv_sync_record.input_filename

            log_stream = StringIO()
            string_handler = logging.StreamHandler(log_stream)
            root_logger = logging.getLogger()

            loggers = [root_logger, ] + [logging.getLogger(name) for name in logging.root.manager.loggerDict]  # @UndefinedVariable
            for one_logger in loggers:
                one_logger.addHandler(string_handler)

        filename = os.path.expanduser(filename)
        if not os.path.isfile(filename):
            if record_id >= 0:
                csv_sync_record = CSVFileSync.executions.get(id=record_id)
                csv_sync_record.status = 'failed'
                csv_sync_record.output_log = 'File not found "%s"' % filename
                csv_sync_record.save()
            raise CommandError('File not found "%s"' % filename)

        import_results = load_from_csv(filename, dry_run=dry_run)

        if record_id >= 0:
            csv_sync_record = CSVFileSync.executions.get(id=record_id)
            if import_results >= 0:
                csv_sync_record.status = 'finished'
                csv_sync_record.output_log = log_stream.getvalue()
                csv_sync_record.processed_count = import_results
            else:
                csv_sync_record.status = 'failed'
                csv_sync_record.output_log = log_stream.getvalue()
            csv_sync_record.save()

        if import_results < 0:
            self.stdout.write(self.style.ERROR('FAILED'))
            return

        self.stdout.write('import results: {}\n'.format(str(import_results)))
        self.stdout.write(self.style.SUCCESS('Done in %.3f seconds' % (time.time() - started)))
