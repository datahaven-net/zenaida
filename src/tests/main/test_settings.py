from django.test import override_settings

from main import settings


def test_settings():
    assert settings.ENV in ['prod', 'development', ]
