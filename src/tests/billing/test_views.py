import copy
import datetime
import mock
import pytest

from django.test import TestCase, override_settings

from back.models.contact import Registrant
from back.models.domain import Domain
from back.models.zone import Zone
from billing import payments
from billing.models.order import Order
from billing.models.order_item import OrderItem
from billing.models.payment import Payment
from billing.payments import finish_payment
from tests import testsupport
from zen import zusers


class BaseAuthTesterMixin(object):

    @pytest.mark.django_db
    def setUp(self):
        self.account = zusers.create_account('tester@zenaida.ai', account_password='123', is_active=True)
        self.client.login(email='tester@zenaida.ai', password='123')


class TestNewPaymentView(BaseAuthTesterMixin, TestCase):

    @override_settings(ZENAIDA_BILLING_PAYMENT_TIME_FREEZE_SECONDS=60)
    @pytest.mark.django_db
    def test_create_new_btc_payment_in_db(self):
        response = self.client.post('/billing/pay/', data=dict(amount=100, payment_method='pay_btcpay'))
        # Payment is started, so that redirect to the starting btc payment page.
        assert response.status_code == 200
        assert response.context['transaction_id']

    @override_settings(
        ZENAIDA_BILLING_PAYMENT_TIME_FREEZE_SECONDS=60,
        ZENAIDA_BILLING_4CSONLINE_BANK_COMMISSION_RATE=0.2
    )
    @pytest.mark.django_db
    def test_create_new_credit_card_payment_in_db(self):
        response = self.client.post('/billing/pay/', data=dict(amount=100, payment_method='pay_4csonline'))
        # Payment is started, so that redirect to the starting 4csonline page.
        assert response.status_code == 200
        transaction_id = response.context['transaction_id']
        assert response.context['transaction_id']
        payment = payments.by_transaction_id(transaction_id)
        assert payment.amount == 100.0

    @override_settings(ZENAIDA_BILLING_PAYMENT_TIME_FREEZE_SECONDS=3*60)
    @mock.patch('billing.payments.latest_payment')
    @mock.patch('django.utils.timezone.now')
    def test_last_payment_was_done_before_3_minutes(self, mock_timezone_now, mock_latest_payment):
        mock_timezone_now.return_value = datetime.datetime(2019, 3, 23, 13, 35, 0)
        mock_latest_payment.return_value = mock.MagicMock(
            started_at=datetime.datetime(2019, 3, 23, 13, 34, 0),
        )
        response = self.client.post('/billing/pay/', data=dict(amount=100, payment_method='pay_btcpay'))
        # There was a payment a minute ago, so that redirect back to the payment page with an error message.
        assert response.status_code == 302
        assert response.url == '/billing/pay/'

    @pytest.mark.django_db
    @override_settings(ZENAIDA_BILLING_PAYMENT_TIME_FREEZE_SECONDS=60)
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
        response = self.client.post('/billing/orders/', data=dict(year=2019, month=4))
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

    @mock.patch('django.contrib.messages.warning')
    def test_download_receipts_return_warning(self, mock_messages_warning):
        self.client.post('/billing/orders/receipts/download/', data=dict(year=2019, month=2))
        mock_messages_warning.assert_called_once()

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

    @mock.patch('django.contrib.messages.warning')
    def test_download_receipt_for_another_user(self, mock_messages_warning):
        test_account = testsupport.prepare_tester_account(email='baduser@zenaida.ai')
        order = Order.orders.create(
            owner=test_account,
            started_at=datetime.datetime(2019, 3, 23, 13, 34, 0),
            status='processed',
        )
        response = self.client.get(f'/billing/orders/receipts/download/{order.id}/')
        assert response.status_code == 302
        assert response.url == '/billing/orders/'
        mock_messages_warning.assert_called_once()

    @mock.patch('django.contrib.messages.warning')
    def test_download_receipt_for_non_existing_order(self, mock_messages_warning):
        response = self.client.get(f'/billing/orders/receipts/download/1232131/')
        assert response.status_code == 302
        assert response.url == '/billing/orders/'
        mock_messages_warning.assert_called_once()


class TestPaymentInvoiceDownloadView(BaseAuthTesterMixin, TestCase):

    @pytest.mark.django_db
    def test_download_invoice(self):
        payment = Payment.payments.create(
            owner=self.account,
            started_at=datetime.datetime(2019, 3, 23, 13, 34, 0),
            finished_at=datetime.datetime(2019, 3, 23, 13, 34, 5),
            transaction_id='abcd',
            amount=100.0,
            status='processed',
        )
        with mock.patch('billing.payments.build_invoice') as mock_build_invoice:
            self.client.get(f'/billing/payment/invoice/download/{payment.transaction_id}/')
            mock_build_invoice.assert_called_once()

    @mock.patch('django.contrib.messages.warning')
    def test_download_invoice_for_another_user(self, mock_messages_warning):
        test_account = testsupport.prepare_tester_account(email='baduser@zenaida.ai')
        payment = Payment.payments.create(
            owner=test_account,
            started_at=datetime.datetime(2019, 3, 23, 13, 34, 0),
            finished_at=datetime.datetime(2019, 3, 23, 13, 34, 5),
            transaction_id='abcd',
            amount=100.0,
            status='processed',
        )
        response = self.client.get(f'/billing/payment/invoice/download/{payment.transaction_id}/')
        assert response.status_code == 302
        assert response.url == '/billing/payments/'
        mock_messages_warning.assert_called_once()

    @mock.patch('django.contrib.messages.warning')
    def test_download_invoice_for_non_existing_payment(self, mock_messages_warning):
        response = self.client.get(f'/billing/payment/invoice/download/fake_id/')
        assert response.status_code == 302
        assert response.url == '/billing/payments/'
        mock_messages_warning.assert_called_once()


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
    @mock.patch('zen.zdomains.domain_find')
    def test_domain_renew_order_successful(self, mock_domain_search):
        mock_domain_search.return_value = mock.MagicMock(expiry_date=datetime.datetime(2099, 1, 1))
        with mock.patch('billing.payments.by_transaction_id') as mock_payment_by_transaction_id:
            # Add 100.0 to the balance of the user to renew a domain
            mock_payment_by_transaction_id.return_value = mock.MagicMock(
                status='started',
                amount=100.0,
                owner=self.account,
            )
        response = self.client.get('/billing/order/create/renew/test.ai/')
        assert response.status_code == 200

    @pytest.mark.django_db
    @mock.patch('django.contrib.messages.warning')
    @mock.patch('zen.zdomains.domain_find')
    def test_one_started_order_for_same_user(self, mock_domain_search, mock_messages_warning):
        mock_domain_search.return_value = mock.MagicMock(expiry_date=datetime.datetime(2099, 1, 1))
        with mock.patch('billing.payments.by_transaction_id') as mock_payment_by_transaction_id:
            # Add 100.0 to the balance of the user to renew a domain
            mock_payment_by_transaction_id.return_value = mock.MagicMock(
                status='started',
                amount=100.0,
                owner=self.account,
            )
        response = self.client.get('/billing/order/create/renew/test.ai/')
        assert response.status_code == 200
        orders = Order.orders.all()
        assert len(orders) == 1
        assert orders[0].status == 'started'

        # Do another call again to verify that new order is not created for the same account.
        response = self.client.get('/billing/order/create/renew/test1.ai/')
        orders = Order.orders.all()
        assert len(orders) == 1
        assert orders[0].status == 'started'
        assert orders[0].items.all()[0].name == 'test.ai'
        mock_messages_warning.assert_called_once()


class TestOrderDomainRegisterView(BaseAuthTesterMixin, TestCase):

    @pytest.mark.django_db
    @mock.patch('zen.zdomains.domain_find')
    def test_domain_register_order_successful(self, mock_domain_search):
        mock_domain_search.return_value = mock.MagicMock(expiry_date=datetime.datetime(2099, 1, 1))
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

    @pytest.mark.django_db
    @mock.patch('django.contrib.messages.warning')
    @mock.patch('zen.zdomains.domain_find')
    def test_one_started_order_for_same_user(self, mock_domain_search, mock_messages_warning):
        mock_domain_search.return_value = mock.MagicMock(expiry_date=datetime.datetime(2099, 1, 1))
        with mock.patch('billing.payments.by_transaction_id') as mock_payment_by_transaction_id:
            # Add 100.0 to the balance of the user to register a domain
            mock_payment_by_transaction_id.return_value = mock.MagicMock(
                status='started',
                amount=100.0,
                owner=self.account,
            )
        response = self.client.get('/billing/order/create/register/test.ai/')
        assert response.status_code == 200
        orders = Order.orders.all()
        assert len(orders) == 1
        assert orders[0].status == 'started'

        # Do another call again to verify that new order is not created for the same account.
        response = self.client.get('/billing/order/create/register/test1.ai/')
        orders = Order.orders.all()
        assert len(orders) == 1
        assert orders[0].status == 'started'
        assert orders[0].items.all()[0].name == 'test.ai'
        mock_messages_warning.assert_called_once()


class TestOrderDomainRestoreView(BaseAuthTesterMixin, TestCase):

    @pytest.mark.django_db
    @mock.patch('zen.zdomains.domain_find')
    def test_domain_restore_order_successful(self, mock_domain_search):
        mock_domain_search.return_value = mock.MagicMock(expiry_date=datetime.datetime(2099, 1, 1))
        with mock.patch('billing.payments.by_transaction_id') as mock_payment_by_transaction_id:
            # Add 200.0 to the balance of the user to register a domain
            mock_payment_by_transaction_id.return_value = mock.MagicMock(
                status='started',
                amount=200.0,
                owner=self.account,
            )
        response = self.client.get('/billing/order/create/restore/test.ai/')
        assert response.status_code == 200

    @pytest.mark.django_db
    @mock.patch('django.contrib.messages.warning')
    @mock.patch('zen.zdomains.domain_find')
    def test_one_started_order_for_same_user(self, mock_domain_search, mock_messages_warning):
        mock_domain_search.return_value = mock.MagicMock(expiry_date=datetime.datetime(2099, 1, 1))
        with mock.patch('billing.payments.by_transaction_id') as mock_payment_by_transaction_id:
            # Add 200.0 to the balance of the user to register a domain
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

        # Do another call again to verify that new order is not created for the same account.
        response = self.client.get('/billing/order/create/restore/test1.ai/')
        orders = Order.orders.all()
        assert len(orders) == 1
        assert orders[0].status == 'started'
        assert orders[0].items.all()[0].name == 'test.ai'
        mock_messages_warning.assert_called_once()


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
    @mock.patch('django.contrib.messages.warning')
    def test_multiple_domains_order_and_one_started_order_per_user(self, mock_messages_warning):
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

        Domain.domains.create(
            owner=self.account,
            name='test.ai',
            expiry_date=datetime.datetime(2099, 1, 1),
            create_date=datetime.datetime(1970, 1, 1),
            zone=aizone,
        )
        Domain.domains.create(
            owner=self.account,
            name='test1_active.ai',
            expiry_date=datetime.datetime(2099, 1, 1),
            create_date=datetime.datetime(1970, 1, 1),
            zone=aizone,
            epp_id='epp10',
            status='active',
        )
        response = self.client.post('/billing/order/create/', data={'order_items': [
            'test.ai',
            'test1_active.ai',
        ]})

        assert response.status_code == 302
        orders = Order.orders.all()
        assert len(orders) == 1
        assert orders[0].status == 'started'
        # It is still previous order as that one's status is started.
        assert orders[0].description == 'register 1 domain, restore 1 domain, renew 1 domain'
        assert len(orders[0].items.all()) == 3
        assert orders[0].items.filter(name='test_not_registered.ai').first().status == 'started'
        mock_messages_warning.assert_called_once()

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
        # First, create a domain in database without epp_id as there was no payment yet.
        Domain.domains.create(
            owner=self.account,
            name='test.ai',
            expiry_date=datetime.datetime(2099, 1, 1),
            create_date=datetime.datetime(1970, 1, 1),
            zone=Zone.zones.create(name='ai'),
            status='inactive'
        )

        assert Domain.domains.all().count() == 1

        # Second, create an order for that domain to complete register.
        order = Order.orders.create(
            owner=self.account,
            started_at=datetime.datetime(2019, 3, 23, 13, 34, 0),
            status='processed',
        )

        OrderItem.order_items.create(
            order=order,
            type='domain_register',
            price=100.0,
            name='test.ai'
        )

        # Third, cancel that order.
        response = self.client.post(f'/billing/order/cancel/{order.id}/')
        assert response.status_code == 302
        assert response.url == '/billing/orders/'
        assert Domain.domains.all().count() == 0

    @pytest.mark.django_db
    def test_do_not_remove_domain_with_epp_id(self):
        # First, create a domain in database with an epp_id.
        Domain.domains.create(
            owner=self.account,
            name='test.ai',
            expiry_date=datetime.datetime(2099, 1, 1),
            create_date=datetime.datetime(1970, 1, 1),
            zone=Zone.zones.create(name='ai'),
            epp_id='12345',
            status='inactive'
        )

        assert Domain.domains.all().count() == 1

        order = Order.orders.create(
            owner=self.account,
            started_at=datetime.datetime(2019, 3, 23, 13, 34, 0),
            status='processed',
        )

        OrderItem.order_items.create(
            order=order,
            type='domain_register',
            price=100.0,
            name='test.ai'
        )

        response = self.client.post(f'/billing/order/cancel/{order.id}/')
        assert response.status_code == 302
        assert response.url == '/billing/orders/'
        # Order is removed but domain is still there.
        assert Domain.domains.all().count() == 1
        assert Order.orders.all().count() == 0

    @pytest.mark.django_db
    def test_do_not_remove_domain_without_inactive_status(self):
        # First, create a domain in database with an active status.
        Domain.domains.create(
            owner=self.account,
            name='test.ai',
            expiry_date=datetime.datetime(2099, 1, 1),
            create_date=datetime.datetime(1970, 1, 1),
            zone=Zone.zones.create(name='ai'),
            status='active'
        )

        assert Domain.domains.all().count() == 1

        order = Order.orders.create(
            owner=self.account,
            started_at=datetime.datetime(2019, 3, 23, 13, 34, 0),
            status='processed',
        )

        OrderItem.order_items.create(
            order=order,
            type='domain_register',
            price=100.0,
            name='test.ai'
        )

        response = self.client.post(f'/billing/order/cancel/{order.id}/')
        assert response.status_code == 302
        assert response.url == '/billing/orders/'
        # Order is removed but domain is still there.
        assert Domain.domains.all().count() == 1
        assert Order.orders.all().count() == 0

    @pytest.mark.django_db
    def test_cancel_order_for_non_existing_domain(self):
        order = testsupport.prepare_tester_order(domain_name='test.ai')
        assert Order.orders.all().count() == 1
        assert Domain.domains.all().count() == 0

        self.client.post(f'/billing/order/cancel/{order.id}/')
        assert Order.orders.all().count() == 0
        assert Domain.domains.all().count() == 0

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
    @mock.patch('zen.zmaster.domain_synchronize_from_backend')
    @mock.patch('zen.zmaster.domain_synchronize_contacts')
    def test_order_execute_within_same_registrar(self, mock_sync_contacts, mock_sync_backend):
        account_to_transfer = zusers.create_account('new_user@zenaida.ai', account_password='123', is_active=True)
        self.client.login(email='new_user@zenaida.ai', password='123')

        registrant = Registrant.registrants.create(
            person_name='TesterA',
            organization_name='TestingCorporation',
            address_street='Testers Boulevard 123',
            address_city='Testopia',
            address_province='TestingLands',
            address_postal_code='1234AB',
            address_country='NL',
            contact_voice='+31612341234',
            contact_fax='+31656785678',
            contact_email='tester_contact@zenaida.ai',
            owner=account_to_transfer
        )

        # Create the order and order_item for the account_to_transfer
        order = Order.orders.create(
            owner=account_to_transfer,
            started_at=datetime.datetime(2019, 3, 23, 13, 34, 0),
            status='processed',
        )
        OrderItem.order_items.create(
            order=order,
            type='domain_transfer',
            price=0,
            details={
                'internal': True,
                'transfer_code': 'abcd1234',
            },
            name='test.ai'
        )

        # Create a domain owned by previous user.
        ai_zone = Zone.zones.create(name='ai')
        Domain.domains.create(
            owner=self.account,
            name='test.ai',
            expiry_date=datetime.datetime(2099, 1, 1),
            create_date=datetime.datetime(1970, 1, 1),
            zone=ai_zone,
            epp_id='epp2',
            status='active',
            auth_key='abcd1234'
        )

        response = self.client.post(f'/billing/order/process/{order.id}/')
        assert response.status_code == 302
        assert response.url == '/domains/'

        # Check if backends is called to sync the domain info
        mock_sync_contacts.assert_called_once()
        mock_sync_backend.assert_called_once()

        # Check if domain is transfered to the new owner in database
        transfered_domain = Domain.domains.filter(name='test.ai')[0]
        assert transfered_domain.auth_key == ''
        assert transfered_domain.owner == account_to_transfer

    @pytest.mark.django_db
    def test_order_execute_returns_technical_error(self):
        order = Order.orders.create(
            owner=self.account,
            started_at=datetime.datetime(2019, 3, 23, 13, 34, 0),
            status='processed',
        )
        with mock.patch('billing.orders.execute_order') as mock_execute_order:
            mock_execute_order.return_value = False
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
                total_price=200.00,
                id=1,
            )
            order_id = order_mock().id
            response = self.client.post(f'/billing/order/process/{order_id}/')
        assert response.status_code == 302
        assert response.url == '/billing/pay/?amount=200'
