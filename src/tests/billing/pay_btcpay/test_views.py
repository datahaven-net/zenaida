import mock
import pytest
from django.test import TestCase

from billing.models.order import Order
from billing.pay_btcpay.models import BTCPayInvoice
from zen import zusers


class BaseAuthTesterMixin(object):
    @pytest.mark.django_db
    def setUp(self):
        self.account = zusers.create_account('tester@zenaida.ai', account_password='123', is_active=True)
        self.account.balance = 1000
        self.account.save()
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
        payment = self.client.post('/billing/pay/', data=dict(amount=120, payment_method='pay_btcpay'))
        transaction_id = payment.context['transaction_id']

        request_data = {'amount': 120}
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
        payment = self.client.post('/billing/pay/', data=dict(amount=120, payment_method='pay_btcpay'))
        transaction_id = payment.context['transaction_id']

        request_data = {'amount': 120}
        response = self.client.post(path=f'/billing/btcpay/process/{transaction_id}/', data=request_data)

        assert response.status_code == 302
        assert response.url == '/billing/pay/'
        mock_log_exception.assert_called_once()
        mock_messaging_error.assert_called_once()


class TestRedirectPaymentView(BaseAuthTesterMixin, TestCase):
    @mock.patch('django.contrib.messages.warning')
    def test_redirect_payment_to_order(self, mock_messages_warning):
        with mock.patch('billing.payments.by_transaction_id') as mock_payment_by_transaction_id:
            mock_payment_by_transaction_id.return_value = mock.MagicMock(
                status='started',
                amount=200.0,
                owner=self.account,
            )
        response = self.client.get('/billing/order/create/restore/test.ai/')
        assert response.status_code == 200
        orders = Order.orders.all()
        assert len(orders) == 1
        assert orders[0].status == 'started'

        redirect_payment_resp = self.client.get('/billing/btcpay/redirect/')
        assert redirect_payment_resp.status_code == 302
        order_id = Order.orders.filter(owner=self.account)[0].id
        assert redirect_payment_resp.url == f'/billing/order/{order_id}/'
        mock_messages_warning.assert_called_once()

    def test_redirect_payment_to_payments_overview(self):
        resp = self.client.get('/billing/btcpay/redirect/')
        assert resp.status_code == 302
        assert resp.url == '/billing/payments/'
