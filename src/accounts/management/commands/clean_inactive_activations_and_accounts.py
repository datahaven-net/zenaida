import datetime
import logging
import time

from django.conf import settings
from django.core.management.base import BaseCommand

from accounts.models.activation import Activation

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    def handle(self, *args, **options):
        while True:
            cleanup()
            time.sleep(60*5)


def cleanup():
    '''
    If the activation_code is older than a certain time of period and the account is still inactive (no domain,
    balance or payment belongs to the account as well), removes the inactive account and the expired activation code.

    If the activation_code is older than a certain time of period but the account is still active, then removes
    only the activation code.
    '''

    activation_code_expiry_time = datetime.datetime.now() - datetime.timedelta(
        minutes=settings.ACTIVATION_CODE_EXPIRING_MINUTE
    )
    expired_activation_code_objects = Activation.objects.filter(created_at__lte=activation_code_expiry_time)

    for activation_code in expired_activation_code_objects:
        account = activation_code.account
        if not account.is_active:
            if account.balance == 0 and len(account.domains.all()) == 0 and len(account.payments.all()) == 0:
                activation_code.account.delete()  # This will remove activation code as well.
                logger.warning(f"Inactive account for this email address is removed: '{account.email}'")
                continue
        activation_code.delete()
