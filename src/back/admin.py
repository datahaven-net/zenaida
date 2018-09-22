from django.contrib import admin

from back.models.zone import Zone
from back.models.registrar import Registrar
from back.models.account import Account
from back.models.profile import Profile
from back.models.domain import Domain
from back.models.contact import Contact


class ZoneAdmin(admin.ModelAdmin):
    pass


class RegistrarAdmin(admin.ModelAdmin):
    pass


class AccountAdmin(admin.ModelAdmin):
    pass


class ProfileAdmin(admin.ModelAdmin):
    pass


class DomainAdmin(admin.ModelAdmin):
    pass


class ContactAdmin(admin.ModelAdmin):
    pass


admin.site.register(Zone, ZoneAdmin)
admin.site.register(Registrar, RegistrarAdmin)
admin.site.register(Account, AccountAdmin)
admin.site.register(Profile, ProfileAdmin)
admin.site.register(Domain, DomainAdmin)
admin.site.register(Contact, ContactAdmin)
