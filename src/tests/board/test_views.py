import datetime
from unittest import mock

import pytest
from django.test import TestCase, override_settings

from billing.models.order import Order
from billing.models.order_item import OrderItem
from zen import zusers


class BaseAuthTesterMixin(object):
    @pytest.mark.django_db
    def setUp(self):
        self.account = zusers.create_account('tester@zenaida.ai', account_password='123', is_active=True)
        self.client.login(email='tester@zenaida.ai', password='123')


class TestFinancialReportView(BaseAuthTesterMixin, TestCase):
    @pytest.mark.django_db
    def create_order(self, year, month):
        # Create an order
        order = Order.orders.create(
            owner=self.account,
            started_at=datetime.datetime(year, month, 1, 1, 0, 0),
            finished_at=datetime.datetime(year, month, 1, 1, 0, 0),
            status='processed',
        )
        OrderItem.order_items.create(
            order=order,
            type='domain_register',
            price=100.00,
            name='test.ai',
        )

    def test_financial_result_for_specific_month_successful(self):
        self.account.is_staff = True
        self.account.date_joined = datetime.datetime(2019, 1, 1, 1, 0, 0)
        self.account.save()
        self.create_order(2019, 1)

        response = self.client.post('/board/financial-report/', data=dict(year=2019, month=1))

        assert response.status_code == 200
        assert response.context['total_payment_by_users'] == 100.0
        assert response.context['total_registered_users'] == 1
        assert len(response.context['object_list']) == 1

    def test_financial_result_for_specific_year_successful(self):
        self.account.is_staff = True
        self.account.date_joined = datetime.datetime(2019, 1, 1, 1, 0, 0)
        self.account.save()
        self.create_order(2019, 1)
        self.create_order(2019, 2)

        response = self.client.post('/board/financial-report/', data=dict(year=2019))

        assert response.status_code == 200
        assert response.context['total_payment_by_users'] == 200.0
        assert response.context['total_registered_users'] == 1
        assert len(response.context['object_list']) == 2

    @mock.patch('django.contrib.messages.error')
    def test_financial_result_access_denied_for_normal_user(self, mock_messages_error):
        self.create_order(2019, 1)
        self.create_order(2019, 2)

        response = self.client.post('/board/financial-report/', data=dict(year=2019))

        assert response.status_code == 302
        assert response.url == '/'
        mock_messages_error.assert_called_once()
