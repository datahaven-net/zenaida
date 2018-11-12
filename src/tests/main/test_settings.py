from django.conf import settings as django_settings

from main import settings as main_settings


def test_settings():
    assert main_settings.LOADED_OK == 'OK'
    assert django_settings.LOADED_OK == 'OK'
