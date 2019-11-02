from django.core.management.base import BaseCommand

from accounts import notifications


class Command(BaseCommand):

    help = 'Sending Email/SMS notifications from the queue'

    def handle(self, *args, **options):
        notifications.process_notifications_queue()
