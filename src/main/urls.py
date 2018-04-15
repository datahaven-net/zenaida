from __future__ import unicode_literals

from django.contrib import admin
from django.contrib.auth import views as auth_views

from django.views.generic import TemplateView

from django.urls import path

from signup import views as signup_views

admin_patterns = [
    path(r'^admin/', admin.site.urls),
]

auth_patterns = [

    path(r'^signup/', signup_views.signup, name='auth_signup'),

    path(r'^login/', auth_views.LoginView.as_view(), name='auth_login'),
    path(r'^logout/', auth_views.LogoutView.as_view(), name='auth_logout'),

    path(r'^password_change/', auth_views.PasswordChangeView.as_view(), name='auth_password_change'),
    path(r'^password_change/done/', auth_views.PasswordChangeDoneView.as_view(), name='auth_password_change_done'),

    path(r'^password_reset/', auth_views.PasswordResetView.as_view(), name='auth_password_reset'),
    path(r'^password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='auth_password_reset_done'),

    path(r'^reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='auth_password_reset_confirm'),
    path(r'^reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='auth_password_reset_complete'),

]

patterns = [
    path('', TemplateView.as_view(template_name="index.html"), name='index'),
]

urlpatterns = admin_patterns + auth_patterns + patterns
