"""
This file contains configuration and hooks needed to generate documentation
using the de-partition-docs package.
"""
from __future__ import unicode_literals

import os

import django

from de_partition_docs import conf


def configure_django_settings():
    """Configure Django"""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "main.settings")
    django.setup()


def configure():
    """Configure the de-partition-docs package similar to py.tests' configure"""
    configure_django_settings()
    conf.settings.configure(
        DOCS_PATH=os.path.abspath(
            os.path.join(
                os.path.dirname(os.path.dirname(__file__)), '..',
                'docs', 'api'
            )
        )
    )
