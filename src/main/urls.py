from __future__ import unicode_literals

from django.contrib import admin
from django.contrib.auth import views as auth_views

from django.views.generic import TemplateView

from django.urls import path

from signup import views as signup_views
from front import views as front_views

admin_patterns = [
    path('admin/', admin.site.urls),
]

auth_patterns = [

    path('signup/', signup_views.signup, name='auth_signup'),

    path('login/', auth_views.LoginView.as_view(), name='auth_login'),
    path('logout/', auth_views.LogoutView.as_view(), name='auth_logout'),

    path('password_change/', auth_views.PasswordChangeView.as_view(), name='auth_password_change'),
    path('password_change/done/', auth_views.PasswordChangeDoneView.as_view(), name='auth_password_change_done'),

    path('password_reset/', auth_views.PasswordResetView.as_view(), name='auth_password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='auth_password_reset_done'),

    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='auth_password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='auth_password_reset_complete'),

]

patterns = [
    path('', TemplateView.as_view(template_name="index.html"), name='index'),
    path('lookup/', front_views.domain_lookup, name='domain_lookup'),
    path('overview/', front_views.account_overview, name='account_overview'),
]

urlpatterns = admin_patterns + auth_patterns + patterns
