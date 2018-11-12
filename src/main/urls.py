from __future__ import unicode_literals

from django.contrib import admin
from django.contrib.auth import views as auth_views

from django.urls import path
from django.conf.urls import include

from front import views as front_views
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

    path('domains/', front_views.account_domains, name='account_domains'),

    path('lookup/', front_views.domain_lookup, name='domain_lookup'),

    path('', front_views.account_overview, name='index'),

]

urlpatterns = admin_patterns + auth_patterns + patterns
