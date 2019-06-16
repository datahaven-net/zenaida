import datetime
from unittest import mock

import pytest
from django.test import TestCase, override_settings

from back.models.domain import Domain
from back.models.zone import Zone
from billing.models.order import Order
from billing.models.payment import Payment
from billing.payments import finish_payment
from zen import zusers


class BaseAuthTesterMixin(object):
    @pytest.mark.django_db
    def setUp(self):
        self.account = zusers.create_account('tester@zenaida.ai', account_password='123', is_active=True)
        self.client.login(email='tester@zenaida.ai', password='123')


class TestNewPaymentView(BaseAuthTesterMixin, TestCase):
    @override_settings(ZENAIDA_BILLING_BYPASS_PAYMENT_TIME_CHECK=True)
    @pytest.mark.django_db
    def test_create_new_payment_in_db(self):
        response = self.client.post('/billing/pay/', data=dict(amount=100, payment_method='pay_4csonline'))
        # Payment is started, so that redirect to the starting 4csonline page.
        assert response.status_code == 200
        assert response.context['transaction_id']

    @override_settings(ZENAIDA_BILLING_BYPASS_PAYMENT_TIME_CHECK=False)
    @mock.patch('billing.payments.latest_payment')
    @mock.patch('django.utils.timezone.now')
    def test_last_payment_was_done_before_3_minutes(self, mock_timezone_now, mock_latest_payment):
        mock_timezone_now.return_value = datetime.datetime(2019, 3, 23, 13, 35, 0)
        mock_latest_payment.return_value = mock.MagicMock(
            started_at=datetime.datetime(2019, 3, 23, 13, 34, 0),
        )
        response = self.client.post('/billing/pay/', data=dict(amount=100, payment_method='pay_4csonline'))
        # There was a payment a minute ago, so that redirect back to the payment page with an error message.
        assert response.status_code == 302
        assert response.url == '/billing/pay/'

    @pytest.mark.django_db
    @override_settings(ZENAIDA_BILLING_BYPASS_PAYMENT_TIME_CHECK=True)
    def test_payment_method_is_invalid(self):
        response = self.client.post('/billing/pay/', data=dict(amount=100, payment_method='unknown'))
        # When payment method is invalid, it returns back to the same page.
        assert response.status_code == 200
        assert response.template_name == ['billing/new_payment.html']


class TestOrdersListView(BaseAuthTesterMixin, TestCase):
    @pytest.mark.django_db
    def create_order(self):
        # Create an order
        Order.orders.create(
            owner=self.account,
            started_at=datetime.datetime(2019, 3, 23, 13, 34, 0),
            status='processed',
        )

    def test_orders_list_successful(self):
        self.create_order()
        response = self.client.post('/billing/orders/')
        assert response.status_code == 200
        assert len(response.context['object_list']) == 1

    def test_orders_list_by_year(self):
        self.create_order()
        response = self.client.post('/billing/orders/', data=dict(year=2019))
        assert response.status_code == 200
        assert len(response.context['object_list']) == 1

    def test_orders_list_by_year_and_month(self):
        self.create_order()
        response = self.client.post('/billing/orders/', data=dict(year=2019, month=3))
        assert response.status_code == 200
        assert len(response.context['object_list']) == 1

    def test_orders_list_by_year_and_month_returns_empty_list(self):
        self.create_order()
        response = self.client.post('/billing/orders/', data=dict(year=2018, month=3))
        assert response.status_code == 200
        assert len(response.context['object_list']) == 0


class TestOrderReceiptsDownloadView(BaseAuthTesterMixin, TestCase):
    @pytest.mark.django_db
    def test_download_receipts(self):
        Order.orders.create(
            owner=self.account,
            started_at=datetime.datetime(2019, 3, 23, 13, 34, 0),
            status='processed',
        )
        with mock.patch('billing.orders.build_receipt') as mock_build_receipt:
            self.client.post('/billing/orders/receipts/download/', data=dict(year=2019, month=3))
            mock_build_receipt.assert_called_once()

    def test_download_receipts_return_warning(self):
        response = self.client.post('/billing/orders/receipts/download/', data=dict(year=2019, month=2))
        assert response.url == '/billing/orders/receipts/download/'

    def test_get_billing_receipt_page(self):
        response = self.client.post('/billing/orders/receipts/download/')
        assert response.status_code == 200


class TestOrderSingleReceiptDownloadView(BaseAuthTesterMixin, TestCase):
    @pytest.mark.django_db
    def test_download_single_receipt(self):
        order = Order.orders.create(
            owner=self.account,
            started_at=datetime.datetime(2019, 3, 23, 13, 34, 0),
            status='processed',
        )
        with mock.patch('billing.orders.build_receipt') as mock_build_receipt:
            self.client.get(f'/billing/orders/receipts/download/{order.id}/')
            mock_build_receipt.assert_called_once()

    def test_download_single_receipt_returns_error(self):
        response = self.client.get(f'/billing/orders/receipts/download/1/')
        assert response.status_code == 302
        assert response.url == '/billing/orders/'


class TestPaymentsListView(BaseAuthTesterMixin, TestCase):
    @pytest.mark.django_db
    def test_show_paid_payments(self):
        # Create new payment with status paid
        Payment.payments.create(
            owner=self.account,
            amount=100,
            method='pay_4csonline',
            transaction_id='12345',
            started_at=datetime.datetime(2019, 3, 23),
            status='paid',
        )
        response = self.client.get('/billing/payments/')
        assert response.status_code == 200
        assert len(response.context['object_list']) == 1


class TestOrderDomainRenewView(BaseAuthTesterMixin, TestCase):
    @pytest.mark.django_db
    def test_domain_renew_order_successful(self):
        with mock.patch('billing.payments.by_transaction_id') as mock_payment_by_transaction_id:
            # Add 100.0 to the balance of the user to renew a domain
            mock_payment_by_transaction_id.return_value = mock.MagicMock(
                status='started',
                amount=100.0,
                owner=self.account,
            )
            finish_payment('12345', status='processed')
        response = self.client.get('/billing/order/create/renew/test.ai/')
        assert response.status_code == 200


class TestOrderDomainRegisterView(BaseAuthTesterMixin, TestCase):
    @pytest.mark.django_db
    def test_domain_register_order_successful(self):
        with mock.patch('billing.payments.by_transaction_id') as mock_payment_by_transaction_id:
            # Add 100.0 to the balance of the user to register a domain
            mock_payment_by_transaction_id.return_value = mock.MagicMock(
                status='started',
                amount=100.0,
                owner=self.account,
            )
            finish_payment('12345', status='processed')
        response = self.client.get('/billing/order/create/register/test.ai/')
        assert response.status_code == 200


class TestOrderDetailsView(BaseAuthTesterMixin, TestCase):

    @pytest.mark.django_db
    def test_order_detail_successful(self):
        new_order = Order.orders.create(
            owner=self.account,
            started_at=datetime.datetime(2019, 3, 23, 13, 34, 0),
            status='processed',
        )
        response = self.client.get('/billing/order/%d/' % new_order.id)
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
            status='processed',
        )

        response = self.client.get('/billing/order/1/')
        assert response.status_code == 400

    def test_unknown_order_returns_bad_request(self):
        """
        User tries to reach a domain which is not existing.
        Test if user will get 400 bad request error.
        """
        response = self.client.get('/billing/order/1/')
        assert response.status_code == 400


class TestOrderCreateView(BaseAuthTesterMixin, TestCase):

    @pytest.mark.django_db
    def test_multiple_domains_order(self):
        aizone = Zone.zones.create(name='ai')
        Domain.domains.create(
            owner=self.account,
            name='test_not_registered.ai',
            expiry_date=datetime.datetime(2099, 1, 1),
            create_date=datetime.datetime(1970, 1, 1),
            zone=aizone,
        )
        Domain.domains.create(
            owner=self.account,
            name='test_to_be_deleted.ai',
            expiry_date=datetime.datetime(2099, 1, 1),
            create_date=datetime.datetime(1970, 1, 1),
            zone=aizone,
            epp_id='epp1',
            status='to_be_deleted',
        )
        Domain.domains.create(
            owner=self.account,
            name='test_active.ai',
            expiry_date=datetime.datetime(2099, 1, 1),
            create_date=datetime.datetime(1970, 1, 1),
            zone=aizone,
            epp_id='epp2',
            status='active',
        )
        response = self.client.post('/billing/order/create/', data={'order_items': [
            'test_not_registered.ai',
            'test_to_be_deleted.ai',
            'test_active.ai',
        ]})
        assert response.status_code == 200
        assert response.context['order'].status == 'started'
        assert response.context['order'].description == 'register 1 domain, restore 1 domain, renew 1 domain'
        assert response.context['order'].owner == self.account
        assert len(response.context['order'].items.all()) == 3

    @pytest.mark.django_db
    def test_domain_register_order(self):
        Domain.domains.create(
            owner=self.account,
            name='test.ai',
            expiry_date=datetime.datetime(2099, 1, 1),
            create_date=datetime.datetime(1970, 1, 1),
            zone=Zone.zones.create(name='ai'),
        )
        response = self.client.post('/billing/order/create/', data={'order_items': ['test.ai']})
        assert response.status_code == 200
        assert response.context['order'].status == 'started'
        assert response.context['order'].description == 'domain register'
        assert response.context['order'].owner == self.account

    @pytest.mark.django_db
    def test_domain_restore_order(self):
        Domain.domains.create(
            owner=self.account,
            name='test.ai',
            expiry_date=datetime.datetime(2099, 1, 1),
            create_date=datetime.datetime(1970, 1, 1),
            zone=Zone.zones.create(name='ai'),
            epp_id='12345',
            status='to_be_deleted',
        )
        response = self.client.post('/billing/order/create/', data={'order_items': ['test.ai']})
        assert response.status_code == 200
        assert response.context['order'].status == 'started'
        assert response.context['order'].description == 'domain restore'
        assert response.context['order'].owner == self.account

    @pytest.mark.django_db
    def test_domain_renew_order(self):
        Domain.domains.create(
            owner=self.account,
            name='test.ai',
            expiry_date=datetime.datetime(2099, 1, 1),
            create_date=datetime.datetime(1970, 1, 1),
            zone=Zone.zones.create(name='ai'),
            epp_id='12345',
            status='active',
        )
        response = self.client.post('/billing/order/create/', data={'order_items': ['test.ai']})
        assert response.status_code == 200
        assert response.context['order'].status == 'started'
        assert response.context['order'].description == 'domain renew'
        assert response.context['order'].owner == self.account

    def test_domain_not_available_to_order(self):
        """
        Domain is not in database at all, so user can't do any action with it.
        """
        response = self.client.post('/billing/order/create/', data={'order_items': ['test.ai']})
        assert response.status_code == 404

    @pytest.mark.django_db
    def test_domain_blocked_order_failed(self):
        Domain.domains.create(
            owner=self.account,
            name='test.ai',
            expiry_date=datetime.datetime(2099, 1, 1),
            create_date=datetime.datetime(1970, 1, 1),
            zone=Zone.zones.create(name='ai'),
            epp_id='12345',
            status='blocked',
        )
        response = self.client.post('/billing/order/create/', data={'order_items': ['test.ai']})
        assert response.status_code == 302
        assert response.url == '/domains/'

    @pytest.mark.django_db
    @mock.patch('logging.critical')
    def test_domain_is_not_owned_by_other_user(self, mock_logging_critical):
        zone = Zone.zones.create(name='ai')
        account = zusers.create_account('other_user@zenaida.ai', account_password='123', is_active=True)
        Domain.domains.create(
            owner=account,
            name='test.ai',
            expiry_date=datetime.datetime(2099, 1, 1),
            create_date=datetime.datetime(1970, 1, 1),
            zone=zone,
        )
        response = self.client.post('/billing/order/create/', data={'order_items': ['test.ai']})
        assert response.status_code == 400
        mock_logging_critical.assert_called_once()

    def test_no_domain_selected_to_order(self):
        response = self.client.post('/billing/order/create/', data={'order_items': []})
        assert response.status_code == 302
        assert response.url == '/domains/'


class TestOrderCancelView(BaseAuthTesterMixin, TestCase):
    @pytest.mark.django_db
    def test_order_cancel_successful(self):
        # First create an order then cancel it.
        order = Order.orders.create(
            owner=self.account,
            started_at=datetime.datetime(2019, 3, 23, 13, 34, 0),
            status='processed',
        )

        response = self.client.post(f'/billing/order/cancel/{order.id}/')
        assert response.status_code == 302
        assert response.url == '/billing/orders/'

    def test_unknown_order_returns_bad_request(self):
        """
        User tries to cancel a domain which is not existing.
        Test if user will get 400 bad request error.
        """
        response = self.client.post('/billing/order/cancel/1/')
        assert response.status_code == 400

    @pytest.mark.django_db
    def test_order_cancel_suspicious(self):
        owner = zusers.create_account('other_user@zenaida.ai', account_password='123', is_active=True)
        order = Order.orders.create(
            owner=owner,
            started_at=datetime.datetime(2019, 3, 23, 13, 34, 0),
            status='processed',
        )
        response = self.client.post(f'/billing/order/cancel/{order.id}/')
        assert response.status_code == 400


class TestOrderExecuteView(BaseAuthTesterMixin, TestCase):
    @pytest.mark.django_db
    def test_order_execute_successful(self):
        order = Order.orders.create(
            owner=self.account,
            started_at=datetime.datetime(2019, 3, 23, 13, 34, 0),
            status='processed',
        )

        response = self.client.post(f'/billing/order/process/{order.id}/')
        assert response.status_code == 302
        assert response.url == '/domains/'

    @pytest.mark.django_db
    def test_order_execute_returns_technical_error(self):
        order = Order.orders.create(
            owner=self.account,
            started_at=datetime.datetime(2019, 3, 23, 13, 34, 0),
            status='processed',
        )
        with mock.patch('billing.orders.execute_single_order') as mock_execute_single_order:
            mock_execute_single_order.return_value = False
            response = self.client.post(f'/billing/order/process/{order.id}/')
        assert response.status_code == 302
        assert response.url == '/domains/'

    @pytest.mark.django_db
    def test_order_execute_suspicious(self):
        owner = zusers.create_account('other_user@zenaida.ai', account_password='123', is_active=True)
        order = Order.orders.create(
            owner=owner,
            started_at=datetime.datetime(2019, 3, 23, 13, 34, 0),
            status='processed',
        )

        response = self.client.post(f'/billing/order/process/{order.id}/')
        assert response.status_code == 400

    def test_unknown_order_returns_bad_request(self):
        """
        User tries to reach a domain which is not existing.
        Test if user will get 400 bad request error.
        """
        response = self.client.post('/billing/order/process/1/')
        assert response.status_code == 400

    def test_order_execute_error_not_enough_balance(self):
        with mock.patch('billing.orders.get_order_by_id_and_owner') as order_mock:
            order_mock.return_value = mock.MagicMock(
                owner=self.account,
                started_at=datetime.datetime(2019, 3, 23, 13, 34, 0),
                status='processed',
                total_price=100.00,
                id=1,
            )
            order_id = order_mock().id
            response = self.client.post(f'/billing/order/process/{order_id}/')
        assert response.status_code == 302
        assert response.url == '/billing/pay/'
