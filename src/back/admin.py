from django.contrib import admin
from django.db.models import Count
from django.urls import reverse
from django.utils.safestring import mark_safe
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

    list_display = ('account', 'person_name', 'organization_name',
                    'address_street', 'address_city', 'address_province', 'address_postal_code', 'address_country',
                    'contact_voice', 'contact_fax', 'contact_email',
                    'email_notifications_enabled', 'automatic_renewal_enabled', )



class DomainAdmin(NestedModelAdmin):

    actions = [
        'domain_synchronize_from_backend',
        'domain_synchronize_from_backend_hard',
        'domain_generate_and_set_new_auth_info_key',
        'domain_renew_on_behalf_of_customer',
        'domain_deduplicate_contacts',
    ]
    list_display = ('name', 'account', 'status', 'create_date', 'expiry_date', 'epp_id', 'epp_statuses',
                    'registrant_contact', 'admin_contact', 'billing_contact', 'tech_contact', )
    list_filter = ('status', )
    search_fields = ('name', )

    def account(self, domain_instance):
        return mark_safe('<a href="{}">{}</a>'.format(
            reverse("admin:accounts_account_change", args=[domain_instance.owner.pk]),
            domain_instance.owner.email))

    def registrant_contact(self, domain_instance):
        return mark_safe('<a href="{}">{}</a>'.format(
            reverse("admin:back_registrant_change", args=[domain_instance.registrant.pk]),
            domain_instance.registrant.epp_id)) if domain_instance.registrant else ''

    def admin_contact(self, domain_instance):
        return mark_safe('<a href="{}">{}</a>'.format(
            reverse("admin:back_contact_change", args=[domain_instance.contact_admin.pk]),
            domain_instance.contact_admin.epp_id)) if domain_instance.contact_admin else ''

    def billing_contact(self, domain_instance):
        return mark_safe('<a href="{}">{}</a>'.format(
            reverse("admin:back_contact_change", args=[domain_instance.contact_billing.pk]),
            domain_instance.contact_billing.epp_id)) if domain_instance.contact_billing else ''

    def tech_contact(self, domain_instance):
        return mark_safe('<a href="{}">{}</a>'.format(
            reverse("admin:back_contact_change", args=[domain_instance.contact_tech.pk]),
            domain_instance.contact_tech.epp_id)) if domain_instance.contact_tech else ''

    def _do_domain_synchronize_from_backend(self, queryset, soft_delete=True):
        report = []
        for domain_object in queryset:
            outputs = zmaster.domain_synchronize_from_backend(
                domain_name=domain_object.name,
                refresh_contacts=True,
                rewrite_contacts=True,
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

    def _do_domain_deduplicate_contacts(self, queryset):
        report = []
        for domain_object in queryset:
            outputs = zmaster.domain_synchronize_contacts(
                domain_object=domain_object,
                skip_contact_details=True,
                merge_duplicated_contacts=True,
                reset_to_oldest_registrant=True,
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

    def domain_deduplicate_contacts(self, request, queryset):
        self.message_user(request, ', '.join(self._do_domain_deduplicate_contacts(queryset)))
    domain_deduplicate_contacts.short_description = "Deduplicate contacts"


class ContactAdmin(NestedModelAdmin):

    list_display = ('epp_id', 'account', 'person_name', 'organization_name',
                    'address_street', 'address_city', 'address_province', 'address_postal_code', 'address_country',
                    'contact_voice', 'contact_fax', 'contact_email', 'domains_count', )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(
            _all_domains_count=Count("admin_domains", distinct=True) + Count("billing_domains", distinct=True) + Count("tech_domains", distinct=True),
        )
        return queryset

    def account(self, contact_instance):
        return mark_safe('<a href="{}">{}</a>'.format(
            reverse("admin:accounts_account_change", args=[contact_instance.owner.pk]),
            contact_instance.owner.email))

    def domains_count(self, obj):
        return obj._all_domains_count
    domains_count.admin_order_field = '_all_domains_count'


class RegistrantAdmin(NestedModelAdmin):

    list_display = ('epp_id', 'account', 'person_name', 'organization_name',
                    'address_street', 'address_city', 'address_province', 'address_postal_code', 'address_country',
                    'contact_voice', 'contact_fax', 'contact_email', 'domains_count', )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(_all_domains_count=Count("registrant_domains", distinct=True))
        return queryset

    def account(self, registrant_instance):
        return mark_safe('<a href="{}">{}</a>'.format(
            reverse("admin:accounts_account_change", args=[registrant_instance.owner.pk]),
            registrant_instance.owner.email))

    def domains_count(self, obj):
        return obj._all_domains_count
    domains_count.admin_order_field = '_all_domains_count'


admin.site.register(Zone, ZoneAdmin)
admin.site.register(Registrar, RegistrarAdmin)
admin.site.register(Profile, ProfileAdmin)
admin.site.register(Domain, DomainAdmin)
admin.site.register(Contact, ContactAdmin)
admin.site.register(Registrant, RegistrantAdmin)
