from django.db import models

from accounts.models.account import Account


class Order(models.Model):
    
    orders = models.Manager()

    class Meta:
        app_label = 'billing'
        base_manager_name = 'orders'
        default_manager_name = 'orders'


    # related fields:
    # items -> billing.models.order_item.OrderItem


    owner = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='orders')

    started_at = models.DateTimeField(null=False)

    finished_at = models.DateTimeField(null=True, blank=True, default=None)

    status = models.CharField(
        choices=(
            ('started', 'Started', ),
            ('cancelled', 'Cancelled', ),
            ('failed', 'Failed', ),
            ('processed', 'Processed', ),
        ),
        default='started',
        max_length=16,
        null=False,
        blank=False,
    )

    @property
    def total_price(self):
        return sum([i.price for i in self.items.all()])

    @property
    def items_count(self):
        return len(self.items.all())
