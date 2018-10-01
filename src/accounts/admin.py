from django.contrib import admin
from nested_admin import NestedModelAdmin


from accounts.models import Activation, Account


class ActivationAdmin(NestedModelAdmin):
    pass


class AccountAdmin(NestedModelAdmin):
    list_display = ('email', 'is_active', 'is_staff', )


admin.site.register(Activation, ActivationAdmin)
admin.site.register(Account, AccountAdmin)
