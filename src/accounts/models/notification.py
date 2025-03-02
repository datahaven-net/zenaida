from django.core.serializers.json import DjangoJSONEncoder
from django.db import models

from accounts.models.account import Account


class Notification(models.Model):

    notifications = models.Manager()

    class Meta:
        app_label = 'accounts'
        base_manager_name = 'notifications'
        default_manager_name = 'notifications'

    created_at = models.DateTimeField(auto_now_add=True)

    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='notifications')

    recipient = models.CharField(max_length=255)

    status = models.CharField(
        max_length=10,
        choices=(
            ('started', 'STARTED', ),
            ('sent', 'SENT', ),
            ('failed', 'FAILED', ),
            ('skipped', 'SKIPPED', ),
        ),
        default='started',
    )

    type = models.CharField(
        max_length=10,
        choices=(
            ('email', 'EMAIL', ),
            ('sms', 'SMS', ),
        ),
        default='email',
    )

    subject = models.CharField(
        max_length=32,
        choices=(
            ('domain_expiring', 'DOMAIN EXPIRING', ),
            ('domain_expire_soon', 'DOMAIN EXPIRE SOON', ),
            ('domain_restored', 'DOMAIN RESTORED', ),
            ('domain_transferred', 'DOMAIN TRANSFERRED', ),
            ('domain_activated', 'DOMAIN ACTIVATED', ),
            ('domain_deactivated', 'DOMAIN DEACTIVATED', ),
            ('domain_renewed', 'DOMAIN RENEWED', ),
            ('domain_deleted', 'DOMAIN DELETED', ),
            ('low_balance', 'LOW BALANCE', ),
            ('low_balance_back_end_renew', 'LOW BALANCE BACK END RENEW', ),
            ('account_approved', 'ACCOUNT_APPROVED', ),
        ),
    )

    domain_name = models.CharField(max_length=255)

    details = models.JSONField(null=True, encoder=DjangoJSONEncoder)

    def __str__(self):
        return 'Notification({}->{}:{}:{}:{})'.format(self.account.email, self.recipient, self.subject, self.type, self.status)
