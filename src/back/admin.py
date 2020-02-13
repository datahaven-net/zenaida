from django.contrib import admin
from django.conf import settings
from nested_admin import NestedModelAdmin  # @UnresolvedImport

from back.models.zone import Zone
from back.models.registrar import Registrar
from back.models.profile import Profile
from back.models.domain import Domain
from back.models.contact import Contact, Registrant

from billing import orders as billing_orders

from zen import zmaster


class ZoneAdmin(NestedModelAdmin):
    pass


class RegistrarAdmin(NestedModelAdmin):
    pass


class ProfileAdmin(NestedModelAdmin):
    pass


class DomainAdmin(NestedModelAdmin):

    actions = [
        'domain_synchronize_from_backend',
        'domain_synchronize_from_backend_hard',
        'domain_generate_and_set_new_auth_info_key',
        'domain_renew_on_behalf_of_customer',
    ]
    list_display = ('name', 'owner_email', 'status', 'create_date', 'expiry_date', 'epp_id', 'epp_statuses', )

    def owner_email(self, domain_instance):
        return domain_instance.owner.email

    def _do_domain_synchronize_from_backend(self, queryset, soft_delete=True):
        report = []
        for domain_object in queryset:
            outputs = zmaster.domain_synchronize_from_backend(
                domain_name=domain_object.name,
                refresh_contacts=True,
                change_owner_allowed=True,
                soft_delete=soft_delete,
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
        return report

    def _do_generate_and_set_new_auth_info_key(self, queryset):
        report = []
        for domain_object in queryset:
            result = zmaster.domain_set_auth_info(domain_object)
            report.append('"%s": %s' % (domain_object.name, 'OK' if result else 'ERROR', ))
        return report

    def _do_renew_on_behalf_of_customer(self, queryset):
        report = []
        for domain_object in queryset:
            renewal_order = billing_orders.order_single_item(
                owner=domain_object.owner,
                item_type='domain_renew',
                item_price=settings.ZENAIDA_DOMAIN_PRICE,
                item_name=domain_object.name,
            )
            if renewal_order.total_price > renewal_order.owner.balance:
                report.append('"%s": %s' % (domain_object.name, 'not enough funds'))
                continue
            new_status = billing_orders.execute_order(renewal_order)
            report.append('"%s": %s' % (domain_object.name, new_status))
        return report

    def domain_synchronize_from_backend(self, request, queryset):
        self.message_user(request, ', '.join(self._do_domain_synchronize_from_backend(queryset, soft_delete=True)))
    domain_synchronize_from_backend.short_description = "Synchronize from back-end"

    def domain_synchronize_from_backend_hard(self, request, queryset):
        self.message_user(request, ', '.join(self._do_domain_synchronize_from_backend(queryset, soft_delete=False)))
    domain_synchronize_from_backend_hard.short_description = "Synchronize from back-end (hard delete)"

    def domain_generate_and_set_new_auth_info_key(self, request, queryset):
        self.message_user(request, ', '.join(self._do_generate_and_set_new_auth_info_key(queryset)))
    domain_generate_and_set_new_auth_info_key.short_description = "Generate new auth info"

    def domain_renew_on_behalf_of_customer(self, request, queryset):
        self.message_user(request, ', '.join(self._do_renew_on_behalf_of_customer(queryset)))
    domain_renew_on_behalf_of_customer.short_description = "Renew on behalf of customer"


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
