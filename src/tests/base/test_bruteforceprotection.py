import mock
import pytest
from django.test import TestCase

from base.exceptions import ExceededMaxAttemptsException
from base.bruteforceprotection import BruteForceProtection


class TestBruteForceProtection(TestCase):
    def setUp(self):

        self.brute_force_protection = BruteForceProtection(
            cache_key_prefix="test_hashkey_prefix",
            key="192.168.1.1",
            max_attempts=1,
            timeout=2
        )

    def test_read_total_attempts(self):
        assert self.brute_force_protection.read_total_attempts() == 0

    @mock.patch('django.core.cache.cache.set')
    def test_increase_total_attempts(self, mock_cache_set):
        assert self.brute_force_protection.increase_total_attempts() == 1
        mock_cache_set.assert_called_once_with('test_hashkey_prefix_192.168.1.1', 1, timeout=2)

    @mock.patch('django.core.cache.cache.get')
    def test_register_attempt_returns_exception(self, mock_cache_get):
        mock_cache_get.return_value = 2
        with pytest.raises(ExceededMaxAttemptsException):
            self.brute_force_protection.register_attempt()
