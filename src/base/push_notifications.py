import requests
from django.conf import settings


class PushNotificationService(object):
    def __init__(self, notification_message):
        self.notification_message = notification_message

    def push(self):
        requests.post(
            url=settings.PUSH_NOTIFICATION_SERVICE_POST_URL,
            json=dict(
                token=settings.PUSH_NOTIFICATION_SERVICE_API_TOKEN,
                user=settings.PUSH_NOTIFICATION_SERVICE_USER_TOKEN,
                message=self.notification_message
            )
        )
        return True
