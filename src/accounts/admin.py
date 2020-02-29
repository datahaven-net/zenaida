from django.contrib import admin
from nested_admin import NestedModelAdmin  # @UnresolvedImport

from accounts.models.account import Account
from accounts.models.activation import Activation
from accounts.models.notification import Notification


class AccountAdmin(NestedModelAdmin):
    list_display = ('email', 'is_active', 'is_staff', )


class ActivationAdmin(NestedModelAdmin):
    list_display = ('account', 'code', 'created_at', )


class NotificationAdmin(NestedModelAdmin):
    list_display = ('account', 'recipient', 'subject', 'type', 'status', 'created_at',  )


admin.site.register(Account, AccountAdmin)
admin.site.register(Activation, ActivationAdmin)
admin.site.register(Notification, NotificationAdmin)
