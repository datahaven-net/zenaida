from django.core.management.base import BaseCommand

from zepp import epp_poll


class Command(BaseCommand):

    help = 'Starts background process to poll/listen EPP notifications from the back-end'

#     def add_arguments(self, parser):
#         parser.add_argument('filename', type=str)
#         parser.add_argument('--dry_run', action='store_true', dest='dry_run')

    def handle(self, *args, **options):
        epp_poll.main()
