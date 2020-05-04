from urllib.parse import parse_qsl, urlparse

from django.test import TestCase

from two_factor.utils import get_otp_auth_url, totp_digits


class TestUtils(TestCase):
    def _assertEqualUrl(self, expected_otp_url, otp_url):
        """
        Asserts whether the URLs are canonically equal.
        """
        expected_otp_url = urlparse(expected_otp_url)
        otp_url = urlparse(otp_url)
        self.assertEqual(expected_otp_url.scheme, otp_url.scheme)
        self.assertEqual(expected_otp_url.netloc, otp_url.netloc)
        self.assertEqual(expected_otp_url.path, otp_url.path)
        self.assertEqual(expected_otp_url.fragment, otp_url.fragment)

        # We used parse_qs before, but as query parameter order became
        # significant with Microsoft Authenticator and possibly other
        # authenticator apps, we've switched to parse_qsl.
        self.assertEqual(parse_qsl(expected_otp_url.query), parse_qsl(otp_url.query))

    def test_get_otp_auth_url(self):
        for num_digits in (6, 8):
            self._assertEqualUrl(
                'otpauth://totp/test%40example.com?secret=abcd1234&digits=' + str(num_digits),
                get_otp_auth_url(account_name='test@example.com', secret='abcd1234', digits=num_digits))

            self._assertEqualUrl(
                'otpauth://totp/test%20user?secret=abcd1234&digits=' + str(num_digits),
                get_otp_auth_url(account_name='test user', secret='abcd1234', digits=num_digits))

            self._assertEqualUrl(
                'otpauth://totp/example.com%3A%20test%40example.com?'
                'secret=abcd1234&digits=' + str(num_digits) + '&issuer=example.com',
                get_otp_auth_url(account_name='test@example.com', issuer='example.com',
                                 secret='abcd1234', digits=num_digits))

            self._assertEqualUrl(
                'otpauth://totp/Zenaida%20Site%3A%20test%40example.com?'
                'secret=abcd1234&digits=' + str(num_digits) + '&issuer=Zenaida+Site',
                get_otp_auth_url(account_name='test@example.com', issuer='Zenaida Site',
                                 secret='abcd1234', digits=num_digits))

    def test_get_totp_digits(self):
        # test that the default is 6 if TWO_FACTOR_TOTP_DIGITS is not set
        self.assertEqual(totp_digits(), 6)

        for no_digits in (6, 8):
            with self.settings(TWO_FACTOR_TOTP_DIGITS=no_digits):
                self.assertEqual(totp_digits(), no_digits)
