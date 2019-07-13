import mock

from base.email import send_email


class TestEmail(object):
    @mock.patch("django.core.mail.message.EmailMultiAlternatives.send")
    def test_send_email_successful(self, mock_mail_send):
        send_email(
            subject="Subject",
            text_content="Text Content",
            from_email="noreply@example.com",
            to_email="receiver@example.com"
        )

        mock_mail_send.assert_called_once()

    @mock.patch("logging.Logger.exception")
    @mock.patch("django.core.mail.message.EmailMultiAlternatives.send")
    def test_send_email_returns_exception(self, mock_mail_send, mock_log_exception):
        mock_mail_send.side_effect = Exception

        send_email(
            subject="Subject",
            text_content="Text Content",
            from_email="noreply@example.com",
            to_email="receiver@example.com"
        )

        mock_log_exception.assert_called_once_with("Failed to send email")
