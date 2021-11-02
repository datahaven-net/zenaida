import requests
from django.conf import settings


class PushNotificationService(object):
    def __init__(self, notification_message):
        self.notification_message = notification_message

    def push(self):
        for token_info in settings.PUSH_NOTIFICATION_SERVICE_SUBSCRIBERS_TOKENS:
            requests.post(
                url=settings.PUSH_NOTIFICATION_SERVICE_POST_URL,
                json=dict(
                    token=token_info[0],
                    user=token_info[1],
                    message=self.notification_message
                )
            )
        return True
