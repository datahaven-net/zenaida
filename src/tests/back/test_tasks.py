import mock
import pytest
import datetime

from django.test import TestCase
from django.utils import timezone

from tests import testsupport

from accounts.models.notification import Notification
from accounts.notifications import process_notifications_queue
from back import tasks


class TestSyncExpiredDomains(TestCase):

    @pytest.mark.django_db
    def test_dry_run(self):
        tester = testsupport.prepare_tester_account()
        tester_domain = testsupport.prepare_tester_domain(
            domain_name='abcd.ai',
            tester=tester,
            domain_epp_id='aaa123',
        )
        tester_domain.expiry_date = timezone.now() - datetime.timedelta(days=1)  # already expired a day ago
        tester_domain.status = 'active'
        tester_domain.save()
        report = tasks.sync_expired_domains(dry_run=True)
        assert len(report) == 1
        assert report[0] == (tester_domain, [], )
    
    
    @pytest.mark.django_db
    @mock.patch('zen.zmaster.domain_synchronize_from_backend')
    def test_ok(self, mock_domain_synchronize_from_backend):
        mock_domain_synchronize_from_backend.return_value = ['ok', ]
        tester = testsupport.prepare_tester_account()
        tester_domain = testsupport.prepare_tester_domain(
            domain_name='abcd.ai',
            tester=tester,
            domain_epp_id='aaa123',
        )
        tester_domain.expiry_date = timezone.now() - datetime.timedelta(days=1)  # already expired a day ago
        tester_domain.status = 'active'
        tester_domain.save()
        report = tasks.sync_expired_domains(dry_run=False)
        assert len(report) == 1
        assert report[0] == (tester_domain, ['ok', ], )
    
    
    @pytest.mark.django_db
    def test_skip_not_expired(self):
        tester = testsupport.prepare_tester_account()
        tester_domain = testsupport.prepare_tester_domain(
            domain_name='abcd.ai',
            tester=tester,
            domain_epp_id='aaa123',
        )
        tester_domain.expiry_date = timezone.now() + datetime.timedelta(days=1)  # not expired yet
        tester_domain.status = 'active'
        tester_domain.save()
        report = tasks.sync_expired_domains(dry_run=False)
        assert len(report) == 0
    
    
    @pytest.mark.django_db
    def test_skip_not_active(self):
        tester = testsupport.prepare_tester_account()
        tester_domain = testsupport.prepare_tester_domain(
            domain_name='abcd.ai',
            tester=tester,
            domain_epp_id='aaa123',
        )
        tester_domain.expiry_date = timezone.now() - datetime.timedelta(days=1)  # already expired a day ago
        tester_domain.status = 'inactive'
        tester_domain.save()
        report = tasks.sync_expired_domains(dry_run=False)
        assert len(report) == 0


class TestAutoRenewExpiringDomains(TestCase):

    @pytest.mark.django_db
    @mock.patch('accounts.notifications.EmailMultiAlternatives.send')
    @mock.patch('zen.zmaster.domain_check_create_update_renew')
    def test_order_created_executed_email_sent(self, mock_send, mock_domain_check_create_update_renew):
        mock_send.return_value = True
        mock_domain_check_create_update_renew.return_value = True
        tester = testsupport.prepare_tester_account()
        tester.balance = 1000.0
        tester.save()
        tester_domain = testsupport.prepare_tester_domain(
            domain_name='abcd.ai',
            tester=tester,
            domain_epp_id='aaa123',
        )
        tester_domain.expiry_date = timezone.now() + datetime.timedelta(days=89)  # will expire in 89 days
        tester_domain.status = 'active'
        tester_domain.save()
        report = tasks.auto_renew_expiring_domains(dry_run=False)
        assert len(report) == 1
        assert report[0][0] == tester_domain.name
        tester.refresh_from_db()
        assert tester.balance == 900.0
        process_notifications_queue(iterations=1, delay=0.1, iteration_delay=0.1)
        new_notification = Notification.notifications.first()
        assert new_notification.domain_name == 'abcd.ai'
        assert new_notification.status == 'sent'
        assert new_notification.subject == 'domain_renewed'

    @pytest.mark.django_db
    def test_auto_renew_started(self):
        tester = testsupport.prepare_tester_account()
        tester_domain = testsupport.prepare_tester_domain(
            domain_name='abcd.ai',
            tester=tester,
            domain_epp_id='aaa123',
        )
        tester_domain.expiry_date = timezone.now() + datetime.timedelta(days=89)  # will expire in 89 days
        tester_domain.status = 'active'
        tester_domain.save()
        report = tasks.auto_renew_expiring_domains(dry_run=True)
        assert len(report) == 1
        assert report[0][0] == tester_domain.name

    @pytest.mark.django_db
    def test_auto_renew_not_started(self):
        tester = testsupport.prepare_tester_account()
        tester_domain = testsupport.prepare_tester_domain(
            domain_name='abcd.ai',
            tester=tester,
            domain_epp_id='aaa123',
        )
        tester_domain.expiry_date = timezone.now() + datetime.timedelta(days=91)  # will expire in 91 days
        tester_domain.status = 'active'
        tester_domain.save()
        report = tasks.auto_renew_expiring_domains(dry_run=True)
        assert len(report) == 0

    @pytest.mark.django_db
    def test_balance_not_enough(self):
        tester = testsupport.prepare_tester_account()
        tester.balance = 50.0
        tester.save()
        tester_domain = testsupport.prepare_tester_domain(
            domain_name='abcd.ai',
            tester=tester,
            domain_epp_id='aaa123',
        )
        tester_domain.expiry_date = timezone.now() + datetime.timedelta(days=89)  # will expire in 89 days
        tester_domain.status = 'active'
        tester_domain.save()
        report = tasks.auto_renew_expiring_domains(dry_run=False)
        assert len(report) == 1
        assert report[0][0] == tester_domain.name
        assert report[0][1].args[0] == 'not enough funds'

    @pytest.mark.django_db
    @mock.patch('billing.orders.execute_order')
    def test_execute_order_failed(self, mock_execute_order):
        mock_execute_order.return_value = 'failed'
        tester = testsupport.prepare_tester_account()
        tester.balance = 200.0
        tester.save()
        tester_domain = testsupport.prepare_tester_domain(
            domain_name='abcd.ai',
            tester=tester,
            domain_epp_id='aaa123',
        )
        tester_domain.expiry_date = timezone.now() + datetime.timedelta(days=89)  # will expire in 89 days
        tester_domain.status = 'active'
        tester_domain.save()
        report = tasks.auto_renew_expiring_domains(dry_run=False)
        assert len(report) == 1
        assert report[0][0] == tester_domain.name
        assert report[0][1].args[0] == 'renew order status is failed'
