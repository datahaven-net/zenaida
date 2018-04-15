from __future__ import unicode_literals

from django.conf.urls import include, url

from django.contrib import admin
from django.views.generic import TemplateView

from signup import views as signup_views

admin_patterns = [
    url(r'^admin/', admin.site.urls),
]

auth_patterns = [
    url('^', include('django.contrib.auth.urls')),
]

patterns = [
    url(r'^signup/$', signup_views.signup, name='signup'),
    url('', TemplateView.as_view(template_name="index.html"), name='index'),
]

urlpatterns = admin_patterns + auth_patterns + patterns
