from django.db import models

from accounts.models.account import Account


class Payment(models.Model):
    
    payments = models.Manager()

    class Meta:
        app_label = 'billing'
        base_manager_name = 'payments'
        default_manager_name = 'payments'


    owner = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='payments')

    transaction_id = models.CharField(max_length=16, unique=True, null=False, blank=False)

    amount = models.IntegerField(null=False, blank=False, )

    method = models.CharField(
        choices=(
            ('pay_4csonline', 'Credit Card', ),
            ('pay_bank_transfer_anguilla', 'Bank Transfer', ),
        ),
        max_length=32,
        null=False,
        blank=False,
    ) 

    started_at = models.DateTimeField(null=False)

    finished_at = models.DateTimeField(null=True, default=None)

    status = models.CharField(
        choices=(
            ('started', 'Started', ),
            ('failed', 'Failed', ),
            ('paid', 'Paid', ),
            ('processed', 'Processed', ),
        ),
        default='started',
        max_length=16,
        null=False,
        blank=False,
    )
