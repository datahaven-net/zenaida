from unittest import mock

import pytest
from django.test import TestCase

from billing.payments import finish_payment
from zen import zusers


class BaseAuthTesterMixin(object):
    @pytest.mark.django_db
    def setUp(self):
        self.account = zusers.create_account('tester@zenaida.ai', account_password='123', is_active=True)
        self.client.login(email='tester@zenaida.ai', password='123')


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
