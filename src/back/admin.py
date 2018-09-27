from django.contrib import admin
from nested_admin import NestedModelAdmin, NestedStackedInline

from back.models.zone import Zone
from back.models.registrar import Registrar
from back.models.account import Account
from back.models.profile import Profile
from back.models.domain import Domain
from back.models.contact import Contact


class ZoneAdmin(NestedModelAdmin):
    pass


class RegistrarAdmin(NestedModelAdmin):
    pass


class AccountAdmin(NestedModelAdmin):
    list_display = ('email', 'is_active', 'is_staff', )


class ProfileAdmin(NestedModelAdmin):
    pass


class DomainAdmin(NestedModelAdmin):
    pass


class ContactAdmin(NestedModelAdmin):
    pass


admin.site.register(Zone, ZoneAdmin)
admin.site.register(Registrar, RegistrarAdmin)
admin.site.register(Account, AccountAdmin)
admin.site.register(Profile, ProfileAdmin)
admin.site.register(Domain, DomainAdmin)
admin.site.register(Contact, ContactAdmin)
