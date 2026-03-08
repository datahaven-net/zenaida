from django.db import models

from django.core.serializers.json import DjangoJSONEncoder

from billing.models.order import Order

from zen.zdomains import domain_find, check_renew_duration_increase_possible, validate_domain_name


class OrderItem(models.Model):

    order_items = models.Manager()

    class Meta:
        app_label = 'billing'
        base_manager_name = 'order_items'
        default_manager_name = 'order_items'

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')

    price = models.FloatField(null=False, blank=False, db_index=True)

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
        db_index=True,
    )

    duration = models.IntegerField(null=True, blank=True, default=None, db_index=True)

    name = models.CharField(max_length=255, validators=[validate_domain_name, ], db_index=True)

    details = models.JSONField(null=True, encoder=DjangoJSONEncoder)

    status = models.CharField(
        choices=(
            ('started', 'Started', ),
            ('pending', 'Pending', ),
            ('executing', 'Executing', ),
            ('failed', 'Failed', ),
            ('blocked', 'Blocked', ),
            ('processed', 'Processed', ),
        ),
        default='started',
        max_length=16,
        null=False,
        blank=False,
        db_index=True,
    )

    def __str__(self):
        return 'OrderItem({} {} {})'.format(self.type, self.name, self.status)

    def __repr__(self):
        return 'OrderItem({} {} {})'.format(self.type, self.name, self.status)

    @property
    def maximum_price(self):
        if self.type == 'domain_restore':
            from django.conf import settings
            return self.price + settings.ZENAIDA_DOMAIN_PRICE
        return self.price

    @property
    def duration_formatted(self):
        if self.duration:
            return f'{self.duration} years'
        return ''

    def is_duration_increase_possible(self, duration_increase_value):
        if self.type != 'domain_renew':
            return False
        from django.conf import settings
        domain_object = domain_find(domain_name=self.name)
        current_renew_duration = self.duration or settings.ZENAIDA_DOMAIN_RENEW_YEARS
        return domain_object and check_renew_duration_increase_possible(domain_object, current_renew_duration, duration_increase_value)

    @property
    def is_duration_increase_possible_2(self):
        return self.is_duration_increase_possible(2)

    @property
    def is_duration_increase_possible_4(self):
        return self.is_duration_increase_possible(4)

    @property
    def is_duration_increase_possible_6(self):
        return self.is_duration_increase_possible(6)

    @property
    def is_duration_increase_possible_8(self):
        return self.is_duration_increase_possible(8)
