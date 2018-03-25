import os

import django
from django import http
from django.core.handlers.wsgi import WSGIHandler, WSGIRequest, get_str_from_wsgi
from django.utils.functional import cached_property

# Directly assign to os.environ instead of using os.environ.setdefault as the former plays nice
# with having multiple django sites run from one WSGIProcessGroup, as done on test server.
# There seems to be no use case where the DJANGO_SETTINGS_MODULE needs to be defined elsewhere.
# See comment in default Django project wsgi
os.environ["DJANGO_SETTINGS_MODULE"] = "main.settings"


# Bug in python not reading cookies that are not properly escaped or have colons in the name.
# http://bugs.python.org/issue22931
# https://code.djangoproject.com/ticket/24492


class MyWSGIRequest(WSGIRequest):

    @cached_property
    def COOKIES(self):
        cookies = dict()
        raw_cookie = get_str_from_wsgi(self.environ, 'HTTP_COOKIE', '')
        for cookie in [cookie for cookie in raw_cookie.split(';')]:
            cookies.update(http.parse_cookie(cookie))
        return cookies


class MyWSGIHandler(WSGIHandler):
    request_class = MyWSGIRequest


def get_wsgi_application():
    django.setup()
    return MyWSGIHandler()


application = get_wsgi_application()
