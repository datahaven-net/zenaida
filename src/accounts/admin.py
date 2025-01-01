from captcha.models import CaptchaStore

from django.contrib import admin, auth, messages
from django.http import HttpResponseRedirect
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.shortcuts import resolve_url

from nested_admin import NestedModelAdmin  # @UnresolvedImport

from accounts.models.account import Account
from accounts.models.activation import Activation
from accounts.models.notification import Notification
from accounts import notifications


class AccountAdmin(NestedModelAdmin):

    list_display = (
        'email', 'profile_link', 'balance', 'is_active', 'is_approved', 'is_staff', 'known_registrants',
        'known_contacts', 'total_domains', 'total_payments', 'total_orders', 'notes',
        'get_admin_login_link', 'get_approve_link',
    )
    search_fields = ('email', )
    readonly_fields = ('email', )

    def get_model_info(self):
        return (self.model._meta.app_label, self.model._meta.model_name)

    def profile_link(self, account_instance):
        return mark_safe('<a href="{}?q={}">{}</a>'.format(
            reverse("admin:back_profile_changelist"), account_instance.email, account_instance.profile))
    profile_link.short_description = 'Profile'

    def known_registrants(self, account_instance):
        return mark_safe('<br>'.join([
            '<a href="{}">{}</a>'.format(
                reverse("admin:back_registrant_change", args=[r.pk]), str(r)) for r in account_instance.registrants.all()]))

    def known_contacts(self, account_instance):
        return mark_safe('<br>'.join([
            '<a href="{}">{}</a>'.format(
                reverse("admin:back_contact_change", args=[c.pk]), str(c)) for c in account_instance.contacts.all()]))

    def total_domains(self, account_instance):
        return mark_safe('<a href="{}?q={}">{} domains</a>'.format(
            reverse("admin:back_domain_changelist"),
            account_instance.email,
            str(account_instance.domains.count() or 'no')))

    def total_payments(self, account_instance):
        return mark_safe('<a href="{}?q={}">{} payments</a>'.format(
            reverse("admin:billing_payment_changelist"),
            account_instance.email,
            str(account_instance.payments.count() or 'no')))

    def total_orders(self, account_instance):
        return mark_safe('<a href="{}?q={}">{} orders</a>'.format(
            reverse("admin:billing_order_changelist"),
            account_instance.email,
            str(account_instance.orders.count() or 'no')))

    def process_account_admin_login(self, request, account_id, *args, **kwargs):
        current_user = request.user
        if not current_user.is_staff:
            messages.add_message(request, messages.ERROR, 'Must have staff permissions to login as another user')
            return HttpResponseRedirect(resolve_url('admin:accounts_account_changelist'))
        if not current_user.is_superuser:
            messages.add_message(request, messages.ERROR, 'Must have superuser permissions to login as another user')
            return HttpResponseRedirect(resolve_url('admin:accounts_account_changelist'))
        another_user = self.get_object(request, account_id)
        if another_user.is_staff:
            messages.add_message(request, messages.ERROR, 'May not login as another staff account')
            return HttpResponseRedirect(resolve_url('admin:accounts_account_changelist'))
        if another_user.is_superuser:
            messages.add_message(request, messages.ERROR, 'May not login as another superuser account')
            return HttpResponseRedirect(resolve_url('admin:accounts_account_changelist'))
        auth.login(request, another_user)
        messages.add_message(request, messages.SUCCESS, 'Superuser %s successfully logged in as %s' % (current_user, another_user, ))
        return HttpResponseRedirect(resolve_url('/'))

    def process_account_approve(self, request, account_id, *args, **kwargs):
        current_user = request.user
        if not current_user.is_staff:
            messages.add_message(request, messages.ERROR, 'Must have staff permissions to login as another user')
            return HttpResponseRedirect(resolve_url('admin:accounts_account_changelist'))
        if not current_user.is_superuser:
            messages.add_message(request, messages.ERROR, 'Must have superuser permissions to login as another user')
            return HttpResponseRedirect(resolve_url('admin:accounts_account_changelist'))
        inst = self.get_object(request, account_id)
        inst.is_approved = True
        inst.save()
        url = reverse("admin:%s_%s_changelist" % self.get_model_info(), current_app=self.admin_site.name)
        notifications.start_email_notification_account_approved(inst)
        return HttpResponseRedirect(url)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:account_id>/admin_login/',
                self.admin_site.admin_view(self.process_account_admin_login),
                name='account-admin-login',
            ),
            path(
                '<int:account_id>/approve/',
                self.admin_site.admin_view(self.process_account_approve),
                name='account-approve',
            ),
        ]
        return custom_urls + urls

    def get_admin_login_link(self, instance):
        if instance.is_staff:
            return format_html('&nbsp;')
        t = '<a href="{}" class="grp-button {}" style="opacity: {};">{}</a>'
        l = reverse('admin:account-admin-login', args=[instance.pk])
        return format_html(t.format(l, 'grp-default', '.6', 'login'))
    get_admin_login_link.short_description = 'superuser'
    get_admin_login_link.allow_tags = True

    def get_approve_link(self, instance):
        if instance.is_approved:
            return format_html('yes')
        t = '<a href="{}" class="grp-button {}" style="opacity: {};">{}</a>'
        l = reverse('admin:account-approve', args=[instance.pk])
        return format_html(t.format(l, 'grp-default', '.6', 'approve'))
    get_approve_link.short_description = 'approved'
    get_approve_link.allow_tags = True


class ActivationAdmin(NestedModelAdmin):
    list_display = ('account', 'code', 'created_at', )
    search_fields = ('account__email', )


class NotificationAdmin(NestedModelAdmin):
    list_display = ('account', 'recipient', 'subject', 'type', 'status', 'created_at',  )
    search_fields = ('account__email', 'recipient', )


class CaptchaStoreAdmin(NestedModelAdmin):
    pass


admin.site.register(Account, AccountAdmin)
admin.site.register(Activation, ActivationAdmin)
admin.site.register(Notification, NotificationAdmin)
admin.site.register(CaptchaStore, CaptchaStoreAdmin)
