from django.core.management.base import BaseCommand

from zen import zpoll


class Command(BaseCommand):

    help = 'Starts background process to "listen" EPP notifications from the back-end'

    def handle(self, *args, **options):
        zpoll.main()
