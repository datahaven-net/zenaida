from django.contrib import admin
from django.urls import reverse
from django.utils.safestring import mark_safe
from nested_admin import NestedModelAdmin  # @UnresolvedImport

from accounts.models.account import Account
from accounts.models.activation import Activation
from accounts.models.notification import Notification


class AccountAdmin(NestedModelAdmin):

    list_display = ('email', 'is_active', 'is_staff', 'known_registrants', 'known_contacts', 'total_domains', 'total_payments', 'total_orders', )
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
        return account_instance.domains.count()

    def total_payments(self, account_instance):
        return account_instance.payments.count()

    def total_orders(self, account_instance):
        return account_instance.orders.count()


class ActivationAdmin(NestedModelAdmin):
    list_display = ('account', 'code', 'created_at', )


class NotificationAdmin(NestedModelAdmin):
    list_display = ('account', 'recipient', 'subject', 'type', 'status', 'created_at',  )


admin.site.register(Account, AccountAdmin)
admin.site.register(Activation, ActivationAdmin)
admin.site.register(Notification, NotificationAdmin)
