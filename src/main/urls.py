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

    path('contacts/', front_views.account_contacts, name='account_contacts'),
    path('contacts/create/', front_views.account_contact_create, name='account_contact_create'),
    path('contacts/delete/<int:contact_id>/', front_views.account_contact_delete, name='account_contact_delete'),
    path('contacts/edit/<int:contact_id>/', front_views.account_contact_edit, name='account_contact_edit'),

    path('domains/', front_views.account_domains, name='account_domains'),
    path('domains/create/', front_views.account_domain_create, name='account_domain_create'),
    path('domains/edit/<int:domain_id>/', front_views.account_domain_edit, name='account_domain_edit'),
    path('domains/transfer', front_views.account_domain_transfer, name='account_domain_transfer'),
    # path('domains/history', front_views.account_domain_history, name='account_domain_renew'),

    path('billing/', billing_views.billing_overview, name='billing_overview'),
    path('billing/orders/', billing_views.orders_list, name='billing_orders'),
    path('billing/orders/receipt/', billing_views.order_receipt_download, name='billing_receipt_download'),
    path('billing/orders/receipt/<int:order_id>', billing_views.order_receipt_download, name='billing_receipt_download'),
    path('billing/orders/<int:order_id>/', billing_views.order_details, name='billing_order_details'),
    path('billing/orders/process/<int:order_id>/', billing_views.order_execute, name='billing_order_process'),
    path('billing/orders/cancel/<int:order_id>/', billing_views.order_cancel, name='billing_order_cancel'),
    path('billing/order/create/register/', billing_views.order_domain_register, name='billing_order_register'),
    path('billing/order/create/renew/', billing_views.order_domain_renew, name='billing_order_renew'),
    path('billing/order/create/restore/', billing_views.order_domain_restore, name='billing_order_restore'),
    path('billing/order/create/', billing_views.order_create, name='billing_order_create'),
    path('billing/order/modify/', billing_views.orders_modify, name='billing_orders_modify'),
    path('billing/payments/', billing_views.payments_list, name='billing_payments'),
    path('billing/pay/', billing_views.new_payment, name='billing_new_payment'),
    path('billing/4csonline/pay/', pay_4csonline_views.start_payment, name='billing_4csonline_start_payment'),
    path('billing/4csonline/process/', pay_4csonline_views.process_payment, name='billing_4csonline_process_payment'),
    path('billing/4csonline/verify/', pay_4csonline_views.verify_payment, name='billing_4csonline_verify_payment'),

    path('lookup/', front_views.domain_lookup, name='domain_lookup'),

    path('faq/', front_views.get_faq, name='faq'),
    path('faq_epp/', front_views.get_faq_epp, name='faq_epp'),
    path('faq_auctions/', front_views.get_faq_auctions, name='faq_auctions'),
    path('faq_payments/', front_views.get_faq_payments, name='faq_payments'),
    path('correspondentbank/', front_views.get_correspondentbank, name='correspondentbank'),
    path('registrars/', front_views.get_registrars, name='registrars'),

    path('contact-us/', front_views.contact_us, name='contact_us'),

    path('', front_views.index_page, name='index'),
]

urlpatterns = admin_patterns + auth_patterns + patterns
