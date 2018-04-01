from __future__ import unicode_literals

from django.conf.urls import include, url

patterns = [
    # url(r'v1/', include('api.v1.urls', namespace='api')),
    # url(r'system/', include(system_patterns, namespace='system'))
]

urlpatterns = [
    url(r'^test/', include(patterns)),
]
