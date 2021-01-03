from django.db import models

from django.core.serializers.json import DjangoJSONEncoder

from billing.models.order import Order

from zen.zdomains import validate_domain_name


class OrderItem(models.Model):
    
    order_items = models.Manager()

    class Meta:
        app_label = 'billing'
        base_manager_name = 'order_items'
        default_manager_name = 'order_items'

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')

    price = models.FloatField(null=False, blank=False)

    type = models.CharField(
        choices=(
            ('domain_register', 'Domain Register', ),
            ('domain_renew', 'Domain Renew', ),
            ('domain_restore', 'Domain Restore', ),
            ('domain_transfer', 'Domain Transfer', ),
        ),
        max_length=32,
        null=False,
        blank=False,
    )

    name = models.CharField(max_length=255, validators=[validate_domain_name, ])

    details = models.JSONField(null=True, encoder=DjangoJSONEncoder)

    status = models.CharField(
        choices=(
            ('started', 'Started', ),
            ('pending', 'Pending', ),
            ('failed', 'Failed', ),
            ('processed', 'Processed', ),
        ),
        default='started',
        max_length=16,
        null=False,
        blank=False,
    )

    def __str__(self):
        return 'OrderItem({} {} {})'.format(self.type, self.name, self.status)

    def __repr__(self):
        return 'OrderItem({} {} {})'.format(self.type, self.name, self.status)
