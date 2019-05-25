from django.db import models


class BTCPayInvoice(models.Model):

    invoices = models.Manager()

    class Meta:
        app_label = 'billing'
        base_manager_name = 'invoices'
        default_manager_name = 'invoices'

    transaction_id = models.CharField(max_length=16, unique=True, null=False, blank=False)

    invoice_id = models.CharField(max_length=32, unique=True, null=False, blank=False)

    amount = models.FloatField(null=False, blank=False)

    started_at = models.DateTimeField(auto_now_add=True)

    finished_at = models.DateTimeField(null=True, blank=True, default=None)

    status = models.CharField(
        choices=(
            ('new', 'New',),
            ('paid', 'Paid',),
            ('confirmed', 'Confirmed',),
            ('complete', 'Complete',),
            ('expired', 'Expired',),
            ('invalid', 'Invalid',),
        ),
        default='started',
        max_length=16,
        null=False,
        blank=False,
    )

    def __str__(self):
        return 'BTCPayInvoice({} {} {} {})'.format(self.transaction_id, self.invoice_id, self.amount, self.status)
