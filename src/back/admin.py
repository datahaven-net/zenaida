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

    fields = (
        ('get_owner_link', ),
        ('person_name', ),
        ('organization_name', ),
        ('address_street', ),
        ('address_city', ),
        ('address_province', ),
        ('address_postal_code', ),
        ('address_country', ),
        ('contact_voice', ),
        ('contact_fax', ),
        ('contact_email', ),
        ('email_notifications_enabled', ),
        ('automatic_renewal_enabled', ),
    )
    list_display = ('account', 'person_name', 'organization_name',
                    'address_street', 'address_city', 'address_province', 'address_postal_code', 'address_country',
                    'contact_voice', 'contact_fax', 'contact_email',
                    'email_notifications_enabled', 'automatic_renewal_enabled', )
    readonly_fields = ('get_owner_link', 'contact_email', )

    def get_owner_link(self, profile_instance):
        link = reverse("admin:accounts_account_change", args=[profile_instance.account.pk])
        return mark_safe(f'<a href="{link}">{profile_instance.account}</a>')
    get_owner_link.short_description = 'Account'


class DomainAdmin(NestedModelAdmin):
    fields = (
        ('name', ),
        ('get_owner_link', ),
        ('status', ),
        ('epp_id', ),
        ('create_date', ),
        ('expiry_date', ),
        ('epp_statuses', ),
        ('auth_key', ),
        ('zone', ),
        ('registrar', ),
        ('auto_renew_enabled', ),
        ('get_registrant_link', ),
        ('get_contact_admin_link', ),
        ('get_contact_billing_link', ),
        ('get_contact_tech_link', ),
        ('nameserver1', ),
        ('nameserver2', ),
        ('nameserver3', ),
        ('nameserver4', ),
    )
    actions = (
        'domain_synchronize_from_backend',
        'domain_synchronize_from_backend_hard',
        'domain_synchronize_from_backend_transfer',
        'domain_generate_and_set_new_auth_info_key',
        'domain_renew_on_behalf_of_customer',
        'domain_deduplicate_contacts',
    )
    list_display = ('name', 'account', 'status', 'create_date', 'expiry_date', 'epp_id', 'epp_statuses',
                    'registrant_contact', 'admin_contact', 'billing_contact', 'tech_contact', )
    list_filter = ('status', )
    search_fields = ('name', 'owner__email', )
    readonly_fields = ('name', 'owner', 'registrar', 'zone',
                       'get_owner_link', 'get_registrant_link',
                       'get_contact_admin_link', 'get_contact_billing_link', 'get_contact_tech_link', )

    def account(self, domain_instance):
        return mark_safe('<a href="{}?q={}">{}</a>'.format(
            reverse("admin:accounts_account_changelist"), domain_instance.owner.email, domain_instance.owner.email))

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

    def get_owner_link(self, domain_instance):
        link = '{}?q={}'.format(reverse("admin:accounts_account_changelist"), domain_instance.owner.email)
        return mark_safe(f'<a href="{link}">{domain_instance.owner}</a>')
    get_owner_link.short_description = 'Account'

    def get_registrant_link(self, domain_instance):
        link = reverse("admin:back_registrant_change", args=[domain_instance.registrant.pk])
        return mark_safe(f'<a href="{link}">{domain_instance.registrant}</a>')
    get_registrant_link.short_description = 'Registrant'

    def get_contact_admin_link(self, domain_instance):
        link = reverse("admin:back_contact_change", args=[domain_instance.contact_admin.pk])
        return mark_safe(f'<a href="{link}">{domain_instance.contact_admin}</a>')
    get_contact_admin_link.short_description = 'Admin contact'

    def get_contact_billing_link(self, domain_instance):
        link = reverse("admin:back_contact_change", args=[domain_instance.contact_billing.pk])
        return mark_safe(f'<a href="{link}">{domain_instance.contact_billing}</a>')
    get_contact_billing_link.short_description = 'Billing contact'

    def get_contact_tech_link(self, domain_instance):
        link = reverse("admin:back_contact_change", args=[domain_instance.contact_tech.pk])
        return mark_safe(f'<a href="{link}">{domain_instance.contact_tech}</a>')
    get_contact_tech_link.short_description = 'Tech contact'

    def _do_domain_synchronize_from_backend(self, queryset, soft_delete=True, change_owner_allowed=False):
        report = []
        for domain_object in queryset:
            outputs = []
            outputs.extend(zmaster.domain_synchronize_from_backend(
                domain_name=domain_object.name,
                refresh_contacts=True,
                rewrite_contacts=False,
                change_owner_allowed=change_owner_allowed,
                create_new_owner_allowed=change_owner_allowed,
                soft_delete=soft_delete,
                raise_errors=True,
                log_events=True,
                log_transitions=True,
            ))
            if soft_delete is True:
                domain_object.refresh_from_db()
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
                rewrite_registrant=True,
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

    def domain_synchronize_from_backend_transfer(self, request, queryset):
        self.message_user(request, ', '.join(self._do_domain_synchronize_from_backend(queryset, change_owner_allowed=True)))
    domain_synchronize_from_backend_transfer.short_description = "Synchronize and change owner"

    def domain_synchronize_from_backend_hard(self, request, queryset):
        self.message_user(request, ', '.join(self._do_domain_synchronize_from_backend(queryset, soft_delete=False)))
    domain_synchronize_from_backend_hard.short_description = "Synchronize and delete"

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

    fields = (
        ('get_owner_link', ),
        ('epp_id', ),
        ('person_name', ),
        ('organization_name', ),
        ('address_street', ),
        ('address_city', ),
        ('address_province', ),
        ('address_postal_code', ),
        ('address_country', ),
        ('contact_voice', ),
        ('contact_fax', ),
        ('contact_email', ),
    )
    list_display = ('epp_id', 'account', 'person_name', 'organization_name',
                    'address_street', 'address_city', 'address_province', 'address_postal_code', 'address_country',
                    'contact_voice', 'contact_fax', 'contact_email', 'domains_count', )
    search_fields = ('owner__email', )
    readonly_fields = ('owner', 'get_owner_link', )

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

    def get_owner_link(self, contact_instance):
        link = reverse("admin:accounts_account_change", args=[contact_instance.owner.pk])
        return mark_safe(f'<a href="{link}">{contact_instance.owner}</a>')
    get_owner_link.short_description = 'Account'


class RegistrantAdmin(NestedModelAdmin):

    fields = (
        ('get_owner_link', ),
        ('epp_id', ),
        ('person_name', ),
        ('organization_name', ),
        ('address_street', ),
        ('address_city', ),
        ('address_province', ),
        ('address_postal_code', ),
        ('address_country', ),
        ('contact_voice', ),
        ('contact_fax', ),
        ('contact_email', ),
    )
    list_display = ('epp_id', 'account', 'person_name', 'organization_name',
                    'address_street', 'address_city', 'address_province', 'address_postal_code', 'address_country',
                    'contact_voice', 'contact_fax', 'contact_email', 'domains_count', )
    search_fields = ('owner__email', )
    readonly_fields = ('owner', 'get_owner_link', )

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

    def get_owner_link(self, registrant_instance):
        link = reverse("admin:accounts_account_change", args=[registrant_instance.owner.pk])
        return mark_safe(f'<a href="{link}">{registrant_instance.owner}</a>')
    get_owner_link.short_description = 'Account'


admin.site.register(Zone, ZoneAdmin)
admin.site.register(Registrar, RegistrarAdmin)
admin.site.register(Profile, ProfileAdmin)
admin.site.register(Domain, DomainAdmin)
admin.site.register(Contact, ContactAdmin)
admin.site.register(Registrant, RegistrantAdmin)
