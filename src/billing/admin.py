from django.contrib import admin
from nested_admin import NestedModelAdmin  # @UnresolvedImport

from billing.models.payment import Payment


class PaymentAdmin(NestedModelAdmin):
    list_display = ('transaction_id', 'amount', 'owner', 'method', 'started_at', 'finished_at', 'status', )


admin.site.register(Payment, PaymentAdmin)
