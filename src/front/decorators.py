from django import shortcuts
from django.conf import settings
from django.contrib import messages

from base import utils as base_utils
from base.bruteforceprotection import BruteForceProtection
from base.exceptions import ExceededMaxAttemptsException

from zen import zusers


def validate_profile_exists(dispatch_func):
    def dispatch_wrapper(self, request, *args, **kwargs):
        if self.request.user.is_authenticated:
            if not hasattr(request.user, 'profile'):
                zusers.create_profile(request.user, contact_email=request.user.email)
            if not request.user.profile.is_complete() or not request.user.registrants.count():
                messages.info(request, 'Please provide your contact information to be able to register new domains')
                return shortcuts.redirect('account_profile')
        return dispatch_func(self, request, *args, **kwargs)
    return dispatch_wrapper


def brute_force_protection(cache_key_prefix, max_attempts, timeout):
    def decorator(func):
        def wrapper(request, *args, **kwargs):
            if settings.BRUTE_FORCE_PROTECTION_ENABLED:
                client_ip = base_utils.get_client_ip(request_meta=request.request.META)
                brute_force = BruteForceProtection(
                    cache_key_prefix=cache_key_prefix,
                    key=client_ip,
                    max_attempts=max_attempts,
                    timeout=timeout
                )
                try:
                    request.request.temporarily_blocked = False
                    brute_force.register_attempt()
                except ExceededMaxAttemptsException:
                    request.request.temporarily_blocked = True
            else:
                request.request.temporarily_blocked = False
            return func(request, *args, **kwargs)
        return wrapper
    return decorator
