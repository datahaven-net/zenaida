from __future__ import unicode_literals

from django.contrib import admin
from django.contrib.auth import views as auth_views

from django.urls import path
from django.conf.urls import include

from front import views as front_views
from billing import views as billing_views
from billing.pay_4csonline import views as pay_4csonline_views
from accounts import views as accounts_views


admin_patterns = [
    path('grappelli/', include('grappelli.urls')),
    path('_nested_admin/', include('nested_admin.urls')),
    path('admin/', admin.site.urls),

]

auth_patterns = [
    path('accounts/login/', accounts_views.SignInView.as_view(), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(
        template_name='accounts/logout.html'), name='logout'),
    path('accounts/register/', accounts_views.SignUpView.as_view(), name='register'),
    path('accounts/activate/<code>/', accounts_views.ActivateView.as_view(), name='activate'),
    path('accounts/password/change/', auth_views.PasswordChangeView.as_view(
        template_name='accounts/password_change_form.html'), name='password_change'),
    path('accounts/password/change/done/', auth_views.PasswordChangeDoneView.as_view(
        template_name='accounts/password_change_done.html'), name='password_change_done'),
    path('accounts/password/reset/', auth_views.PasswordResetView.as_view(
        template_name='accounts/password_reset.html'), name='password_reset'),
    path('accounts/password/reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='accounts/password_reset_done.html'), name='password_reset_done'),
    path('accounts/password/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='accounts/password_reset_confirm.html'), name='password_reset_confirm'),
    path('accounts/password/reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='accounts/password_reset_complete.html'), name='password_reset_complete'),
]

patterns = [
    path('profile/', front_views.account_profile, name='account_profile'),

    path('contacts/', front_views.ContactsView.as_view(), name='account_contacts'),
    path('contacts/new/', front_views.create_new_contact, name='account_contacts_new'),
    path('contacts/edit/<int:contact_id>/', front_views.edit_contact, name='account_contacts_edit'),

    path('domains/', front_views.account_domains, name='account_domains'),
    path('domains/add', front_views.account_domain_add, name='account_domain_add'),
    # path('domains/edit', front_views.account_domain_edit, name='account_domain_edit'),
    # path('domains/register', front_views.account_domain_register, name='account_domain_register'),
    # path('domains/renew', front_views.account_domain_renew, name='account_domain_renew'),
    # path('domains/transfer', front_views.account_domain_transfer, name='account_domain_transfer'),
    # path('domains/history', front_views.account_domain_history, name='account_domain_renew'),

    # path('billing/', front_views.billing_overview, name='billing_overview'),
    # path('billing/invoice', front_views.billing_invoice, name='billing_invoice'),
    path('billing/pay/', billing_views.new_payment, name='billing_new_payment'),
    path('billing/4csonline/pay/', pay_4csonline_views.start_payment, name='billing_4csonline_start_payment'),
    path('billing/4csonline/process/', pay_4csonline_views.process_payment, name='billing_4csonline_process_payment'),
    path('billing/4csonline/verify/', pay_4csonline_views.verify_payment, name='billing_4csonline_verify_payment'),

    path('lookup/', front_views.domain_lookup, name='domain_lookup'),

    # FAQ URLs
    path('faq/', front_views.get_faq, name='faq'),
    path('faq_epp/', front_views.get_faq_epp, name='faq_epp'),
    path('faq_auctions/', front_views.get_faq_auctions, name='faq_auctions'),
    path('faq_payments/', front_views.get_faq_payments, name='faq_payments'),
    path('correspondentbank/', front_views.get_correspondentbank, name='correspondentbank'),
    path('registrars/', front_views.get_registrars, name='registrars'),
    # Index
    path('', front_views.account_overview, name='index'),
]

urlpatterns = admin_patterns + auth_patterns + patterns
