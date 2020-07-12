from functools import wraps

from django.conf import settings
from django.contrib import messages

import requests


def check_recaptcha(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        request.request.recaptcha_is_valid = None
        if request.request.method == 'POST':
            recaptcha_response = request.request.POST.get('g-recaptcha-response')
            data = {
                'secret': settings.GOOGLE_RECAPTCHA_SECRET_KEY,
                'response': recaptcha_response
            }
            r = requests.post('https://www.recaptcha.net/recaptcha/api/siteverify', data=data)
            result = r.json()
            # If recaptcha is active, then check if user correctly filled the captcha.
            # When recaptcha is not active, application will behave as captcha was filled correctly.
            if result.get('success') or not settings.GOOGLE_RECAPTCHA_SITE_KEY:
                request.request.recaptcha_is_valid = True
            else:
                request.request.recaptcha_is_valid = False
                messages.error(request.request, 'You filled the captcha wrong, please try again')
        return view_func(request, *args, **kwargs)
    return _wrapped_view
