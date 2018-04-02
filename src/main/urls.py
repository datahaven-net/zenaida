from __future__ import unicode_literals

from django.conf.urls import include, url

from django.contrib import admin
from django.urls import path

patterns = [
    # url(r'v1/', include('api.v1.urls', namespace='api')),
    # url(r'system/', include(system_patterns, namespace='system'))
]

urlpatterns = [
    url(r'^test/', include(patterns)),
    path('admin/', admin.site.urls),
]
