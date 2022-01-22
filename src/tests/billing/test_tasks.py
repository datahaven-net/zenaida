import mock
import pytest
import datetime

from django.test import TestCase
from django.utils import timezone

from tests import testsupport

from billing import tasks
from billing.models.order import Order
from billing.models.order_item import OrderItem


@pytest.mark.django_db
def test_identify_domains_for_auto_renew():
    tester = testsupport.prepare_tester_account()
    tester_domain = testsupport.prepare_tester_domain(
        domain_name='abcd.ai',
        tester=tester,
        domain_epp_id='aaa123',
        auto_renew_enabled=True,
    )
    tester_domain.expiry_date = timezone.now() + datetime.timedelta(days=45)  # expiry_date 45 days from now
    tester_domain.status = 'active'
    tester_domain.save()
    domains_to_renew = tasks.identify_domains_for_auto_renew()
    assert domains_to_renew == {tester: ['abcd.ai', ]}


@pytest.mark.django_db
def test_identify_domains_for_auto_renew_auto_renew_disabled():
    tester = testsupport.prepare_tester_account()
    tester_domain = testsupport.prepare_tester_domain(
        domain_name='abcd.ai',
        tester=tester,
        domain_epp_id='aaa123',
        auto_renew_enabled=False,
    )
    tester_domain.expiry_date = timezone.now() + datetime.timedelta(days=45)  # expiry_date 45 days from now
    tester_domain.status = 'active'
    tester_domain.save()
    domains_to_renew = tasks.identify_domains_for_auto_renew()
    assert domains_to_renew == {}


@pytest.mark.django_db
def test_identify_domains_for_auto_renew_can_not_be_renewed():
    tester = testsupport.prepare_tester_account()
    tester_domain = testsupport.prepare_tester_domain(
        domain_name='abcd.ai',
        tester=tester,
        domain_status='inactive',
        auto_renew_enabled=True,
    )
    tester_domain.expiry_date = timezone.now() + datetime.timedelta(days=45)  # expiry_date 45 days from now
    tester_domain.status = 'active'
    tester_domain.save()
    domains_to_renew = tasks.identify_domains_for_auto_renew()
    assert domains_to_renew == {}


class TestOrderRemovalTasks(TestCase):
    @pytest.mark.django_db
    @mock.patch('logging.Logger.debug')
    def test_remove_started_orders_older_than_1_day(self, mock_log_debug):
        time_now = datetime.datetime.now()
        testsupport.prepare_tester_order(
            domain_name='test.ai',
            status='started',
            started_at=time_now-datetime.timedelta(days=2)
        )
        assert Order.orders.all().count() == 1

        tasks.remove_started_orders(1)
        assert Order.orders.all().count() == 0
        mock_log_debug.assert_called_once()



class TestRetryFailedOrdersTask(TestCase):

    @pytest.mark.django_db
    def test_order_failed_to_incomplete(self):
        time_now = datetime.datetime.now()
        testsupport.prepare_tester_order(
            domain_name='test.ai',
            order_type='domain_renew',
            status='failed',
            item_status='executing',
            started_at=time_now-datetime.timedelta(minutes=20)
        )
        assert Order.orders.first().status == 'failed'
        tasks.retry_failed_orders()
        assert Order.orders.first().status == 'incomplete'

    @pytest.mark.django_db
    def test_order_started_and_executing(self):
        time_now = datetime.datetime.now()
        testsupport.prepare_tester_order(
            domain_name='test.ai',
            order_type='domain_transfer',
            status='started',
            item_status='executing',
            started_at=time_now-datetime.timedelta(minutes=20)
        )
        assert Order.orders.first().status == 'started'
        tasks.retry_failed_orders()
        assert Order.orders.first().status == 'started'

    @pytest.mark.django_db
    def test_order_item_failed_to_incomplete(self):
        time_now = datetime.datetime.now()
        testsupport.prepare_tester_order(
            domain_name='test.ai',
            order_type='domain_register',
            status='failed',
            item_status='failed',
            started_at=time_now-datetime.timedelta(minutes=20)
        )
        assert Order.orders.first().status == 'failed'
        tasks.retry_failed_orders()
        assert Order.orders.first().status == 'incomplete'

    @pytest.mark.django_db
    def test_order_created_recently(self):
        time_now = datetime.datetime.now()
        testsupport.prepare_tester_order(
            domain_name='test.ai',
            order_type='domain_register',
            status='failed',
            item_status='failed',
            started_at=time_now-datetime.timedelta(minutes=4)
        )
        assert Order.orders.first().status == 'failed'
        tasks.retry_failed_orders()
        assert Order.orders.first().status == 'failed'

    @pytest.mark.django_db
    def test_order_incomplete_but_retried(self):
        time_now = datetime.datetime.now()
        testsupport.prepare_tester_order(
            domain_name='test.ai',
            order_type='domain_renew',
            status='incomplete',
            item_status='executing',
            started_at=time_now-datetime.timedelta(minutes=20)
        )
        assert Order.orders.first().status == 'incomplete'
        assert OrderItem.order_items.first().status == 'executing'
        tasks.retry_failed_orders()
        assert Order.orders.first().status == 'incomplete'
        assert OrderItem.order_items.first().status == 'blocked'

    @pytest.mark.django_db
    @mock.patch('zen.zmaster.domain_check_create_update_renew')
    def test_order_incomplete_failed_retried(self, mock_domain_check_create_update_renew):
        time_now = datetime.datetime.now()
        tester = testsupport.prepare_tester_account(account_balance=200)
        testsupport.prepare_tester_domain(
            domain_name='test.ai',
            tester=tester,
            domain_status='active',
        )
        testsupport.prepare_tester_order(
            domain_name='test.ai',
            order_type='domain_renew',
            status='incomplete',
            item_status='failed',
            started_at=time_now-datetime.timedelta(minutes=20)
        )
        assert Order.orders.first().status == 'incomplete'
        assert OrderItem.order_items.first().status == 'failed'
        mock_domain_check_create_update_renew.return_value = True
        tasks.retry_failed_orders()
        assert Order.orders.first().status == 'processed'
        assert OrderItem.order_items.first().status == 'processed'
        mock_domain_check_create_update_renew.assert_called_once()
        tester.refresh_from_db()
        assert tester.balance == 100
