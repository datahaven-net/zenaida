"""
"""
from __future__ import unicode_literals

import os

import django


def configure_django_settings():
    """Configure Django"""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "main.settings")
    django.setup()


def configure():
    configure_django_settings()
