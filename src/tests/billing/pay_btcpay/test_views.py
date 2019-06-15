import mock
import pytest
from django.test import TestCase

from billing.pay_btcpay.models import BTCPayInvoice
from zen import zusers


class BaseAuthTesterMixin(object):
    @pytest.mark.django_db
    def setUp(self):
        self.account = zusers.create_account('tester@zenaida.ai', account_password='123', is_active=True)
        self.client.login(email='tester@zenaida.ai', password='123')


class TestProcessPaymentView(BaseAuthTesterMixin, TestCase):
    """
    Tests successful scenario for processing the payment.
    """
    @pytest.mark.django_db
    @mock.patch('btcpay.BTCPayClient')
    def test_successful_process_payment(self, mock_btcpay_invoice):
        mock_btcpay_invoice.return_value.create_invoice.return_value = {
            'url': 'https://example.com', 'id': '123456789', 'status': 'new'
        }
        # Call payment endpoint to create payment first
        payment = self.client.post('/billing/pay/', data=dict(amount=100, payment_method='pay_btcpay'))
        transaction_id = payment.context['transaction_id']

        request_data = {'amount': 100}
        response = self.client.post(path=f'/billing/btcpay/process/{transaction_id}/', data=request_data)

        assert len(BTCPayInvoice.invoices.all()) == 1
        assert response.status_code == 302
        assert response.url == 'https://example.com'

    @pytest.mark.django_db
    @mock.patch('django.contrib.messages.error')
    @mock.patch('logging.Logger.exception')
    @mock.patch('btcpay.BTCPayClient')
    def test_process_payment_exception(self, mock_btcpay_invoice, mock_log_exception, mock_messaging_error):
        mock_btcpay_invoice.side_effect = Exception
        # Call payment endpoint to create payment first
        payment = self.client.post('/billing/pay/', data=dict(amount=100, payment_method='pay_btcpay'))
        transaction_id = payment.context['transaction_id']

        request_data = {'amount': 100}
        response = self.client.post(path=f'/billing/btcpay/process/{transaction_id}/', data=request_data)

        assert response.status_code == 302
        assert response.url == '/billing/pay/'
        mock_log_exception.assert_called_once()
        mock_messaging_error.assert_called_once()
