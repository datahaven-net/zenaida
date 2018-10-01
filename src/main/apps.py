from __future__ import unicode_literals

from django.apps import AppConfig


class MainConfig(AppConfig):
    name = 'main'

    def ready(self):
        """Location for package configurations"""
        return True
