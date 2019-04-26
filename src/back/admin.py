from django.contrib import admin
from nested_admin import NestedModelAdmin  # @UnresolvedImport

from back.models.zone import Zone
from back.models.registrar import Registrar
from back.models.profile import Profile
from back.models.domain import Domain
from back.models.contact import Contact, Registrant


class ZoneAdmin(NestedModelAdmin):
    pass


class RegistrarAdmin(NestedModelAdmin):
    pass


class ProfileAdmin(NestedModelAdmin):
    pass


class DomainAdmin(NestedModelAdmin):

    actions = ['domain_synchronize_from_backend', ]
    list_display = ('name', 'owner_email', 'status', 'create_date', 'expiry_date', 'epp_id', 'epp_statuses', )

    def owner_email(self, domain_instance):
        return domain_instance.owner.email

    def domain_synchronize_from_backend(self, request, queryset):
        from zen import zmaster
        report = []
        for domain_object in queryset:
            outputs = zmaster.domain_synchronize_from_backend(
                domain_name=domain_object.name,
                refresh_contacts=True,
                change_owner_allowed=True,
                raise_errors=True,
                log_events=True,
                log_transitions=True,
            )
            ok = True
            for output in outputs:
                if isinstance(output, Exception):
                    report.append('"%s": %r' % (domain_object.name, output, ))
                    ok = False
            if ok:
                report.append('"%s": %d calls OK' % (domain_object.name, len(outputs), ))
        self.message_user(request, ', '.join(report))
    domain_synchronize_from_backend.short_description = "Synchronize from back-end"


class ContactAdmin(NestedModelAdmin):
    pass


class RegistrantAdmin(NestedModelAdmin):
    pass


admin.site.register(Zone, ZoneAdmin)
admin.site.register(Registrar, RegistrarAdmin)
admin.site.register(Profile, ProfileAdmin)
admin.site.register(Domain, DomainAdmin)
admin.site.register(Contact, ContactAdmin)
admin.site.register(Registrant, RegistrantAdmin)
