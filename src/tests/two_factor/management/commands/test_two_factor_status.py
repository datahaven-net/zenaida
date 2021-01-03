from io import StringIO

from django.core.management import CommandError, call_command
from django.test import TestCase

from tests.two_factor.mixins import UserMixin


class TestStatusCommand(UserMixin, TestCase):
    def _assert_raises(self, err_type, err_message):
        return self.assertRaisesMessage(err_type, err_message)

    def test_raises(self):
        stdout = StringIO()
        stderr = StringIO()
        with self._assert_raises(CommandError, 'User "some_username" does not exist'):
            call_command(
                'two_factor_status', 'some_username',
                no_color=True,
                stdout=stdout, stderr=stderr)

        with self._assert_raises(CommandError, 'User "other_username" does not exist'):
            call_command(
                'two_factor_status', 'other_username', 'some_username',
                no_color=True,
                stdout=stdout, stderr=stderr)

    def test_status_single(self):
        user = self.create_user()
        stdout = StringIO()
        call_command('two_factor_status', 'test@example.com', no_color=True, stdout=stdout)
        self.assertEqual(stdout.getvalue(), 'test@example.com: disabled\n')

        stdout = StringIO()
        self.enable_otp(user)
        call_command('two_factor_status', 'test@example.com', no_color=True, stdout=stdout)
        self.assertEqual(stdout.getvalue(), 'test@example.com: enabled\n')

    def test_status_multiple(self):
        users = [self.create_user(n) for n in ['test@example.com', 'test1@example.com']]
        self.enable_otp(users[0])
        stdout = StringIO()
        call_command('two_factor_status', 'test@example.com', 'test1@example.com', no_color=True, stdout=stdout)
        self.assertEqual(stdout.getvalue(), 'test@example.com: enabled\n'
                                            'test1@example.com: disabled\n')
