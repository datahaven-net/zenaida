from django.contrib import admin
from nested_admin import NestedModelAdmin  # @UnresolvedImport

from accounts.models.account import Account
from accounts.models.activation import Activation


class ActivationAdmin(NestedModelAdmin):
    list_display = ('account', 'code', 'created_at', )


class AccountAdmin(NestedModelAdmin):
    list_display = ('email', 'is_active', 'is_staff', )


admin.site.register(Activation, ActivationAdmin)
admin.site.register(Account, AccountAdmin)
