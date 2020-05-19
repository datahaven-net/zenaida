import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class BaseSMSGateway(object):
    def __init__(self):
        self.auth_token = settings.SMS_GATEWAY_AUTHORIZATION_BEARER_TOKEN
        self.request_headers = {
            "Content-Type": "application/json",
            "Authorization": self.auth_token,
            "X-Version": "1"
        }


class SMSSender(BaseSMSGateway):
    def __init__(self, text_message, phone_numbers=None):
        super().__init__()
        self.phone_numbers = phone_numbers
        if not self.phone_numbers:
            self.phone_numbers = settings.ALERT_SMS_PHONE_NUMBERS
        self.text_message = text_message

    def send_sms(self):
        try:
            resp = requests.post(
                url=settings.SMS_GATEWAY_SEND_URL,
                json=dict(text=self.text_message, to=self.phone_numbers),
                headers=self.request_headers
            )
        except:
            logger.critical(f"sending a SMS is failed to {self.phone_numbers} with this message: {self.text_message}")
            return False

        if resp.status_code != 202:
            error_code = resp.json().get("error", {}).get("code")
            error_description = resp.json().get("error", {}).get("description")
            logger.critical(f"sending a SMS to {self.phone_numbers} with this message: '{self.text_message}' "
                            f"returned an error. Error code: {error_code}, Error description: {error_description}")

        return True


class SMSStatus(BaseSMSGateway):
    def __init__(self, sms_id):
        super().__init__()
        self.sms_id = sms_id

    def get_status(self):
        try:
            resp = requests.get(url=f"{settings.SMS_GATEWAY_SEND_URL}/{self.sms_id}", headers=self.request_headers)
        except:
            logger.critical(f"getting status of SMS call was not successful. SMS ID: {self.sms_id}")
            return False

        if (resp.status_code == 200 and not resp.json().get("data", {}).get("messageStatus") == "004") or not resp.status_code == 200:
            error_description = resp.json().get("data", {}).get("description")
            if not error_description:
                error_description = resp.json().get("error", {}).get("description")
            logger.critical(f"sending a SMS with this {self.sms_id} ID was not successfully done. "
                            f"Error description: {error_description}")
            return False
        return True
