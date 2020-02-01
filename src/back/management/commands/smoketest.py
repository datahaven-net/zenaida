from django.core.management.base import BaseCommand

from back import smoketest


class Command(BaseCommand):

    help = 'Smoke-test script to be executed every 10 minutes and check important hosts to be accessible'

    def add_arguments(self, parser):
        parser.add_argument('--email_alert', action='store_true', dest='email_alert', default=True)
        parser.add_argument('--push_notification_alert', action='store_true', dest='push_notification_alert', default=False)
        parser.add_argument('--sms_alert', action='store_true', dest='sms_alert', default=False)
        parser.add_argument('--history_filename', dest='history_filename', default='/tmp/smoketests')

    def handle(self, email_alert, push_notification_alert, sms_alert, history_filename, *args, **options):
        smoketest.run(
            history_filename=history_filename,
            email_alert=email_alert,
            push_notification_alert=push_notification_alert,
            sms_alert=sms_alert,
        )
