import datetime
from unittest import mock

import pytest
from django.test import TestCase, override_settings

from billing.models.payment import Payment
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
    @override_settings(BILLING_BYPASS_PAYMENT_TIME_CHECK=True)
    @pytest.mark.django_db
    def test_successful_process_payment(self):
        # Call payment endpoint to create payment first
        payment = self.client.post('/billing/pay/', data=dict(amount=100, payment_method='pay_4csonline'))
        transaction_id = payment.context['transaction_id']
        response = self.client.get(f'/billing/4csonline/process/{transaction_id}/')
        assert response.status_code == 200
        assert response.context['tran_id'] == transaction_id
        assert response.context['price'] == '100.00'

    @mock.patch('logging.critical')
    def test_payment_not_found(self, mock_logging_critical):
        """
        Tests process payment with wrong transaction id and check if SuspiciousOperation is logged.
        """
        self.client.post('/billing/pay/', data=dict(amount=100, payment_method='pay_4csonline'))
        response = self.client.get(f'/billing/4csonline/process/1234567890/')
        assert response.status_code == 400
        mock_logging_critical.assert_called_once_with(f'Payment not found, transaction_id is 1234567890')

    @mock.patch('logging.critical')
    def test_payment_is_from_other_user(self, mock_logging_critical):
        """
        Tests process payment with transaction id which belongs to other user and
        check if SuspiciousOperation is logged.
        """
        account = zusers.create_account('other_user@zenaida.ai', account_password='123', is_active=True)
        Payment.payments.create(
            owner=account,
            amount=100,
            method='pay_4csonline',
            transaction_id='12345',
            started_at=datetime.datetime(2019, 3, 23),
            status='paid'
        )
        response = self.client.get(f'/billing/4csonline/process/12345/')
        assert response.status_code == 400
        mock_logging_critical.assert_called_once_with('Invalid request, payment process raises SuspiciousOperation: '
                                                      'payment owner is not matching to request')

    @mock.patch('logging.critical')
    def test_payment_is_already_finished(self, mock_logging_critical):
        """
        Tests process payment with transaction id which was already finished and
        check if SuspiciousOperation is logged.
        """
        Payment.payments.create(
            owner=self.account,
            amount=100,
            method='pay_4csonline',
            transaction_id='12345',
            started_at=datetime.datetime(2019, 3, 23),
            finished_at=datetime.datetime(2019, 3, 24),
            status='paid'
        )
        response = self.client.get(f'/billing/4csonline/process/12345/')
        assert response.status_code == 400
        mock_logging_critical.assert_called_once_with('Invalid request, payment process raises SuspiciousOperation: '
                                                      'payment transaction is already finished')
