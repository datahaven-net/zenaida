import logging

from django.core.cache import cache

from base.exceptions import ExceededMaxAttemptsException


logger = logging.getLogger(__name__)


class BruteForceProtection(object):

    def __init__(self, cache_key_prefix, key, max_attempts, timeout):
        self.cache_key = f"{cache_key_prefix}_{key}"
        self.max_attempts = max_attempts
        self.timeout = timeout
        self._local_value = None

    def read_total_attempts(self):
        self._local_value = cache.get(self.cache_key)
        logger.debug('bruteforceprotection.read_total_attempts key=%r %r', self.cache_key, self._local_value)
        return self._local_value if self._local_value else 0

    def increase_total_attempts(self):
        self.read_total_attempts()
        if not self._local_value:
            self._local_value = 0
        self._local_value += 1
        cache.set(self.cache_key, self._local_value, timeout=self.timeout)
        logger.debug('bruteforceprotection.increase_total_attempts key=%r %r', self.cache_key, self._local_value)
        return self._local_value

    def register_attempt(self):
        total_attempts = self.read_total_attempts()
        if total_attempts >= self.max_attempts:
            raise ExceededMaxAttemptsException
        self.increase_total_attempts()
