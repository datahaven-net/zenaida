from io import StringIO

from django.core.management import CommandError, call_command
from django.test import TestCase
from django_otp import devices_for_user

from tests.two_factor.mixins import UserMixin


class TestDisableCommand(UserMixin, TestCase):
    def _assert_raises(self, err_type, err_message):
        return self.assertRaisesMessage(err_type, err_message)

    def test_raises(self):
        stdout = StringIO()
        stderr = StringIO()
        with self._assert_raises(CommandError, 'User "some_username" does not exist'):
            call_command(
                'two_factor_disable', 'some_username',
                no_color=True,
                stdout=stdout, stderr=stderr)

        with self._assert_raises(CommandError, 'User "other_username" does not exist'):
            call_command(
                'two_factor_disable', 'other_username', 'some_username',
                no_color=True,
                stdout=stdout, stderr=stderr)

    def test_disable_single(self):
        user = self.create_user()
        self.enable_otp(user)
        call_command('two_factor_disable', 'test@example.com', no_color=True)
        self.assertEqual(list(devices_for_user(user)), [])

    def test_happy_flow_multiple(self):
        usernames = ['user%d@example.com' % i for i in range(0, 3)]
        users = [self.create_user(username) for username in usernames]
        [self.enable_otp(user) for user in users]
        call_command('two_factor_disable', *usernames[:2], no_color=True)
        self.assertEqual(list(devices_for_user(users[0])), [])
        self.assertEqual(list(devices_for_user(users[1])), [])
        self.assertNotEqual(list(devices_for_user(users[2])), [])
