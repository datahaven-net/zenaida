import mock
import pytest
import datetime

from django.test import TestCase
from django.utils import timezone

from tests import testsupport

from billing import tasks
from billing.models.order import Order


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
