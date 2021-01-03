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
            ('processing', 'Processing'),
            ('cancelled', 'Cancelled', ),
            ('failed', 'Failed', ),
            ('incomplete', 'Incomplete'),
            ('processed', 'Processed', ),
        ),
        default='started',
        max_length=16,
        null=False,
        blank=False,
    )

    description = models.CharField(max_length=255, blank=True, null=False, default='')

    def __str__(self):
        return 'Order({} #{} : {})'.format(self.description, self.id, self.status)

    def __repr__(self):
        return 'Order({} #{} : {})'.format(self.description, self.id, self.status)

    @property
    def total_price(self):
        return sum([i.price for i in self.items.all()])

    @property
    def items_count(self):
        return len(self.items.all())

    @property
    def is_processable(self):
        return self.status not in ['processed', 'cancelled', ]

    @property
    def is_processed(self):
        return self.status == 'processed'
