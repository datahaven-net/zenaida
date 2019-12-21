import mock

from base.push_notifications import PushNotificationService


class TestPushNotificationService(object):
    @mock.patch("requests.post")
    def test_push(self, mock_post_request):
        mock_post_request.return_value = mock.MagicMock(status_code=200)
        notification = PushNotificationService(notification_message="test notification")
        assert notification.push() is True
