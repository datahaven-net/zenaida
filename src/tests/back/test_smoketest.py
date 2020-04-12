import os
import mock

from django.test import TestCase, override_settings

from back import smoketest


class TestSmoketest(TestCase):

    @override_settings(SMOKETEST_HOSTS=[])
    @mock.patch('back.smoketest.send_email')
    def test_run_no_hosts_no_alerts(self, mock_send_email):
        with open('/tmp/testsmoke', 'w') as f:
            f.write('')
        assert smoketest.run(history_filename='/tmp/testsmoke') is None
        os.remove('/tmp/testsmoke')
        mock_send_email.assert_not_called()

    @override_settings(SMOKETEST_HOSTS=['host_not_exist.abcd', ], ALERT_EMAIL_RECIPIENTS=['one@email.com', ])
    @mock.patch('back.smoketest.send_email')
    def test_run_smoketest_for_the_first_time(self, mock_send_email):
        with open('/tmp/testsmoke', 'w') as f:
            f.write('')

        assert smoketest.run(history_filename='/tmp/testsmoke', email_alert=True) is None

        # Check if file is updated with the negative health check for the host.
        with open('/tmp/testsmoke', 'r') as f:
            for line in f:
                assert line == "-"

        os.remove('/tmp/testsmoke')
        mock_send_email.assert_not_called()

    @override_settings(SMOKETEST_HOSTS=['host_not_exist.abcd', ], ALERT_EMAIL_RECIPIENTS=['one@email.com', ])
    def test_run_smoketest_for_the_file_does_not_exist(self):
        assert smoketest.run(history_filename='/tmp/testsmoke', email_alert=True) is None
        assert os.path.isfile('/tmp/testsmoke') is True
        os.remove('/tmp/testsmoke')

    @override_settings(
        SMOKETEST_HOSTS=['host_not_exist.abcd', 'another_dead_host.xyz', ],
        SMOKETEST_MAXIMUM_UNAVAILABLE_AMOUNT=3,
        ALERT_EMAIL_RECIPIENTS=['one@email.com', ]
    )
    @mock.patch('back.smoketest.PushNotificationService.push')
    @mock.patch('back.smoketest.SMSSender.send_sms')
    @mock.patch('back.smoketest.send_email')
    def test_run_one_alert_with_history(self, mock_send_email, mock_send_sms, mock_push_notification_alert):
        with open('/tmp/testsmoke', 'w') as f:
            f.write('++-+--\n--')

        assert smoketest.run(
            history_filename='/tmp/testsmoke', email_alert=True, sms_alert=True, push_notification_alert=True
        ) == [
            ('email', 'one@email.com', 'host_not_exist.abcd   ++-+---\nanother_dead_host.xyz   ---\n'),
            ('sms', '', 'host_not_exist.abcd   ++-+---\nanother_dead_host.xyz   ---\n'),
            ('push', '', 'host_not_exist.abcd   ++-+---\nanother_dead_host.xyz   ---\n')
        ]

        os.remove('/tmp/testsmoke')
        mock_send_email.assert_called_once()
        mock_send_sms.assert_called_once()
        mock_push_notification_alert.assert_called_once()

    @override_settings(SMOKETEST_HOSTS=['ping://localhost', ], ALERT_EMAIL_RECIPIENTS=['one@email.com', ])
    @mock.patch('back.smoketest.send_email')
    def test_ping_ok(self, mock_send_email):
        assert smoketest.run(history_filename='/tmp/testsmoke', email_alert=True) is None
        with open('/tmp/testsmoke', 'r') as f:
            for line in f:
                assert line == "+"
        os.remove('/tmp/testsmoke')
        mock_send_email.assert_not_called()

    @override_settings(SMOKETEST_HOSTS=['http://zenaida.cate.ai', ], ALERT_EMAIL_RECIPIENTS=['one@email.com', ])
    @mock.patch('back.smoketest.send_email')
    def test_http_ok(self, mock_send_email):
        assert smoketest.run(history_filename='/tmp/testsmoke', email_alert=True) is None
        with open('/tmp/testsmoke', 'r') as f:
            for line in f:
                assert line == "+"
        os.remove('/tmp/testsmoke')
        mock_send_email.assert_not_called()

    @override_settings(SMOKETEST_HOSTS=['https://zenaida.cate.ai', ], ALERT_EMAIL_RECIPIENTS=['one@email.com', ])
    @mock.patch('back.smoketest.send_email')
    def test_https_ok(self, mock_send_email):
        assert smoketest.run(history_filename='/tmp/testsmoke', email_alert=True) is None
        with open('/tmp/testsmoke', 'r') as f:
            for line in f:
                assert line == "+"
        os.remove('/tmp/testsmoke')
        mock_send_email.assert_not_called()

    @override_settings(SMOKETEST_HOSTS=['ping://localhost-not-exist', ], ALERT_EMAIL_RECIPIENTS=['one@email.com', ])
    @mock.patch('back.smoketest.send_email')
    def test_ping_not_ok(self, mock_send_email):
        assert smoketest.run(history_filename='/tmp/testsmoke', email_alert=True) is None
        with open('/tmp/testsmoke', 'r') as f:
            for line in f:
                assert line == "-"
        os.remove('/tmp/testsmoke')
        mock_send_email.assert_not_called()

    @override_settings(SMOKETEST_HOSTS=['http://zenaida-fake.cate.ai', ], ALERT_EMAIL_RECIPIENTS=['one@email.com', ])
    @mock.patch('back.smoketest.send_email')
    def test_http_not_ok(self, mock_send_email):
        assert smoketest.run(history_filename='/tmp/testsmoke', email_alert=True) is None
        with open('/tmp/testsmoke', 'r') as f:
            for line in f:
                assert line == "-"
        os.remove('/tmp/testsmoke')
        mock_send_email.assert_not_called()

    @override_settings(SMOKETEST_HOSTS=['https://zenaida-fake.cate.ai', ], ALERT_EMAIL_RECIPIENTS=['one@email.com', ])
    @mock.patch('back.smoketest.send_email')
    def test_https_not_ok(self, mock_send_email):
        assert smoketest.run(history_filename='/tmp/testsmoke', email_alert=True) is None
        with open('/tmp/testsmoke', 'r') as f:
            for line in f:
                assert line == "-"
        os.remove('/tmp/testsmoke')
        mock_send_email.assert_not_called()
