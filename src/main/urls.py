from __future__ import unicode_literals

from django.contrib import admin
from django.contrib.auth import views as auth_views

from django.urls import path
from django.conf.urls import include, url
from django.views.generic import TemplateView

from front import views as front_views
from billing import views as billing_views
from billing.pay_4csonline import views as pay_4csonline_views
from billing.pay_btcpay import views as pay_btcpay_views
from board import views as board_views
from accounts import views as accounts_views
from two_factor.urls import urlpatterns as two_factor_urls


handler404 = 'front.views.handler404'
handler500 = 'front.views.handler500'

admin_patterns = [
    path('grappelli/', include('grappelli.urls')),
    path('_nested_admin/', include('nested_admin.urls')),
    path('admin/', admin.site.urls),

]

auth_patterns = [
    # All login related stuff goes through the "two_factor" module.
    url(r'', include(two_factor_urls)),

    # Register, logout, password change/reset/forgotten flows go through "accounts" module.
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
    path('profile/', front_views.AccountProfileView.as_view(), name='account_profile'),

    path('contacts/', front_views.AccountContactsListView.as_view(), name='account_contacts'),
    path('contacts/create/', front_views.AccountContactCreateView.as_view(), name='account_contact_create'),
    path('contacts/edit/<int:contact_id>/', front_views.AccountContactUpdateView.as_view(), name='account_contact_edit'),
    path('contacts/delete/<int:contact_id>/', front_views.AccountContactDeleteView.as_view(), name='account_contact_delete'),

    path('domains/', front_views.AccountDomainsListView.as_view(), name='account_domains'),
    path('domains/create/<str:domain_name>/', front_views.AccountDomainCreateView.as_view(), name='account_domain_create'),
    path('domains/transfer/', front_views.AccountDomainTransferTakeoverView.as_view(), name='account_domain_transfer_takeover'),
    path('domains/edit/<int:domain_id>/', front_views.AccountDomainUpdateView.as_view(), name='account_domain_edit'),
    path('domains/<str:domain_id>/transfer-code/', front_views.AccountDomainTransferCodeView.as_view(), name='account_domain_transfer_code'),

    path('billing/', billing_views.billing_overview, name='billing_overview'),
    path('billing/orders/', billing_views.OrdersListView.as_view(), name='billing_orders'),
    path('billing/orders/receipts/download/', billing_views.OrderReceiptsDownloadView.as_view(), name='billing_receipts_download'),
    path('billing/orders/receipts/download/<int:order_id>/', billing_views.OrderSingleReceiptDownloadView.as_view(), name='billing_receipt_download'),
    path('billing/order/<int:order_id>/', billing_views.OrderDetailsView.as_view(), name='billing_order_details'),
    path('billing/order/process/<int:order_id>/', billing_views.OrderExecuteView.as_view(), name='billing_order_process'),
    path('billing/order/cancel/<int:order_id>/', billing_views.OrderCancelView.as_view(), name='billing_order_cancel'),
    path('billing/order/create/register/<str:domain_name>/', billing_views.OrderDomainRegisterView.as_view(), name='billing_order_register'),
    path('billing/order/create/renew/<str:domain_name>/', billing_views.OrderDomainRenewView.as_view(), name='billing_order_renew'),
    path('billing/order/create/restore/<str:domain_name>/', billing_views.OrderDomainRestoreView.as_view(), name='billing_order_restore'),
    path('billing/order/create/', billing_views.OrderCreateView.as_view(), name='billing_order_create'),
    path('billing/payments/', billing_views.PaymentsListView.as_view(), name='billing_payments'),
    path('billing/payment/invoice/download/<str:transaction_id>/', billing_views.PaymentInvoiceDownloadView.as_view(), name='billing_invoice_download'),
    path('billing/pay/', billing_views.NewPaymentView.as_view(), name='billing_new_payment'),

    path('billing/4csonline/process/<str:transaction_id>/', pay_4csonline_views.ProcessPaymentView.as_view(), name='billing_4csonline_process_payment'),
    path('billing/4csonline/verify/', pay_4csonline_views.VerifyPaymentView.as_view(), name='billing_4csonline_verify_payment'),

    path('billing/btcpay/process/<str:transaction_id>/', pay_btcpay_views.ProcessPaymentView.as_view(), name='billing_btcpay_process_payment'),
    path('billing/btcpay/redirect/', pay_btcpay_views.RedirectPaymentView.as_view(), name='billing_btcpay_redirect_payment'),

    path('board/balance-adjustment/', board_views.BalanceAdjustmentView.as_view(), name='balance_adjustment'),
    path('board/financial-report/', board_views.FinancialReportView.as_view(), name='financial_report'),
    path('board/domain-sync/', board_views.NotExistingDomainSyncView.as_view(), name='not_existing_domain_sync'),
    path('board/csv-file-sync/<str:record_id>/', board_views.CSVFileSyncRecordView.as_view(), name='csv_file_sync_record'),
    path('board/csv-file-sync/', board_views.CSVFileSyncView.as_view(), name='csv_file_sync'),

    path('lookup/', front_views.DomainLookupView.as_view(), name='domain_lookup'),

    path('faq/', TemplateView.as_view(template_name='front/faq.html'), name='faq'),

    path('contact-us/', TemplateView.as_view(template_name='front/contact_us.html'), name='contact_us'),

    path('', front_views.IndexPageView.as_view(), name='index'),
]

urlpatterns = admin_patterns + auth_patterns + patterns
