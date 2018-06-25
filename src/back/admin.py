from django.contrib import admin

from back.models.profile import Profile
from back.models.domain import Domain


class ProfileAdmin(admin.ModelAdmin):
    pass


class DomainAdmin(admin.ModelAdmin):
    pass


admin.site.register(Profile, ProfileAdmin)
admin.site.register(Domain, DomainAdmin)
