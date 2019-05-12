from django.contrib import admin
from nested_admin import NestedModelAdmin  # @UnresolvedImport

from billing.models.payment import Payment
from billing.models.order import Order
from billing.models.order_item import OrderItem
from billing.pay_btcpay.models import BTCPayInvoice


class PaymentAdmin(NestedModelAdmin):
    list_display = ('transaction_id', 'amount', 'owner', 'method', 'started_at', 'finished_at', 'status', )


class BTCPayInvoiceAdmin(NestedModelAdmin):
    list_display = ('invoice_id', 'transaction_id', 'amount', 'started_at', 'finished_at', 'status', )


class OrderAdmin(NestedModelAdmin):
    list_display = ('description', 'total_price', 'owner', 'started_at', 'finished_at', 'status', )


class OrderItemAdmin(NestedModelAdmin):
    list_display = ('name', 'type', 'price', 'status', 'order', )


admin.site.register(Payment, PaymentAdmin)
admin.site.register(BTCPayInvoice, BTCPayInvoiceAdmin)
admin.site.register(Order, OrderAdmin)
admin.site.register(OrderItem, OrderItemAdmin)
