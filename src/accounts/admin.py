from django.contrib import admin
from django.urls import reverse
from django.utils.safestring import mark_safe
from nested_admin import NestedModelAdmin  # @UnresolvedImport

from accounts.models.account import Account
from accounts.models.activation import Activation
from accounts.models.notification import Notification


class AccountAdmin(NestedModelAdmin):

    list_display = (
        'email', 'balance', 'is_active', 'is_staff', 'known_registrants',
        'known_contacts', 'total_domains', 'total_payments', 'total_orders', 'notes'
    )
    search_fields = ('email', )
    readonly_fields = ('email', )

    def known_registrants(self, account_instance):
        return mark_safe('<br>'.join([
            '<a href="{}">{}</a>'.format(
                reverse("admin:back_registrant_change", args=[r.pk]), str(r)) for r in account_instance.registrants.all()]))

    def known_contacts(self, account_instance):
        return mark_safe('<br>'.join([
            '<a href="{}">{}</a>'.format(
                reverse("admin:back_contact_change", args=[c.pk]), str(c)) for c in account_instance.contacts.all()]))

    def total_domains(self, account_instance):
        return mark_safe('<a href="{}?q={}">{} domains</a>'.format(
            reverse("admin:back_domain_changelist"),
            account_instance.email,
            str(account_instance.domains.count() or 'no')))

    def total_payments(self, account_instance):
        return mark_safe('<a href="{}?q={}">{} payments</a>'.format(
            reverse("admin:billing_payment_changelist"),
            account_instance.email,
            str(account_instance.payments.count() or 'no')))

    def total_orders(self, account_instance):
        return mark_safe('<a href="{}?q={}">{} orders</a>'.format(
            reverse("admin:billing_order_changelist"),
            account_instance.email,
            str(account_instance.orders.count() or 'no')))


class ActivationAdmin(NestedModelAdmin):
    list_display = ('account', 'code', 'created_at', )


class NotificationAdmin(NestedModelAdmin):
    list_display = ('account', 'recipient', 'subject', 'type', 'status', 'created_at',  )


admin.site.register(Account, AccountAdmin)
admin.site.register(Activation, ActivationAdmin)
admin.site.register(Notification, NotificationAdmin)
