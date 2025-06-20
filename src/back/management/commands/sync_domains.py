import time
import logging

from django.core.management.base import BaseCommand

from zen import zdomains
from zen import zmaster

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = 'Synchronize from back-end given list of domains provided via text file'

    def add_arguments(self, parser):
        parser.add_argument('--filepath', dest='filepath', default='./domains-list.txt')
        parser.add_argument('--delay', type=int, default=10, dest='delay')

    def handle(self, filepath, delay, *args, **options):
        while True:
            fin = open(filepath, 'rt')
            all_lines = fin.read().strip().split('\n')
            fin.close()
            if not all_lines:
                logger.info('DONE')
                break
            one_domain = all_lines[0].strip()
            if not one_domain:
                logger.info('DONE')
                break
            fout = open(filepath, 'wt')
            fout.write('\n'.join(all_lines[1:]))
            fout.close()
            domain_obj = zdomains.domain_find(domain_name=one_domain)
            if not domain_obj:
                logger.warn('domain %r was not found in the DB' % one_domain)
                continue
            zmaster.domains_quick_sync(
                domain_objects_list=[domain_obj, ],
                hours_passed=12,
                request_time_limit=5,
            )
            time.sleep(delay)
