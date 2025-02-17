from django.db import models

from accounts.models.account import Account

from back.models.domain import Domain

from billing.models.order import Order


class BackEndRenew(models.Model):

    renewals = models.Manager()

    class Meta:
        app_label = 'back'
        base_manager_name = 'renewals'
        default_manager_name = 'renewals'

    created = models.DateTimeField(auto_now_add=True)

    domain_name = models.CharField(max_length=255, unique=False)

    domain = models.ForeignKey(
        Domain, on_delete=models.CASCADE, related_name='renewals', null=True, blank=True, verbose_name='Back-End Renewals')

    owner = models.ForeignKey(
        Account, on_delete=models.CASCADE, related_name='renewals', null=True, blank=True)

    renew_order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name='renewals', null=True, blank=True)

    status = models.CharField(
        choices=(
            ('started', 'Started', ),
            ('processed', 'Processed', ),
        ),
        default='started',
        max_length=16,
        null=False,
        blank=False,
    )

    previous_expiry_date = models.DateTimeField(null=True, blank=True, default=None)

    next_expiry_date = models.DateTimeField(null=True, blank=True, default=None)

    def __str__(self):
        return 'BackEndRenew({} {} {})'.format(self.domain_name, self.created, self.status)

    def __repr__(self):
        return 'BackEndRenew({} {} {})'.format(self.domain_name, self.created, self.status)
