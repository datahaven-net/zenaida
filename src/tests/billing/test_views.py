import datetime
from unittest import mock

import pytest
from django.test import TestCase, override_settings

from billing.models.order import Order
from billing.payments import finish_payment
from zen import zusers


class BaseAuthTesterMixin(object):
    @pytest.mark.django_db
    def setUp(self):
        self.account = zusers.create_account('tester@zenaida.ai', account_password='123', is_active=True)
        self.client.login(email='tester@zenaida.ai', password='123')


class TestNewPaymentView(BaseAuthTesterMixin, TestCase):
    @override_settings(BILLING_BYPASS_PAYMENT_TIME_CHECK=True)
    @pytest.mark.django_db
    def test_create_new_payment_in_db(self):
        response = self.client.post('/billing/pay/', data=dict(amount=100, payment_method='pay_4csonline'))
        # Payment is started, so that redirect to the starting 4csonline page.
        assert response.status_code == 200
        assert response.context['transaction_id']

    @override_settings(BILLING_BYPASS_PAYMENT_TIME_CHECK=False)
    @mock.patch('billing.payments.latest_payment')
    @mock.patch('django.utils.timezone.now')
    def test_last_payment_was_done_before_3_minutes(self, mock_timezone_now, mock_latest_payment):
        mock_timezone_now.return_value = datetime.datetime(2019, 3, 23, 13, 35, 0)
        mock_latest_payment.return_value = mock.MagicMock(
            started_at=datetime.datetime(2019, 3, 23, 13, 34, 0)
        )
        response = self.client.post('/billing/pay/', data=dict(amount=100, payment_method='pay_4csonline'))
        # There was a payment a minute ago, so that redirect back to the payment page with an error message.
        assert response.status_code == 302
        assert response.url == '/billing/pay/'

    @pytest.mark.django_db
    @override_settings(BILLING_BYPASS_PAYMENT_TIME_CHECK=True)
    def test_payment_method_is_invalid(self):
        response = self.client.post('/billing/pay/', data=dict(amount=100, payment_method='unknown'))
        # When payment method is invalid, it returns back to the same page.
        assert response.status_code == 200
        assert response.template_name == ['billing/new_payment.html']


class TestOrderDomainRenewView(BaseAuthTesterMixin, TestCase):
    @pytest.mark.django_db
    def test_domain_renew_order_successful(self):
        with mock.patch('billing.payments.by_transaction_id') as mock_payment_by_transaction_id:
            # Add 100.0 to the balance of the user to renew a domain
            mock_payment_by_transaction_id.return_value = mock.MagicMock(
                status='started',
                amount=100.0,
                owner=self.account
            )
            finish_payment('12345', status='processed')
        response = self.client.get('/billing/order/create/renew/test.ai/')
        assert response.status_code == 200

    def test_domain_renew_error_not_enough_balance(self):
        response = self.client.get('/billing/order/create/renew/test.ai/')
        assert response.status_code == 302
        assert response.url == '/billing/pay/'


class TestOrderDomainRegisterView(BaseAuthTesterMixin, TestCase):
    @pytest.mark.django_db
    def test_domain_register_order_successful(self):
        with mock.patch('billing.payments.by_transaction_id') as mock_payment_by_transaction_id:
            # Add 100.0 to the balance of the user to register a domain
            mock_payment_by_transaction_id.return_value = mock.MagicMock(
                status='started',
                amount=100.0,
                owner=self.account
            )
            finish_payment('12345', status='processed')
        response = self.client.get('/billing/order/create/register/test.ai/')
        assert response.status_code == 200

    def test_domain_register_error_not_enough_balance(self):
        response = self.client.get('/billing/order/create/register/test.ai/')
        assert response.status_code == 302
        assert response.url == '/billing/pay/'


class TestOrderDetailsView(BaseAuthTesterMixin, TestCase):

    @pytest.mark.django_db
    def test_order_detail_successful(self):
        new_order = Order.orders.create(
            owner=self.account,
            started_at=datetime.datetime(2019, 3, 23, 13, 34, 0),
            status='processed'
        )
        response = self.client.get('/billing/orders/%d/' % new_order.id)
        assert response.status_code == 200
        assert response.context['object'].id == new_order.id
        assert response.context['object'].status == 'processed'

    @pytest.mark.django_db
    def test_get_order_details_suspicious(self):
        """
        User tries to reach another person's domain order details.
        Test if user will get 400 bad request error.
        """
        owner = zusers.create_account('other_user@zenaida.ai', account_password='123', is_active=True)
        Order.orders.create(
            owner=owner,
            started_at=datetime.datetime(2019, 3, 23, 13, 34, 0),
            status='processed'
        )

        response = self.client.get('/billing/orders/1/')
        assert response.status_code == 400

    def test_unknown_order_returns_bad_request(self):
        """
        User tries to reach a domain which is not existing.
        Test if user will get 400 bad request error.
        """
        response = self.client.get('/billing/orders/1/')
        assert response.status_code == 400
