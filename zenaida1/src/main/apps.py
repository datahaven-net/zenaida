from __future__ import unicode_literals

from django.apps import AppConfig

# The time_execution package can be used for storing metrics.
# See: http://py-timeexecution.readthedocs.io/en/latest/
# import time_execution
# from time_execution.backends.elasticsearch import ElasticsearchBackend
# from time_execution.backends.threaded import ThreadedBackend


class MainConfig(AppConfig):
    name = 'main'

    def ready(self):
        """Location for package configurations"""
