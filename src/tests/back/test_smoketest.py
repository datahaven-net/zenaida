import os
import mock

from django.test import TestCase, override_settings

from back import smoketest


class TestSmoketest(TestCase):

    @override_settings(SMOKETEST_HOSTS=[])
    def test_run_no_hosts_no_alerts(self):
        assert smoketest.run() == []

    @override_settings(SMOKETEST_HOSTS=['host_not_exist.abcd', ])
    @override_settings(ALERT_EMAIL_RECIPIENTS=['one@email.com', ])
    @mock.patch('back.smoketest.send_email')
    def test_run_one_alert(self, mock_send_email):
        assert smoketest.run(email_alert=True) == [('email', 'one@email.com', '-\n'), ]
        mock_send_email.assert_called_once()

    @override_settings(SMOKETEST_HOSTS=['host_not_exist.abcd', 'another_dead_host.xyz', ])
    @override_settings(ALERT_EMAIL_RECIPIENTS=['one@email.com', ])
    @mock.patch('back.smoketest.send_email')
    def test_run_one_alert_with_history(self, mock_send_email):
        with open('/tmp/testsmoke', 'w') as f:
            f.write('++\n')
        assert smoketest.run(history_filename='/tmp/testsmoke', email_alert=True) == [
            ('email', 'one@email.com', ' host_not_exist.abcd   +-\nanother_dead_host.xyz   +-\n'), ]
        mock_send_email.assert_called_once()
        os.remove('/tmp/testsmoke')
