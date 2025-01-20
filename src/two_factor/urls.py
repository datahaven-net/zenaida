from django.urls import re_path

from two_factor.views import (
    BackupTokensView, DisableView, LoginView,
    TwoFactorProfileView, QRGeneratorView, SetupCompleteView, SetupView,
)

core = [
    re_path(
        r'^accounts/login/$',
        view=LoginView.as_view(),
        name='login',
    ),
    re_path(
        r'^account/two_factor/setup/$',
        view=SetupView.as_view(),
        name='setup',
    ),
    re_path(
        r'^account/two_factor/qrcode/$',
        view=QRGeneratorView.as_view(),
        name='qr',
    ),
    re_path(
        r'^account/two_factor/setup/complete/$',
        view=SetupCompleteView.as_view(),
        name='setup_complete',
    ),
    re_path(
        r'^account/two_factor/backup/tokens/$',
        view=BackupTokensView.as_view(),
        name='backup_tokens',
    ),
]

two_factor_profile = [
    re_path(
        r'^account/two_factor/$',
        view=TwoFactorProfileView.as_view(),
        name='profile',
    ),
    re_path(
        r'^account/two_factor/disable/$',
        view=DisableView.as_view(),
        name='disable',
    ),
]

urlpatterns = (core + two_factor_profile, 'two_factor')
