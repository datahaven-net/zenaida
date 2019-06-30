import mock

from base.sms import SMSSender, SMSStatus


class TestSMSSender(object):
    @mock.patch("requests.post")
    def test_successful_send_sms(self, mock_post_request):
        mock_post_request.return_value = mock.MagicMock(status_code=202)
        sms_sender = SMSSender(text_message="test sms", phone_numbers=[31612345678])
        assert sms_sender.send_sms() is True

    @mock.patch("logging.Logger.critical")
    @mock.patch("requests.post")
    def test_sms_gateway_returns_bad_request_error(self, mock_post_request, mock_log_error):
        mock_post_request.return_value = mock.MagicMock(
            status_code=400,
            json=mock.MagicMock(
                return_value={
                    "error": {
                        "code": "105",
                        "description": "Invalid Destination Address",
                    }
                }
            )
        )

        sms_sender = SMSSender(text_message="test sms", phone_numbers=[31612345678])
        assert sms_sender.send_sms() is True
        mock_log_error.assert_called_once_with(
            "Sending a SMS to [31612345678] with this message: 'test sms' returned an error. "
            "Error code: 105, Error description: Invalid Destination Address")

    @mock.patch("logging.Logger.critical")
    @mock.patch("requests.post")
    def test_sms_gateway_returns_exception(self, mock_post_request, mock_log_error):
        mock_post_request.side_effect = Exception
        sms_sender = SMSSender(text_message="test sms", phone_numbers=[31612345678])

        assert sms_sender.send_sms() is False
        mock_log_error.assert_called_once_with("Sending a SMS is failed to [31612345678] with this message: test sms")


class TestSMSStatus(object):
    @mock.patch("requests.get")
    def test_get_sms_status_successful(self, mock_get_request):
        mock_get_request.return_value = mock.MagicMock(
            status_code=200,
            json=mock.MagicMock(
                return_value={
                    "data": {
                        "messageStatus": "004",
                        "description": "Received by recipient"
                    }
                }
            )
        )
        sms_status = SMSStatus(sms_id="3bc862d60fb8825fbd6c9e1bf74197b9")
        resp = sms_status.get_status()

        assert resp is True

    @mock.patch("logging.Logger.critical")
    @mock.patch("requests.get")
    def test_get_sms_for_wrong_sms_id(self, mock_get_request, mock_log_error):
        mock_get_request.return_value = mock.MagicMock(
            status_code=200,
            json=mock.MagicMock(
                return_value={
                    "data": {
                        "messageStatus": "001",
                        "description": "Message unknown",
                    }
                }
            )
        )
        sms_status = SMSStatus(sms_id="3bc862d60fb8825fbd6c9e1bf74197f8")
        resp = sms_status.get_status()

        assert resp is False
        mock_log_error.assert_called_once_with("Sending a SMS with this 3bc862d60fb8825fbd6c9e1bf74197f8 ID was not "
                                               "successfully done. Error description: Message unknown")

    @mock.patch("logging.Logger.critical")
    @mock.patch("requests.get")
    def test_get_sms_bad_request(self, mock_get_request, mock_log_error):
        mock_get_request.return_value = mock.MagicMock(
            status_code=400,
            json=mock.MagicMock(
                return_value={
                    "error": {
                        "description": "Invalid or missing parameter: apiMessageId",
                    }
                }
            )
        )
        sms_status = SMSStatus(sms_id=None)
        resp = sms_status.get_status()

        assert resp is False
        mock_log_error.assert_called_once_with("Sending a SMS with this None ID was not successfully done. "
                                               "Error description: Invalid or missing parameter: apiMessageId")

    @mock.patch("logging.Logger.critical")
    @mock.patch("requests.get")
    def test_sms_gateway_returns_exception(self, mock_get_request, mock_log_error):
        mock_get_request.side_effect = Exception
        sms_status = SMSStatus(sms_id="3bc862d60fb8825fbd6c9e1bf74197b9")

        assert sms_status.get_status() is False
        mock_log_error.assert_called_once_with("Getting status of SMS call was not successful. "
                                               "SMS ID: 3bc862d60fb8825fbd6c9e1bf74197b9")
