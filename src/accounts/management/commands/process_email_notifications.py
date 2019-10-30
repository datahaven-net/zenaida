import time
import logging

from django.core.management.base import BaseCommand

from accounts.models.notification import Notification
from accounts import notifications

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = 'Sending Email notifications from the queue'

    def handle(self, *args, **options):
        notifications.process_notifications_queue()
